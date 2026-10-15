#!/usr/bin/env python3
"""Install the pinned official Open Image Denoise CPU tools for the renderer."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import platform
import tarfile
import tempfile
import urllib.request


VERSION = '2.5.1'
ARCHIVE = f'oidn-{VERSION}.x86_64.linux.tar.gz'
URL = f'https://github.com/RenderKit/oidn/releases/download/v{VERSION}/{ARCHIVE}'
SHA256 = '743c3e2aff8c220d5d70fe6cb970fb3d36f2702d2693c61d1d148e404cf37cd6'
DEFAULT_CACHE = Path('/workspace/.nvxram-tools')


def ensure_oidn(cache_dir: Path = DEFAULT_CACHE) -> Path:
    binary = cache_dir / f'oidn-{VERSION}.x86_64.linux/bin/oidnDenoise'
    if binary.is_file():
        return binary
    if platform.system() != 'Linux' or platform.machine() not in {'x86_64', 'AMD64'}:
        raise SystemExit('This pinned OIDN package requires Linux x86_64.')
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nvxram-oidn-') as temporary:
        archive_path = Path(temporary) / ARCHIVE
        digest = hashlib.sha256()
        # urllib preserves the inherited proxy and normal certificate checks.
        with urllib.request.urlopen(URL, timeout=60) as response, archive_path.open('wb') as target:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                target.write(chunk)
        if digest.hexdigest() != SHA256:
            raise SystemExit('Official OIDN archive checksum mismatch; installation stopped.')
        with tarfile.open(archive_path, 'r:gz') as archive:
            archive.extractall(cache_dir, filter='data')
    if not binary.is_file():
        raise SystemExit('OIDN archive did not contain the expected CPU executable.')
    return binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    print(ensure_oidn(args.cache_dir))


if __name__ == '__main__':
    main()
