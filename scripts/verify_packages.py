#!/usr/bin/env python3
"""Validate ZIP CRC, SHA256SUMS and every packaged frame against workspace bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(directory):
    results = []
    entries = (directory / 'SHA256SUMS').read_text().splitlines()
    assert len(entries) == 2, 'expected exactly two current release packages'
    for entry in entries:
        expected, filename = entry.split()
        assert Path(filename).name == filename
        path = directory / filename
        actual = digest(path.read_bytes())
        assert actual == expected, f'archive SHA mismatch: {filename}'
        frames = 0
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None, f'CRC error: {filename}'
            names = archive.namelist()
            assert len(names) == len(set(names)), f'duplicate ZIP entries: {filename}'
            assert any(n.endswith('/NOTICE.md') for n in names), f'missing asset license: {filename}'
            expected_paths = set()
            for suffix, local in [('/clips/manifest.json', ROOT / 'Runtime/clips'),
                                  ('/characters/xiaohei/manifest.json', ROOT / 'Runtime/characters/xiaohei')]:
                matches = [n for n in names if n.endswith(suffix)]
                assert len(matches) == 1, f'expected one manifest {suffix}'
                manifest_name = matches[0]
                manifest = json.loads(archive.read(manifest_name))
                assert manifest == json.loads((local / 'manifest.json').read_text()), f'stale manifest: {filename}'
                prefix = manifest_name[:-len('manifest.json')]
                for clip in manifest['clips'].values():
                    assert len(clip['frames']) == clip['frameCount']
                    for i, rel in enumerate(clip['frames']):
                        stored = prefix + rel
                        data = archive.read(stored)
                        assert data == (local / rel).read_bytes(), f'stale frame {filename}: {rel}'
                        if 'sha256' in clip:
                            assert digest(data) == clip['sha256'][i], f'frame hash mismatch: {rel}'
                        frames += 1
                        expected_paths.add(stored)
            actual_paths = {n for n in names if n.endswith('.webp')}
            assert expected_paths == actual_paths, f'extra or missing WebP: {filename}'
            assert frames == 2882
        results.append({'file': filename, 'bytes': path.stat().st_size, 'sha256': actual,
                        'verifiedFrames': frames, 'crc': True, 'notice': True})
    return {'ok': True, 'packages': results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    report = verify(args.directory)
    (ROOT / 'audit/package-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
