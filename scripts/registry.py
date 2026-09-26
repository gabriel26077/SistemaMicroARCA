"""Validation and canonical serialization. Never imports package code."""
import ast
from collections import Counter
import hashlib
import json
import keyword
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE = 65536
MAX_BLOCKS = 65536
MAX_CATALOG = 1048576
RESERVED = {'boot.py', 'main.py', 'user.py', 'arca_ble.py', 'arca_runtime.py', 'arca_files.py'}
METADATA = {'manifest.json', 'LICENSE', 'README', 'README.md', 'README.txt', 'UPSTREAM.json'}


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'chave JSON duplicada: {key}')
            result[key] = value
        return result
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(Invalid(f'JSON inválido: {x}')))
    except (UnicodeError, ValueError) as exc:
        raise Invalid(str(exc)) from exc


def schema_check(value, schema, path='$', document=None):
    """Evaluate only the JSON Schema keywords used by our versioned schemas."""
    document = document or schema
    if '$ref' in schema:
        target = document
        for part in schema['$ref'].removeprefix('#/').split('/'):
            target = target[part]
        return schema_check(value, target, path, document)
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}
    if 'type' in schema:
        require(type(value) is types[schema['type']], f'{path}: tipo inválido')
    if 'const' in schema:
        require(value == schema['const'], f'{path}: valor inválido')
    if 'enum' in schema:
        require(value in schema['enum'], f'{path}: valor inválido')
    if isinstance(value, dict):
        require(set(schema.get('required', [])) <= value.keys(), f'{path}: campos obrigatórios ausentes')
        properties = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            require(value.keys() <= properties.keys(), f'{path}: campos desconhecidos')
        for key, item in value.items():
            if key in properties:
                schema_check(item, properties[key], f'{path}.{key}', document)
    if isinstance(value, str):
        require(len(value) >= schema.get('minLength', 0), f'{path}: texto vazio')
        require(len(value) <= schema.get('maxLength', 10000), f'{path}: texto muito longo')
        if 'pattern' in schema:
            require(re.fullmatch(schema['pattern'], value, re.ASCII) is not None, f'{path}: formato inválido')
    if isinstance(value, list):
        require(len(value) >= schema.get('minItems', 0), f'{path}: lista vazia')
        require(len(value) <= schema.get('maxItems', 10000), f'{path}: lista muito longa')
        if schema.get('uniqueItems'):
            require(len({json.dumps(v, sort_keys=True) for v in value}) == len(value), f'{path}: itens duplicados')
        for i, item in enumerate(value):
            schema_check(item, schema.get('items', {}), f'{path}[{i}]', document)
    if type(value) is int:
        require(schema.get('minimum', value) <= value <= schema.get('maximum', value), f'{path}: fora do limite')


def safe_name(name):
    require(isinstance(name, str) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*\.py', name, re.ASCII),
            f'nome de módulo inválido: {name!r}')
    require(not keyword.iskeyword(name[:-3]), f'identificador reservado: {name}')
    require(name.lower() not in RESERVED, f'nome reservado: {name}')


def placeholder_names(value, subject):
    pattern = re.compile(r'\{([A-Z][A-Z0-9_]*)\}', re.ASCII)
    names = [match.group(1) for match in pattern.finditer(value)]
    remainder = pattern.sub('', value)
    require('{' not in remainder and '}' not in remainder, f'placeholder invalido em {subject}')
    return names


def validate_blocks(data, identity):
    require(0 < len(data) <= MAX_BLOCKS, f'manifesto de blocos fora do limite: {identity}')
    value = parse_json(data)
    schema = parse_json((ROOT / 'schemas/blocks.schema.json').read_bytes())
    schema_check(value, schema)
    require((value['package']['id'], value['package']['version']) == identity,
            f'manifesto de blocos pertence a outro pacote: {identity}')
    prefix = identity[0].replace('-', '_') + '_'
    seen_types = set()
    import_pattern = re.compile(
        r'(?:import [A-Za-z_][A-Za-z0-9_.]*|'
        r'from [A-Za-z_][A-Za-z0-9_.]* import '
        r'[A-Za-z_][A-Za-z0-9_]*(?:, [A-Za-z_][A-Za-z0-9_]*)*)',
        re.ASCII,
    )
    for block in value['blocks']:
        block_type = block['type']
        require(block_type.startswith(prefix), f'tipo de bloco sem namespace: {block_type}')
        require(block_type not in seen_types, f'tipo de bloco duplicado: {block_type}')
        seen_types.add(block_type)
        fields = block['fields']
        names = [field['name'] for field in fields]
        require(len(names) == len(set(names)), f'campo duplicado em {block_type}')
        require(Counter(placeholder_names(block['label'], block_type)) == Counter(names),
                f'label diverge dos campos em {block_type}')
        for field in fields:
            field_type, default = field['type'], field['default']
            if field_type == 'identifier':
                require(type(default) is str and
                        re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', default, re.ASCII) and
                        not keyword.iskeyword(default),
                        f'identificador padrao invalido em {block_type}')
                require('min' not in field and 'max' not in field,
                        f'limites invalidos em {block_type}')
            elif field_type == 'text':
                require(type(default) is str and len(default) <= 240,
                        f'texto padrao invalido em {block_type}')
                require('min' not in field and 'max' not in field,
                        f'limites invalidos em {block_type}')
            elif field_type == 'value':
                valid_default = (
                    (type(default) is str and len(default) <= 240) or
                    type(default) is bool or
                    (type(default) in (int, float) and -1000000 <= default <= 1000000)
                )
                require(valid_default, f'valor exibivel padrao invalido em {block_type}')
                require('min' not in field and 'max' not in field,
                        f'limites invalidos em {block_type}')
            else:
                require(type(default) is int and type(field.get('min')) is int and
                        type(field.get('max')) is int and
                        -1000000 <= field['min'] <= default <= field['max'] <= 1000000,
                        f'inteiro padrao invalido em {block_type}')
        python = block['python']
        require(all(import_pattern.fullmatch(item) for item in python['imports']),
                f'import invalido em {block_type}')
        template = python['template']
        require('\r' not in template and template.endswith('\n') and template.count('\n') == 1,
                f'template precisa ser uma linha em {block_type}')
        require(set(placeholder_names(template, block_type)) == set(names),
                f'template diverge dos campos em {block_type}')
    return value


