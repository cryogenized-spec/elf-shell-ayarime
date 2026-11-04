#!/usr/bin/env python3
"""Assemble a deterministic, reviewable AMO *source* submission archive.

This is NOT the runtime extension ZIP. It includes the locked nspell build
inputs and complete project source, while excluding dependencies and local
outputs. Unlike blindly zipping a working tree, only explicit paths are used
so untracked secret files cannot accidentally enter the source submission.
"""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
VERSION = json.loads((ROOT / 'manifest.json').read_text())['version']
OUTPUT = ROOT / 'dist' / f'ELF-SHELL-Ayarime-v{VERSION}-source.zip'
ROOT_FILES = (
    '.gitignore', 'AGENTS.md', 'ARTWORK_LICENSE.md', 'CONTRIBUTING.md',
    'LICENSE', 'LICENSE_SCOPE.md', 'LIVE_FIREFOX_TESTS.md', 'PRIVACY.md',
    'README.md', 'RELEASE_CHECKLIST.md',
    'RELEASE_NOTES_0.5.1.md', 'RELEASE_NOTES_0.5.2.md',
    'RELEASE_NOTES_0.5.3.md', 'RELEASE_NOTES_0.5.4.md',
    'manifest.json', 'package.json', 'background.js', 'feeds.js',
    'newtab.html', 'newtab.js', 'memory.js', 'styles.css',
    'typography.css', 'favicon.ico',
)
SOURCE_FOLDERS = ('.github', 'assets', 'LICENSES', 'scripts', 'spelling', 'tests')
SKIP_DIRS = {'node_modules', 'dist', '.git', '__pycache__', '.pytest_cache'}
REQUIRED = {
    'spelling/vendor/src/index.js', 'spelling/vendor/package.json',
    'spelling/vendor/package-lock.json', 'spelling/vendor/README.md',
    'scripts/verify-spelling.cjs', 'scripts/package.py',
    'spelling/nspell-bundle.js', 'spelling/IS-BUFFER-LICENSE.txt',
}
def collect():
    listed = [ROOT / name for name in ROOT_FILES]
    for folder_name in SOURCE_FOLDERS:
        folder = ROOT / folder_name
        if not folder.is_dir():
            raise ValueError('Missing source folder: ' + folder_name)
        listed.extend(p for p in folder.rglob('*')
                      if p.is_file() and not any(part in SKIP_DIRS
                      for part in p.relative_to(ROOT).parts))
    expected = sorted({p.relative_to(ROOT).as_posix(): p for p in listed}.items())
    for name, file in expected:
        if not file.is_file():
            raise ValueError('Missing source file: ' + name)
        if file.is_symlink():
            raise ValueError('Symlinks are not allowed in source ZIP: ' + name)
    missing = REQUIRED - {name for name, _ in expected}
    if missing:
        raise ValueError('Missing AMO source inputs: ' + repr(missing))
    return expected

def build():
    expected = collect()
    OUTPUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, file in expected:
            info = zipfile.ZipInfo(name, (2026, 11, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    with zipfile.ZipFile(OUTPUT) as archive:
        names = archive.namelist()
        if names != [name for name, _ in expected] or archive.testzip():
            raise ValueError('Source ZIP failed integrity verification')
        if any('node_modules' in name.split('/') or name.startswith('dist/')
               for name in names):
            raise ValueError('Build dependencies or output slipped into source ZIP')
    print(f'AMO reviewer source ZIP: {OUTPUT} ({len(expected)} files)')
    print('SHA256:', hashlib.sha256(OUTPUT.read_bytes()).hexdigest())

if __name__ == '__main__':
    try:
        build()
    except Exception as error:
        print('FAILED:', error, file=sys.stderr)
        sys.exit(1)
