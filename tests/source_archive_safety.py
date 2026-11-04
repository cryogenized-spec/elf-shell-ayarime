#!/usr/bin/env python3
"""AMO source ZIP must never capture an untracked file and must rebuild sans Git."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'manifest.json'
import json
VERSION = json.loads(MANIFEST.read_text())['version']
NAME = f'ELF-SHELL-Ayarime-v{VERSION}-source.zip'
ZIP = ROOT / 'dist' / NAME
SCRATCH = ROOT / 'scripts' / 'review-untracked-secret.env'
assert not SCRATCH.exists(), 'test refuses to replace existing scratch file'

def run(script):
    subprocess.run([sys.executable, str(script)], cwd=script.parent.parent,
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

run(ROOT / 'scripts' / 'package_source.py')
baseline = hashlib.sha256(ZIP.read_bytes()).digest()
SCRATCH.write_text('DO_NOT_SHIP_UNTRACKED_CREDENTIALS=test', encoding='utf-8')
try:
    run(ROOT / 'scripts' / 'package_source.py')
    assert hashlib.sha256(ZIP.read_bytes()).digest() == baseline, (
        'untracked file altered source archive')
    with zipfile.ZipFile(ZIP) as archive:
        assert 'scripts/review-untracked-secret.env' not in archive.namelist()
        assert 'AMO-SOURCE-MANIFEST.json' in archive.namelist()
        assert 'spelling/vendor/package-lock.json' in archive.namelist()
        with tempfile.TemporaryDirectory() as folder:
            archive.extractall(folder)
            unpacked = Path(folder)
            assert not (unpacked / '.git').exists()
            run(unpacked / 'scripts' / 'package_source.py')
            regenerated = unpacked / 'dist' / NAME
            assert regenerated.read_bytes() == ZIP.read_bytes(), (
                'source ZIP must be byte-identical without Git metadata')
finally:
    SCRATCH.unlink(missing_ok=True)
print('AMO source QA PASS: excludes untracked files and rebuilds byte-identically from ZIP.')
