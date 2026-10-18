import json
import subprocess
from unittest.mock import patch

from scripts.registry import Invalid, RESERVED, ROOT, json_bytes, sources, validate
from tests.support import RegistryCase


class ValidationTests(RegistryCase):
    def test_valid_catalog(self):
        self.lock()
        self.assertEqual(len(validate(self.root)), 1)

    def test_real_packages(self):
        identities = {(m['id'], m['version']) for m, _, _ in validate(ROOT)}
        self.assertTrue({('oled-pintor', '1.0.0'), ('ssd1306', '1.0.0')} <= identities)

    def test_limit_exactly_64_kib(self):
        (self.directory / 'alpha.py').write_bytes(b'#' + b'x' * 65535)
        sources(self.root)

    def test_oversized(self):
        (self.directory / 'alpha.py').write_bytes(b'#' + b'x' * 65536)
        with self.assertRaisesRegex(Invalid, '64 KiB'):
            sources(self.root)

    def test_invalid_names_and_traversal(self):
        for name in ['a-b.py', '1foo.py', 'á.py', 'a/b.py', '../a.py', '..\\a.py',
                     'a..py', 'a\n.py', 'a\x00.py', 'foo.txt', 'class.py', '/a.py']:
            with self.subTest(name=name):
                self.modify(lambda m: m['files'][0].update(install_as=name))
                with self.assertRaises(Invalid):
                    sources(self.root)

    def test_reserved_names(self):
        for name in RESERVED | {'Boot.py'}:
            with self.subTest(name=name):
                self.modify(lambda m: m['files'][0].update(install_as=name))
                with self.assertRaisesRegex(Invalid, 'reservado'):
                    sources(self.root)

    def test_source_traversal(self):
        self.modify(lambda m: m['files'][0].update(source='../alpha.py'))
        with self.assertRaises(Invalid):
            sources(self.root)

    def test_invalid_utf8(self):
        (self.directory / 'alpha.py').write_bytes(b'# coding: latin-1\n#\xff')
        with self.assertRaisesRegex(Invalid, 'UTF-8'):
            sources(self.root)

    def test_invalid_syntax(self):
        (self.directory / 'alpha.py').write_text('def foo(:\n')
        with self.assertRaisesRegex(Invalid, 'Python/UTF-8'):
            sources(self.root)

    def test_no_code_execution(self):
        (self.directory / 'alpha.py').write_text('raise RuntimeError("must not execute")\n')
        sources(self.root)

    def test_valid_declarative_blocks(self):
        self.add_blocks()
        packages, _ = sources(self.root)
        self.assertEqual(packages[0][0]['blocks'], {'source': 'blocks.json'})

    def test_blocks_accept_printable_value_field(self):
        path = self.add_blocks()
        value = json.loads(path.read_bytes())
        field = value['blocks'][0]['fields'][0]
        field.update(type='value', default='Contagem: ')
        path.write_bytes(json_bytes(value))
        sources(self.root)

        field['default'] = ['not', 'printable']
        path.write_bytes(json_bytes(value))
        with self.assertRaisesRegex(Invalid, 'valor exibivel'):
            sources(self.root)

    def test_dropdown_options_are_validated(self):
        path = self.add_blocks()
        value = json.loads(path.read_bytes())
        field = value['blocks'][0]['fields'][0]
        field.clear()
        field.update(name='TELA', type='dropdown', default='A', options=[['Do', 'C'], ['La', 'A']])
        # Preserve the original field name used by the fixture's label/template.
        original = json.loads((self.add_blocks()).read_bytes())
        field['name'] = original['blocks'][0]['fields'][0]['name']
        path.write_bytes(json_bytes(value))
        sources(self.root)
        for change in ({'default': 'B'}, {'options': []},
                       {'options': [['Do', 'C'], ['Other', 'C']]},
                       {'options': [['Do', 1]]}, {'min': 0},
                       {'type': 'text'}):
            invalid = json.loads(json.dumps(value))
            invalid['blocks'][0]['fields'][0].update(change)
            path.write_bytes(json_bytes(invalid))
            with self.subTest(change=change), self.assertRaises(Invalid):
                sources(self.root)

    def test_blocks_must_match_package_and_fields(self):
        path = self.add_blocks()
        value = json.loads(path.read_bytes())
        value['package']['id'] = 'other'
        path.write_bytes(json_bytes(value))
        with self.assertRaisesRegex(Invalid, 'outro pacote'):
            sources(self.root)

        value['package']['id'] = 'alpha'
        value['blocks'][0]['python']['template'] = 'pass\n'
        path.write_bytes(json_bytes(value))
        with self.assertRaisesRegex(Invalid, 'diverge'):
            sources(self.root)

    def test_blocks_reject_unknown_javascript_hook(self):
        self.add_blocks()
        self.modify(lambda manifest: manifest['blocks'].update(javascript='plugin.js'))
        with self.assertRaisesRegex(Invalid, 'campos desconhecidos'):
            sources(self.root)

    def test_missing_dependency(self):
        self.modify(lambda m: m.update(dependencies=[{'id': 'missing', 'version': '1.0.0'}]))
        with self.assertRaisesRegex(Invalid, 'inexistente'):
            sources(self.root)

    def test_dependency_cycle(self):
        self.add_package('beta', dependencies=[{'id': 'alpha', 'version': '1.0.0'}])
        self.modify(lambda m: m.update(dependencies=[{'id': 'beta', 'version': '1.0.0'}]))
        with self.assertRaisesRegex(Invalid, 'ciclo'):
            sources(self.root)

    def test_self_cycle(self):
        self.modify(lambda m: m.update(dependencies=[{'id': 'alpha', 'version': '1.0.0'}]))
        with self.assertRaisesRegex(Invalid, 'ciclo'):
            sources(self.root)

    def test_dependency_diamond(self):
        self.add_package('delta')
        for id_ in ['beta', 'gamma']:
            self.add_package(id_, dependencies=[{'id': 'delta', 'version': '1.0.0'}])
        self.modify(lambda m: m.update(dependencies=[{'id': id_, 'version': '1.0.0'} for id_ in ['beta', 'gamma']]))
        sources(self.root)

    def test_dependency_version_conflict(self):
        self.add_package('delta')
        self.add_package('delta', '2.0.0')
        self.add_package('beta', dependencies=[{'id': 'delta', 'version': '1.0.0'}])
        self.add_package('gamma', dependencies=[{'id': 'delta', 'version': '2.0.0'}])
        self.modify(lambda m: m.update(dependencies=[{'id': id_, 'version': '1.0.0'} for id_ in ['beta', 'gamma']]))
        with self.assertRaisesRegex(Invalid, 'conflito de versões'):
            sources(self.root)

    def test_invalid_versions(self):
        for version in ['1.0', '01.0.0', '1.0.0-beta', '../1.0.0', '1.0.0\n']:
            with self.subTest(version=version):
                self.modify(lambda m: m.update(version=version))
                with self.assertRaises(Invalid):
                    sources(self.root)

    def test_invalid_ids(self):
        for id_ in ['Alpha', '../alpha', 'a_b', 'alpha\n', '']:
            with self.subTest(id=id_):
                self.modify(lambda m: m.update(id=id_))
                with self.assertRaises(Invalid):
                    sources(self.root)

    def test_duplicate_file_owners(self):
        self.add_package('beta', filename='alpha.py')
        with self.assertRaisesRegex(Invalid, 'dois pacotes'):
            sources(self.root)

    def test_same_module_across_versions_allowed(self):
        self.add_package('alpha', '2.0.0')
        sources(self.root)

    def test_duplicate_manifest_identity(self):
        directory = self.add_package('beta')
        self.modify(lambda m: m.update(id='alpha'), directory)
        with self.assertRaisesRegex(Invalid, 'duplicados'):
            sources(self.root)

    def test_duplicate_json_keys(self):
        path = self.directory / 'manifest.json'
        path.write_text(path.read_text().replace('"schema": 1', '"schema": 1, "schema": 1'))
        with self.assertRaisesRegex(Invalid, 'chave JSON duplicada'):
            sources(self.root)

    def test_duplicate_declared_file(self):
        self.modify(lambda m: m['files'].append(dict(m['files'][0])))
        with self.assertRaises(Invalid):
            sources(self.root)

    def test_missing_declared_file(self):
        (self.directory / 'alpha.py').unlink()
        with self.assertRaisesRegex(Invalid, 'ausente'):
            sources(self.root)

    def test_undeclared_file(self):
        (self.directory / 'extra.py').write_text('pass\n')
        with self.assertRaisesRegex(Invalid, 'não declarado'):
            sources(self.root)

    def test_symlink_file(self):
        (self.directory / 'alpha.py').unlink()
        (self.directory / 'alpha.py').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(Invalid, 'link simbólico'):
            sources(self.root)

    def test_extra_nested_manifest(self):
        (self.directory / 'nested').mkdir()
        (self.directory / 'nested/manifest.json').write_text('{}')
        with self.assertRaises(Invalid):
            sources(self.root)

    def test_unknown_hook(self):
        self.modify(lambda m: m.update(install_hook='evil.py'))
        with self.assertRaisesRegex(Invalid, 'desconhecidos'):
            sources(self.root)

    def test_boolean_schema_is_not_integer(self):
        self.modify(lambda m: m.update(schema=True))
        with self.assertRaises(Invalid):
            sources(self.root)

    def test_missing_license(self):
        (self.directory / 'LICENSE').unlink()
        with self.assertRaisesRegex(Invalid, 'licença'):
            sources(self.root)

    def test_third_party_missing_provenance(self):
        self.modify(lambda m: m.update(origin='third-party'))
        with self.assertRaisesRegex(Invalid, 'UPSTREAM'):
            sources(self.root)

    def test_third_party_requires_exact_commit(self):
        self.modify(lambda m: m.update(origin='third-party', homepage='https://example.org'))
        (self.directory / 'UPSTREAM.json').write_bytes(json_bytes({'repository': 'https://example.org',
            'commit': 'master', 'version': '1.0.0', 'source_url': 'https://example.org/source',
            'license_url': 'https://example.org/license', 'license': 'MIT'}))
        with self.assertRaisesRegex(Invalid, 'formato'):
            sources(self.root)

    def test_lock_rejects_modification(self):
        self.lock()
        (self.directory / 'alpha.py').write_text('value = 2\n')
        for update in [False, True]:
            with self.assertRaisesRegex(Invalid, 'imutável'):
                validate(self.root, update_lock=update)

    def test_lock_allows_only_new_versions(self):
        self.lock()
        self.add_package('alpha', '1.0.1')
        with self.assertRaisesRegex(Invalid, 'desatualizado'):
            validate(self.root)
        self.lock()
        self.assertEqual(len(validate(self.root)), 2)

    def test_git_baseline_catches_rewritten_lock(self):
        self.lock()
        def git(*args):
            return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        git('init')
        git('add', '.')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'initial')
        (self.directory / 'alpha.py').write_text('value = 2\n')
        _, ledger = sources(self.root)
        (self.root / 'packages.lock.json').write_bytes(json_bytes(ledger))
        with self.assertRaisesRegex(Invalid, 'imutável'):
            validate(self.root)

    def test_bad_baseline_ref_fails_closed(self):
        self.test_git_baseline_catches_rewritten_lock()
        with self.assertRaisesRegex(Invalid, 'referência Git inválida'):
            validate(self.root, baseline='missing-ref')
