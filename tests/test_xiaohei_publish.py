"""Publishing failure must preserve the previous complete asset set."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('xiaohei_publish_generator', ROOT / 'scripts/build_xiaohei.py')
g = importlib.util.module_from_spec(spec); sys.modules[spec.name] = g; spec.loader.exec_module(g)


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.live = self.root / 'characters/xiaohei'
        self.live.mkdir(parents=True)
        (self.live / 'old.webp').write_bytes(b'old frame')
        (self.live / 'manifest.json').write_bytes(b'old manifest')
        self.stage = self.root / 'stage'; self.stage.mkdir()
        (self.stage / 'new.webp').write_bytes(b'new frame')
        self.manifest = {'clips': {'idle': {'frames': ['new.webp']}}}
        self.replace = g.os.replace

    def assert_old(self):
        self.assertEqual((self.live / 'old.webp').read_bytes(), b'old frame')
        self.assertEqual((self.live / 'manifest.json').read_bytes(), b'old manifest')
        self.assertFalse((self.live / 'new.webp').exists())

    def test_success_switches_whole_set(self):
        g.publish(self.stage, self.manifest, self.live)
        self.assertEqual((self.live / 'new.webp').read_bytes(), b'new frame')
        self.assertEqual(json.loads((self.live / 'manifest.json').read_text()), self.manifest)
        self.assertFalse((self.live / 'old.webp').exists())
        self.assertEqual(list(self.live.parent.iterdir()), [self.live])

    def test_copy_failure_leaves_old_set(self):
        with patch.object(g.shutil, 'copyfile', side_effect=OSError('copy failed')):
            with self.assertRaises(OSError):
                g.publish(self.stage, self.manifest, self.live)
        self.assert_old()

    def test_first_rename_failure_leaves_old_set(self):
        with patch.object(g.os, 'replace', side_effect=OSError('rename failed')):
            with self.assertRaises(OSError):
                g.publish(self.stage, self.manifest, self.live)
        self.assert_old()

    def test_second_rename_failure_restores_old_set(self):
        def fail_new(source, target):
            if '.xiaohei-publish-' in str(source):
                raise OSError('new directory move failed')
            return self.replace(source, target)
        with patch.object(g.os, 'replace', side_effect=fail_new):
            with self.assertRaises(OSError):
                g.publish(self.stage, self.manifest, self.live)
        self.assert_old()
        self.assertEqual(list(self.live.parent.iterdir()), [self.live])

    def test_failed_restore_keeps_recovery_directory(self):
        def fail_after_old(source, target):
            if Path(source) != self.live:
                raise OSError('publication and recovery unavailable')
            return self.replace(source, target)
        with patch.object(g.os, 'replace', side_effect=fail_after_old):
            with self.assertRaises(OSError):
                g.publish(self.stage, self.manifest, self.live)
        backups = list(self.live.parent.glob('.xiaohei-previous-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / 'old.webp').read_bytes(), b'old frame')
        self.assertEqual((backups[0] / 'manifest.json').read_bytes(), b'old manifest')


if __name__ == '__main__':
    unittest.main()
