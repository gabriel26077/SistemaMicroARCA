import os
import io
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from scripts.build_catalog import build
from scripts.remote_release import digest, operation, validate_downloads
from tests.support import RegistryCase


class ReleaseTests(RegistryCase):
    def setUp(self):
        super().setUp()
        self.stdout = patch('sys.stdout', new_callable=io.StringIO)
        self.stdout.start()
        self.addCleanup(self.stdout.stop)
        self.lock()
        build(self.root)
        self.base = self.root / 'remote'
        (self.base / 'releases').mkdir(parents=True)
        self.commit = 'a' * 40
        self.token = 'b' * 32

    def prepare(self, commit=None):
        commit = commit or self.commit
        checksum = digest(self.root / 'dist')
        operation(self.base, 'prepare', commit, self.token, checksum)
        incoming = self.base / f'.incoming-{commit}-{self.token}'
        shutil.copytree(self.root / 'dist', incoming, dirs_exist_ok=True)
        return incoming, checksum

    def publish(self, commit=None):
        _, checksum = self.prepare(commit)
        operation(self.base, 'finalize', commit or self.commit, self.token, checksum)

    def test_complete_release_and_idempotent_redeploy(self):
        self.publish()
        self.assertEqual(os.readlink(self.base / 'current'), f'releases/{self.commit}')
        validate_downloads((self.base / 'current').resolve())
        self.publish()

    def test_failed_transfer_preserves_current(self):
        self.publish()
        commit = 'c' * 40
        incoming, checksum = self.prepare(commit)
        (incoming / 'v1/catalog.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'transferência'):
            operation(self.base, 'finalize', commit, self.token, checksum)
        self.assertEqual(os.readlink(self.base / 'current'), f'releases/{self.commit}')
        operation(self.base, 'abort', commit, self.token, checksum)
        self.assertFalse(incoming.exists())

    def test_prior_release_retained_and_rollback(self):
        self.publish()
        self.add_package('alpha', '1.0.1')
        self.lock()
        build(self.root)
        self.publish('c' * 40)
        self.assertTrue((self.base / 'releases' / self.commit).is_dir())
        link = self.base / '.rollback'
        link.symlink_to(f'releases/{self.commit}')
        os.replace(link, self.base / 'current')
        validate_downloads((self.base / 'current').resolve())
        self.assertTrue((self.base / 'releases' / ('c' * 40)).is_dir())

    def test_preexisting_immutable_file_cannot_change(self):
        self.publish()
        # Bypass the local lock to simulate a compromised/re-written local history.
        path = self.root / 'dist/v1/packages/alpha/1.0.0/LICENSE'
        path.write_text('changed license')
        incoming, checksum = self.prepare('c' * 40)
        with self.assertRaisesRegex(ValueError, 'imutável'):
            operation(self.base, 'finalize', 'c' * 40, self.token, checksum)
        self.assertEqual(os.readlink(self.base / 'current'), f'releases/{self.commit}')

    def test_lock_blocks_concurrent_deployment(self):
        _, checksum = self.prepare()
        with self.assertRaises(FileExistsError):
            operation(self.base, 'prepare', 'c' * 40, 'd' * 32, checksum)

    def test_published_catalog_metadata_is_immutable(self):
        self.publish()
        path = self.root / 'dist/v1/catalog.json'
        catalog = json.loads(path.read_bytes())
        catalog['packages'][0]['description'] = 'Changed description'
        path.write_text(json.dumps(catalog))
        _, checksum = self.prepare('c' * 40)
        with self.assertRaisesRegex(ValueError, 'metadados publicados imutáveis'):
            operation(self.base, 'finalize', 'c' * 40, self.token, checksum)

    def test_other_owner_cannot_abort(self):
        _, checksum = self.prepare()
        with self.assertRaisesRegex(ValueError, 'não pertence'):
            operation(self.base, 'abort', self.commit, 'd' * 32, checksum)

    def test_symlink_rejected(self):
        incoming, checksum = self.prepare()
        (incoming / 'bad').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'link proibido'):
            operation(self.base, 'finalize', self.commit, self.token, checksum)

    def test_failed_current_swap_preserves_previous(self):
        self.publish()
        commit = 'c' * 40
        _, checksum = self.prepare(commit)
        with patch('scripts.remote_release.os.replace', side_effect=OSError('simulated')):
            with self.assertRaises(OSError):
                operation(self.base, 'finalize', commit, self.token, checksum)
        self.assertEqual(os.readlink(self.base / 'current'), f'releases/{self.commit}')
        operation(self.base, 'abort', commit, self.token, checksum)
        self.assertTrue((self.base / 'releases' / commit).is_dir())