def plain(path, directory=False):
    require(not path.is_symlink(), f'link simbólico proibido: {path}')
    require(path.is_dir() if directory else path.is_file(), f'caminho ausente ou não regular: {path}')


def inventory(directory):
    plain(directory, True)
    result = {}
    for path in sorted(directory.rglob('*')):
        require(not path.is_symlink(), f'link simbólico proibido: {path}')
        if path.is_dir():
            result[path.relative_to(directory).as_posix() + '/'] = b''
        else:
            plain(path)
            result[path.relative_to(directory).as_posix()] = path.read_bytes()
    return result


def sources(root):
    schema = parse_json((ROOT / 'schemas/package.schema.json').read_bytes())
    base = root / 'packages'
    plain(base, True)
    packages, ledger, owners, seen = [], {}, {}, set()
    for package_dir in sorted(base.iterdir()):
        plain(package_dir, True)
        require(any(package_dir.iterdir()), f'pacote sem versões: {package_dir}')
        for directory in sorted(package_dir.iterdir()):
            plain(directory, True)
            manifest_path = directory / 'manifest.json'
            plain(manifest_path)
            manifest = parse_json(manifest_path.read_bytes())
            schema_check(manifest, schema)
            identity = (manifest['id'], manifest['version'])
            require(identity not in seen, f'ID/versão duplicados: {identity}')
            seen.add(identity)
            require(identity == (package_dir.name, directory.name), f'manifest fora do caminho canônico: {directory}')
            declared, names = set(), set()
            files = {}
            for entry in manifest['files']:
                source, name = entry['source'], entry['install_as']
                safe_name(source)
                safe_name(name)
                require(source not in declared and name.lower() not in names, f'arquivo duplicado: {name}')
                declared.add(source)
                names.add(name.lower())
                require(owners.get(name.lower(), identity[0]) == identity[0], f'arquivo pertence a dois pacotes: {name}')
                owners[name.lower()] = identity[0]
                path = directory / source
                plain(path)
                data = path.read_bytes()
                require(len(data) <= MAX_FILE, f'arquivo maior que 64 KiB: {path}')
                try:
                    code = data.decode('utf-8')
                    # Parse text so a Python encoding cookie cannot override UTF-8.
                    ast.parse(code, filename=str(path))
                except (UnicodeError, SyntaxError, ValueError) as exc:
                    raise Invalid(f'Python/UTF-8 inválido: {path}: {exc}') from exc
                files[name] = data
            blocks = manifest.get('blocks')
            if blocks is not None:
                source = blocks['source']
                require(source not in declared, f'arquivo duplicado: {source}')
                declared.add(source)
                path = directory / source
                plain(path)
                validate_blocks(path.read_bytes(), identity)
            members = {}
            for path in sorted(directory.iterdir()):
                plain(path)
                require(path.name in declared | METADATA, f'arquivo não declarado: {path}')
                members[path.name] = sha(path.read_bytes())
            require('LICENSE' in members and (directory / 'LICENSE').read_text(encoding='utf-8').strip(),
                    f'licença ausente: {directory}')
            if manifest['origin'] == 'third-party':
                upstream_path = directory / 'UPSTREAM.json'
                plain(upstream_path)
                upstream = parse_json(upstream_path.read_bytes())
                schema_check(upstream, schema['$defs']['upstream'])
                require(manifest.get('homepage', '').startswith('https://'), 'homepage de terceiro obrigatória')
                require(upstream['license'] == manifest['license'], 'licença upstream diverge do manifest')
                require(upstream['commit'] in upstream['source_url'] and upstream['commit'] in upstream['license_url'],
                        'URLs upstream precisam fixar o commit registrado')
            dependencies = [(d['id'], d['version']) for d in manifest['dependencies']]
            require(len({d[0] for d in dependencies}) == len(dependencies), f'dependência duplicada: {identity}')
            ledger['/'.join(identity)] = members
            packages.append((manifest, files, directory))
    require(packages, 'catálogo vazio')
    graph = {(m['id'], m['version']): [(d['id'], d['version']) for d in m['dependencies']] for m, _, _ in packages}
    for node, dependencies in graph.items():
        require(all(d in graph for d in dependencies), f'dependência inexistente: {node}')
    # Iterative DFS avoids a recursion limit on long valid dependency chains.
    done = set()
    for start in graph:
        visiting, stack = set(), [(start, False)]
        while stack:
            node, finish = stack.pop()
            if finish:
                visiting.remove(node)
                done.add(node)
            elif node not in done:
                require(node not in visiting, f'ciclo de dependência: {node}')
                visiting.add(node)
                stack.append((node, True))
                stack.extend((d, False) for d in reversed(graph[node]))
        # One installation cannot resolve two exact versions of the same ID.
        versions, pending, visited = {}, [start], set()
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            require(versions.get(node[0], node[1]) == node[1], f'conflito de versões nas dependências de {start}')
            versions[node[0]] = node[1]
            pending.extend(graph[node])
    packages.sort(key=lambda p: (p[0]['id'], tuple(map(int, p[0]['version'].split('.')))))
    return packages, {'schema': 1, 'versions': ledger}


