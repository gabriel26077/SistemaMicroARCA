import json
from pathlib import Path
import tempfile
import unittest

from scripts.registry import json_bytes, validate


class RegistryCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.add_package('alpha')

    def add_package(self, id_, version='1.0.0', dependencies=None, filename=None):
        directory = self.root / 'packages' / id_ / version
        directory.mkdir(parents=True)
        filename = filename or id_.replace('-', '_') + '.py'
        manifest = {'schema': 1, 'id': id_, 'name': id_, 'version': version,
                    'description': 'Example', 'author': 'ARCA', 'license': 'MIT',
                    'homepage': '', 'origin': 'first-party',
                    'compatibility': {'micropython': '>=1.24', 'boards': ['ESP32_GENERIC']},
                    'dependencies': dependencies or [], 'files': [{'source': filename, 'install_as': filename}]}
        (directory / 'manifest.json').write_bytes(json_bytes(manifest))
        (directory / filename).write_bytes(b'value = 1\r\n')
        (directory / 'LICENSE').write_text('MIT fixture license\n')
        return directory

    @property
    def directory(self):
        return self.root / 'packages/alpha/1.0.0'

    def modify(self, fn, directory=None):
        path = (directory or self.directory) / 'manifest.json'
        manifest = json.loads(path.read_bytes())
        fn(manifest)
        path.write_bytes(json_bytes(manifest))

    def add_blocks(self, directory=None):
        directory = directory or self.directory
        manifest_path = directory / 'manifest.json'
        manifest = json.loads(manifest_path.read_bytes())
        manifest['blocks'] = {'source': 'blocks.json'}
        manifest_path.write_bytes(json_bytes(manifest))
        block_type = manifest['id'].replace('-', '_') + '_acao'
        value = {
            'schema': 1,
            'package': {'id': manifest['id'], 'version': manifest['version']},
            'category': {'name': 'Example blocks', 'color': '#336699'},
            'blocks': [{
                'type': block_type,
                'name': 'Action',
                'description': 'Runs one action.',
                'label': 'use object {OBJECT}',
                'fields': [
                    {'name': 'OBJECT', 'type': 'identifier', 'default': 'device'},
                ],
                'python': {'imports': [], 'template': '{OBJECT}.run()\n'},
            }],
        }
        (directory / 'blocks.json').write_bytes(json_bytes(value))
        return directory / 'blocks.json'

    def lock(self):
        validate(self.root, update_lock=True)
