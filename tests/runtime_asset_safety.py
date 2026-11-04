#!/usr/bin/env python3
"""Test that runtime AMO ZIP excludes local files and rebuilds from source ZIP."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
VERSION = json.loads((ROOT / 'manifest.json').read_text())['version']
ZIP_NAME = f'ELF-SHELL-Ayarime-v{VERSION}-AMO.zip'
SOURCE_NAME = f'ELF-SHELL-Ayarime-v{VERSION}-source.zip'
AMO_ZIP = ROOT / 'dist' / ZIP_NAME
SOURCE_ZIP = ROOT / 'dist' / SOURCE_NAME
SCRATCH = ROOT / 'assets' / 'review-untracked-secret.env'
assert not SCRATCH.exists(), 'test refuses to overwrite a pre-existing file'

def build(root):
    subprocess.run([sys.executable, str(root / 'scripts' / 'package.py')],
                   cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

build(ROOT)
baseline = AMO_ZIP.read_bytes()
sha = hashlib.sha256(baseline).hexdigest()
assert len(baseline) > 1000, 'baseline zip unexpectedly empty'

SCRATCH.write_text('DO_NOT_SHIP_UNTRACKED_CREDENTIALS=test', encoding='utf-8')
try:
    # Filesystem scanners accidentally include this, and a source/runtime
    # mismatch passes their verification if it reuses that same scanner.
    build(ROOT)
    assert hashlib.sha256(AMO_ZIP.read_bytes()).hexdigest() == sha, (
        'untracked asset altered the runtime ZIP')
    with zipfile.ZipFile(AMO_ZIP) as archive:
        assert 'assets/review-untracked-secret.env' not in archive.namelist()
        assert all('vendor/' not in n and '/node_modules/' not in n
                   for n in archive.namelist())
finally:
    SCRATCH.unlink(missing_ok=True)

# Mozilla reviewers must be able to recreate the *identical* runtime extension
# from only our separate source ZIP, without .git or untracked project files.
assert SOURCE_ZIP.is_file(), 'create the Mozilla source archive first'
with zipfile.ZipFile(SOURCE_ZIP) as source:
    with tempfile.TemporaryDirectory() as directory:
        source.extractall(directory)
        root = Path(directory)
        assert not (root / '.git').exists()
        build(root)
        assert (root / 'dist' / ZIP_NAME).read_bytes() == baseline, (
            'AMO extension ZIP must be reproducible from submitted source ZIP')
print('Runtime ZIP QA PASS: untracked asset excluded, deterministic, reconstructable without Git.')
