import hashlib
import json
import subprocess
import sys
from unittest.mock import patch

from scripts.build_catalog import build
from scripts.registry import Invalid, ROOT, inventory
from tests.support import RegistryCase


class BuildTests(RegistryCase):
    def setUp(self):
        super().setUp()
        self.lock()

    def test_deterministic_and_binary_copy(self):
        build(self.root)
        before = inventory(self.root / 'dist')
        build(self.root)
        self.assertEqual(before, inventory(self.root / 'dist'))
        self.assertEqual(before['v1/packages/alpha/1.0.0/alpha.py'], b'value = 1\r\n')

    def test_hash_size_relative_urls_and_license(self):
        build(self.root)
        catalog = json.loads((self.root / 'dist/v1/catalog.json').read_bytes())
        file = catalog['packages'][0]['files'][0]
        original = (self.directory / 'alpha.py').read_bytes()
        self.assertEqual(file['sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(file['size'], len(original))
        self.assertEqual(file['url'], 'packages/alpha/1.0.0/alpha.py')
        self.assertNotIn('generated_at', catalog)
        self.assertEqual((self.root / 'dist/v1' / catalog['packages'][0]['license_url']).read_bytes(),
                         (self.directory / 'LICENSE').read_bytes())

    def test_hashes_and_copies_declarative_blocks(self):
        directory = self.add_package('alpha', '1.0.1')
        path = self.add_blocks(directory)
        self.lock()
        build(self.root)
        catalog = json.loads((self.root / 'dist/v1/catalog.json').read_bytes())
        package = next(item for item in catalog['packages'] if item['version'] == '1.0.1')
        blocks = package['blocks']
        original = path.read_bytes()
        self.assertEqual(blocks['url'], 'packages/alpha/1.0.1/blocks.json')
        self.assertEqual(blocks['size'], len(original))
        self.assertEqual(blocks['sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(
            (self.root / 'dist/v1' / blocks['url']).read_bytes(),
            original,
        )

    def test_sort_versions_numerically(self):
        self.add_package('alpha', '1.10.0')
        self.add_package('alpha', '1.2.0')
        self.lock()
        build(self.root)
        catalog = json.loads((self.root / 'dist/v1/catalog.json').read_bytes())
        self.assertEqual([p['version'] for p in catalog['packages']], ['1.0.0', '1.2.0', '1.10.0'])

    def test_check_detects_stale_catalog_without_writing(self):
        build(self.root)
        path = self.root / 'dist/v1/catalog.json'
        path.write_text('{}')
        before = inventory(self.root / 'dist')
        with self.assertRaisesRegex(Invalid, 'desatualizado'):
            build(self.root, check=True)
        self.assertEqual(before, inventory(self.root / 'dist'))

    def test_check_detects_extra_file_and_empty_directory(self):
        build(self.root)
        extra = self.root / 'dist/extra'
        extra.mkdir()
        with self.assertRaises(Invalid):
            build(self.root, check=True)
        extra.rmdir()
        extra.write_text('unexpected')
        with self.assertRaises(Invalid):
            build(self.root, check=True)

    def test_cli_check_exit_codes(self):
        command = [sys.executable, str(ROOT / 'scripts/build_catalog.py'), '--root', str(self.root), '--check']
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        build(self.root)
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        (self.root / 'dist/v1/catalog.json').write_text('{}')
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)

    def test_atomic_exchange_failure_preserves_old_tree(self):
        build(self.root)
        before = inventory(self.root / 'dist')
        self.add_package('alpha', '1.0.1')
        self.lock()
        with patch('scripts.build_catalog.exchange', side_effect=OSError('simulated failure')):
            with self.assertRaises(OSError):
                build(self.root)
        self.assertEqual(before, inventory(self.root / 'dist'))
        self.assertEqual(list(self.root.glob('.catalog-stage-*')), [])

    def test_atomic_exchange_sees_two_complete_trees(self):
        from scripts.build_catalog import exchange
        build(self.root)
        before = inventory(self.root / 'dist')
        self.add_package('alpha', '1.0.1')
        self.lock()
        def inspect(stage, dist):
            self.assertEqual(inventory(dist), before)
            self.assertIn('v1/packages/alpha/1.0.1/alpha.py', inventory(stage))
            exchange(stage, dist)
        with patch('scripts.build_catalog.exchange', side_effect=inspect):
            build(self.root)
        build(self.root, check=True)

    def test_write_failure_preserves_old_tree(self):
        build(self.root)
        before = inventory(self.root / 'dist')
        self.add_package('alpha', '1.0.1')
        self.lock()
        with patch('scripts.build_catalog.os.fsync', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                build(self.root)
        self.assertEqual(inventory(self.root / 'dist'), before)

    def test_validation_failure_preserves_old_tree(self):
        build(self.root)
        before = inventory(self.root / 'dist')
        (self.directory / 'alpha.py').write_bytes(b'\xff')
        with self.assertRaises(Invalid):
            build(self.root)
        self.assertEqual(inventory(self.root / 'dist'), before)
