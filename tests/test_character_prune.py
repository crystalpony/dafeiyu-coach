"""Conflict-copy pruning must compare manifest-relative paths, not basenames."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('character_prune', ROOT / 'scripts/prune_characters.py')
prune = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prune)


class CharacterPruneTests(unittest.TestCase):
    def test_same_basename_in_conflict_directory_is_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); char = root / 'xiaohei'
            for name in ('idle', 'idle 2'):
                (char / name).mkdir(parents=True)
            original = char / 'idle/idle_000.webp'; original.write_bytes(b'original')
            conflicts = [char / 'idle/idle_000 2.webp', char / 'idle 2/idle_000.webp']
            for path in conflicts:
                path.write_bytes(b'conflict')
            (char / 'manifest.json').write_text(json.dumps({'clips': {'idle': {'frames': ['idle/idle_000.webp']}}}))
            self.assertEqual(prune.main(temp), 0)
            self.assertEqual(original.read_bytes(), b'original')
            self.assertTrue(all(not path.exists() for path in conflicts))

    def test_invalid_or_empty_manifest_does_not_delete_assets(self):
        for manifest in ('invalid json', '{}'):
            with self.subTest(manifest=manifest), tempfile.TemporaryDirectory() as temp:
                char = Path(temp) / 'xiaohei'; char.mkdir()
                frame = char / 'frame.webp'; frame.write_bytes(b'keep')
                (char / 'manifest.json').write_text(manifest)
                prune.main(temp)
                self.assertEqual(frame.read_bytes(), b'keep')

    def test_legacy_basename_rule_would_keep_directory_conflict(self):
        reference = 'idle/idle_000.webp'
        conflict = 'idle 2/idle_000.webp'
        self.assertEqual(Path(reference).name, Path(conflict).name)
        self.assertNotEqual(reference, conflict)

    def test_snapshot_copies_only_referenced_bytes(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'source/xiaohei'; source.mkdir(parents=True)
            (source / 'good.webp').write_bytes(b'good')
            (source / 'good 2.webp').write_bytes(b'not referenced')
            data = json.dumps({'clips': {'idle': {'frames': ['good.webp'], 'sha256': [hashlib.sha256(b'good').hexdigest()]}}})
            (source / 'manifest.json').write_text(data)
            target = root / 'snapshot'
            self.assertEqual(prune.snapshot(str(source.parent), str(target)), 0)
            self.assertEqual((target / 'xiaohei/good.webp').read_bytes(), b'good')
            self.assertFalse((target / 'xiaohei/good 2.webp').exists())
            self.assertEqual((target / 'xiaohei/manifest.json').read_text(), data)

    def test_snapshot_rejects_changed_frame_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'source/xiaohei'; source.mkdir(parents=True)
            (source / 'bad.webp').write_bytes(b'changed')
            (source / 'manifest.json').write_text(json.dumps({'clips': {'idle': {'frames': ['bad.webp'], 'sha256': ['0' * 64]}}}))
            with self.assertRaisesRegex(ValueError, 'frame changed'):
                prune.snapshot(str(source.parent), str(root / 'snapshot'))

    def test_snapshot_rejects_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'keep').write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError, 'must be empty'):
                prune.snapshot(temp, temp)
            self.assertEqual((root / 'keep').read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