def check_baseline(root, ledger, ref='HEAD'):
    # No repository is allowed for temporary test fixtures. Invalid refs fail closed.
    if not (root / '.git').exists():
        return
    result = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', f'{ref}^{{commit}}'], capture_output=True, text=True)
    require(result.returncode == 0, f'referência Git inválida: {ref}')
    commit = result.stdout.strip()
    listing = subprocess.run(['git', '-C', str(root), 'ls-tree', '--name-only', commit, '--', 'packages.lock.json'],
                             capture_output=True, text=True, check=True)
    if not listing.stdout.strip():
        return
    previous = parse_json(subprocess.run(['git', '-C', str(root), 'show', f'{commit}:packages.lock.json'],
                                        capture_output=True, check=True).stdout)
    for key, value in previous['versions'].items():
        require(ledger['versions'].get(key) == value, f'versão imutável alterada/removida: {key} ({ref})')


def validate(root, baseline='HEAD', update_lock=False):
    packages, ledger = sources(root)
    check_baseline(root, ledger, baseline)
    lock = root / 'packages.lock.json'
    if lock.exists():
        plain(lock)
        previous = parse_json(lock.read_bytes())
        for key, value in previous['versions'].items():
            require(ledger['versions'].get(key) == value, f'versão imutável alterada/removida: {key}')
        if not update_lock:
            require(previous == ledger, 'lock desatualizado; use validate_catalog.py --update-lock para novas versões')
    else:
        require(update_lock, 'packages.lock.json ausente; use --update-lock')
    if update_lock:
        render(packages)  # Do not freeze versions if the full catalog cannot be built.
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(dir=root, delete=False) as tmp:
            tmp.write(json_bytes(ledger))
            temp = Path(tmp.name)
        try:
            os.replace(temp, lock)
        finally:
            temp.unlink(missing_ok=True)
    return packages


def render(packages):
    entries, output = [], {}
    for manifest, files, directory in packages:
        entry = {k: v for k, v in manifest.items()
                 if k not in {'schema', 'files', 'origin', 'blocks'}}
        entry['dependencies'] = sorted(entry['dependencies'], key=lambda d: (d['id'], tuple(map(int, d['version'].split('.')))))
        entry['compatibility'] = dict(entry['compatibility'], boards=sorted(entry['compatibility']['boards']))
        prefix = f"packages/{entry['id']}/{entry['version']}/"
        entry['files'] = []
        for name, data in sorted(files.items()):
            url = prefix + name
            output['v1/' + url] = data
            entry['files'].append({'name': name, 'url': url, 'size': len(data), 'sha256': sha(data)})
        blocks = manifest.get('blocks')
        if blocks is not None:
            data = (directory / blocks['source']).read_bytes()
            url = prefix + 'blocks.json'
            output['v1/' + url] = data
            entry['blocks'] = {'url': url, 'size': len(data), 'sha256': sha(data)}
        # License travels with the public distribution, never just in the private Git repo.
        for metadata in ('LICENSE', 'UPSTREAM.json'):
            path = directory / metadata
            if path.exists():
                output['v1/' + prefix + metadata] = path.read_bytes()
        entry['license_url'] = prefix + 'LICENSE'
        if (directory / 'UPSTREAM.json').exists():
            entry['provenance_url'] = prefix + 'UPSTREAM.json'
        entries.append(entry)
    catalog = {'schema': 1, 'packages': entries}
    schema_check(catalog, parse_json((ROOT / 'schemas/catalog.schema.json').read_bytes()))
    output['v1/catalog.json'] = json_bytes(catalog)
    require(len(output['v1/catalog.json']) <= MAX_CATALOG, 'catálogo maior que 1 MiB')
    return output
