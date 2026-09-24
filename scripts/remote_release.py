#!/usr/bin/env python3
"""Invoked over SSH by deploy.sh; never edits Caddy or TraceEdu."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

BASE = Path('/var/www/MicroARCA-libs')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def files(root):
    require(root.is_dir() and not root.is_symlink(), f'diretório inválido: {root}')
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), f'link proibido: {path}')
        if path.is_dir():
            continue
        require(path.is_file(), f'arquivo irregular: {path}')
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def digest(root):
    return hashlib.sha256(json.dumps(files(root), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_downloads(root):
    catalog = json.loads((root / 'v1/catalog.json').read_text(encoding='utf-8'))
    require(catalog.get('schema') == 1, 'schema remoto inválido')
    expected = {'v1/catalog.json'}
    for package in catalog['packages']:
        require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', package['id']), 'ID inválido')
        require(re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', package['version']), 'versão inválida')
        prefix = f"packages/{package['id']}/{package['version']}/"
        for file in package['files']:
            require(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*\.py', file['name']), 'nome inválido')
            require(file['url'] == prefix + file['name'], 'URL inválida')
            name = 'v1/' + file['url']
            expected.add(name)
            data = (root / name).read_bytes()
            require(len(data) == file['size'] <= 65536, f'tamanho inválido: {name}')
            require(hashlib.sha256(data).hexdigest() == file['sha256'], f'SHA-256 inválido: {name}')
        for key, name in [('license_url', 'LICENSE'), ('provenance_url', 'UPSTREAM.json')]:
            if key in package:
                require(package[key] == prefix + name, 'URL de metadados inválida')
                expected.add('v1/' + package[key])
        blocks = package.get('blocks')
        if blocks is not None:
            require(
                set(blocks) == {'url', 'size', 'sha256'},
                'metadados de blocos inválidos',
            )
            require(blocks['url'] == prefix + 'blocks.json', 'URL de blocos inválida')
            name = 'v1/' + blocks['url']
            expected.add(name)
            data = (root / name).read_bytes()
            require(0 < len(data) == blocks['size'] <= 65536,
                    f'tamanho inválido: {name}')
            require(hashlib.sha256(data).hexdigest() == blocks['sha256'],
                    f'SHA-256 inválido: {name}')
    require(set(files(root)) == expected, 'conteúdo inesperado ou ausente no release')


def operation(base, action, commit, token, expected):
    require(re.fullmatch(r'[a-f0-9]{40}', commit), 'commit inválido')
    require(re.fullmatch(r'[a-f0-9]{32}', token), 'token inválido')
    require(re.fullmatch(r'[a-f0-9]{64}', expected), 'digest inválido')
    require(base.is_dir() and not base.is_symlink(), 'infraestrutura ausente; preparar somente após autorização')
    releases = base / 'releases'
    require(releases.is_dir() and not releases.is_symlink(), 'diretório releases inválido')
    lock = base / '.deploy-lock'
    incoming = base / f'.incoming-{commit}-{token}'
    current = base / 'current'
    temporary_link = base / f'.current-{token}'
    if action == 'prepare':
        lock.mkdir(mode=0o700)  # Exclusive across deployments, including the transfer.
        (lock / 'owner').write_text(token, encoding='ascii')
        incoming.mkdir(mode=0o755)
        print(f'Release temporário preparado: {incoming}')
        return
    require(lock.is_dir() and not lock.is_symlink() and (lock / 'owner').read_text() == token,
            'lock remoto não pertence a esta implantação')
    if action == 'abort':
        if incoming.exists():
            require(not incoming.is_symlink(), 'incoming inválido')
            shutil.rmtree(incoming)
        temporary_link.unlink(missing_ok=True)
        (lock / 'owner').unlink()
        lock.rmdir()
        return
    require(digest(incoming) == expected, 'transferência incompleta ou divergente')
    validate_downloads(incoming)
    new_files = files(incoming)
    catalog = json.loads((incoming / 'v1/catalog.json').read_text(encoding='utf-8'))
    entries = {(p['id'], p['version']): p for p in catalog['packages']}
    for previous in releases.iterdir():
        require(re.fullmatch(r'[a-f0-9]{40}', previous.name), 'release anterior inesperado')
        for name, checksum in files(previous).items():
            if name.startswith('v1/packages/'):
                require(new_files.get(name) == checksum, f'arquivo publicado imutável alterado/removido: {name}')
        old_catalog = json.loads((previous / 'v1/catalog.json').read_text(encoding='utf-8'))
        for package in old_catalog['packages']:
            key = (package['id'], package['version'])
            require(entries.get(key) == package, f'metadados publicados imutáveis alterados/removidos: {key}')
    if current.exists() or current.is_symlink():
        require(current.is_symlink(), 'current não é um link simbólico')
        require(re.fullmatch(r'releases/[a-f0-9]{40}', os.readlink(current)), 'destino current inválido')
        require(current.is_dir(), 'current aponta para release ausente')
    destination = releases / commit
    if destination.exists():
        require(digest(destination) == expected, 'commit remoto já existe com conteúdo diferente')
        shutil.rmtree(incoming)
    else:
        incoming.rename(destination)
    temporary_link.symlink_to(f'releases/{commit}')
    os.replace(temporary_link, current)
    (lock / 'owner').unlink()
    lock.rmdir()
    print(f'Publicado: current -> releases/{commit}. Releases anteriores preservados.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'finalize', 'abort', 'digest'])
    parser.add_argument('args', nargs='+')
    args = parser.parse_args()
    try:
        if args.action == 'digest':
            print(digest(Path(args.args[0])))
        else:
            operation(BASE, args.action, *args.args)
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
