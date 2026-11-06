#!/usr/bin/env python3
"""Build/verify the distributable Mozilla AMO ZIP, using only runtime files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
VERSION = MANIFEST['version']
DIST = ROOT / 'dist'
STAGING = DIST / 'amo'
OUTPUT = DIST / f'ELF-SHELL-Ayarime-v{VERSION}-AMO.zip'
SOURCES = [
    'LICENSE', 'LICENSE_SCOPE.md', 'LICENSES/MIT-legacy.txt', 'ARTWORK_LICENSE.md',
    'manifest.json', 'background.js', 'favicon.ico', 'newtab.html', 'newtab.js',
    'memory.js', 'feeds.js', 'styles.css', 'typography.css',
    'stories/archive.html', 'stories/archive.css', 'stories/archive.js',
    # Five reviewed, offline illustrated story masters only; no staging docs.
    *['stories/assets/' + name for name in (
        'letters-from-the-lower-city-01-04.png',
        'letters-from-the-lower-city-05-07.png',
        'crushed-rainforest-beans-01-04.png',
        'crushed-rainforest-beans-05-08.png',
        'crushed-rainforest-beans-09-12.png',
    )],
    'integration/background.js', 'integration/ui.js', 'integration/ui.css',
    # Runtime whitelist: never ship npm/vendor source or node_modules to AMO.
    *['spelling/' + name for name in (
        'DICTIONARY-LICENSE.txt', 'NSPELL-LICENSE.txt', 'IS-BUFFER-LICENSE.txt',
        'README.md', 'background.js', 'content.css', 'content.js',
        'en.aff', 'en.dic', 'nspell-bundle.js',
        'popup.css', 'popup.html', 'popup.js', 'worker.js'
    )],
]

def sources():
    # Use exactly the same reviewed source inventory as Mozilla's source ZIP.
    # In a clean checkout it comes from git ls-files; in the extracted reviewer
    # source archive it comes from AMO-SOURCE-MANIFEST.json. No recursive
    # filesystem scan may add untracked .env files or local build artifacts.
    from package_source import inventory
    tracked = set(inventory())
    required = set(SOURCES)
    missing = required - tracked
    if missing:
        raise ValueError('Untracked or missing required runtime file(s): ' + repr(sorted(missing)))
    asset_names = sorted(name for name in tracked if name.startswith('assets/'))
    return [ROOT / name for name in sorted(required | set(asset_names))]

def verify():
    if not OUTPUT.is_file() or not STAGING.is_dir():
        raise ValueError('No build available. First run scripts/package.py without --verify-only.')
    expected = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in sources()}
    with zipfile.ZipFile(OUTPUT) as zf:
        names = zf.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate file names in package')
        if set(names) != set(expected):
            raise ValueError(f'Package file mismatch: missing {set(expected)-set(names)}; extra {set(names)-set(expected)}')
        if any(zf.read(name) != expected[name] for name in names):
            raise ValueError('File content mismatch between release and source')
        if zf.testzip():
            raise ValueError('ZIP CRC check failed')
    if MANIFEST.get('browser_specific_settings',{}).get('gecko',{}).get('data_collection_permissions') != {'required': ['none']}:
        raise ValueError('Mozilla data declaration missing')
    if MANIFEST['browser_specific_settings']['gecko']['strict_min_version'] != '142.0':
        raise ValueError('Incorrect Firefox minimum version')
    if not MANIFEST.get('content_security_policy',{}).get('extension_pages'):
        raise ValueError('Missing restrictive CSP')
    for fn, relative in expected.items():
        if (STAGING / fn).read_bytes() != relative:
            raise ValueError('Staging file content changed: ' + fn)
    print(f'Verified AMO ZIP: {OUTPUT} ({len(expected)} files, {OUTPUT.stat().st_size:,} bytes)')
    print('SHA256:', hashlib.sha256(OUTPUT.read_bytes()).hexdigest())

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    try:
        if not args.verify_only:
            if STAGING.exists():
                shutil.rmtree(STAGING)
            STAGING.mkdir(parents=True)
            for file in sources():
                rel = file.relative_to(ROOT)
                dest = STAGING / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file, dest)
            with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for name in sorted(p.relative_to(ROOT).as_posix() for p in sources()):
                    info=zipfile.ZipInfo(name,(2026,11,4,0,0,0))
                    info.compress_type=zipfile.ZIP_DEFLATED
                    info.external_attr=(0o644 << 16)
                    zf.writestr(info,(ROOT/name).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        verify()
    except Exception as exc:
        print('FAILED:', exc, file=sys.stderr)
        sys.exit(1)
