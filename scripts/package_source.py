#!/usr/bin/env python3
"""Build a deterministic Mozilla reviewer source ZIP using tracked files only.

A clean Git checkout inventories tracked files; the resulting ZIP embeds its
own file inventory so the exact source archive can be rebuilt without .git.
No untracked files, credentials, local dependencies, or build outputs enter it.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
VERSION = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))['version']
OUTPUT = ROOT / 'dist' / f'ELF-SHELL-Ayarime-v{VERSION}-source.zip'
INVENTORY = 'AMO-SOURCE-MANIFEST.json'
SKIP_DIRS = {'node_modules', 'dist', '.git', '__pycache__', '.pytest_cache'}
REQUIRED = {
    'spelling/vendor/src/index.js', 'spelling/vendor/package.json',
    'spelling/vendor/package-lock.json', 'spelling/vendor/README.md',
    'scripts/verify-spelling.cjs', 'scripts/package.py',
    'scripts/package_source.py', 'spelling/nspell-bundle.js',
    'spelling/IS-BUFFER-LICENSE.txt', 'LICENSE', 'manifest.json',
    'package.json',
}

def inventory():
    if (ROOT / '.git').exists():
        # Tracked-only inventory avoids untracked scratch files and secrets.
        status = subprocess.run(
            ['git', 'status', '--porcelain=v1', '--untracked-files=no'],
            cwd=ROOT, capture_output=True, check=True
        )
        if status.stdout:
            raise ValueError('Refusing source archive with modified tracked files')
        tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT,
                                 capture_output=True, check=True).stdout
        names = [p.decode('utf-8') for p in tracked.split(b'\0') if p]
    else:
        # Firefox AMO reviewers receive an extracted ZIP with no Git metadata.
        manifest = ROOT / INVENTORY
        if not manifest.is_file():
            raise ValueError('Need a clean Git checkout or an extracted AMO source ZIP')
        value = json.loads(manifest.read_text(encoding='utf-8'))
        if value.get('format') != 'ayarime-amo-source-v1' or not isinstance(value.get('files'), list):
            raise ValueError('Invalid source inventory')
        names = value['files']
    result = []
    for name in names:
        if not isinstance(name, str) or not name:
            raise ValueError('Invalid tracked path')
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or name == INVENTORY:
            raise ValueError('Unsafe source path: ' + name)
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        file = ROOT / path
        if not file.is_file() or file.is_symlink():
            raise ValueError('Missing or unsafe source file: ' + name)
        result.append(name)
    if len(result) != len(set(result)):
        raise ValueError('Duplicate source paths')
    result.sort()
    missing = REQUIRED - set(result)
    if missing:
        raise ValueError('Required source inputs missing: ' + repr(sorted(missing)))
    return result

def build():
    names = inventory()
    manifest_bytes = (json.dumps({'format': 'ayarime-amo-source-v1', 'files': names},
                                ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    OUTPUT.parent.mkdir(exist_ok=True)
    entries = sorted([(name, (ROOT / name).read_bytes()) for name in names]
                     + [(INVENTORY, manifest_bytes)])
    with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, content in entries:
            info = zipfile.ZipInfo(name, (2026, 11, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    with zipfile.ZipFile(OUTPUT) as archive:
        if archive.namelist() != [name for name, _ in entries] or archive.testzip():
            raise ValueError('Source ZIP integrity verification failed')
        if any(archive.read(name) != content for name, content in entries):
            raise ValueError('Source ZIP contents changed')
    print(f'AMO reviewer source ZIP: {OUTPUT} ({len(entries)} files)')
    print('SHA256:', hashlib.sha256(OUTPUT.read_bytes()).hexdigest())

if __name__ == '__main__':
    try:
        build()
    except Exception as error:
        print('FAILED:', error, file=sys.stderr)
        sys.exit(1)
