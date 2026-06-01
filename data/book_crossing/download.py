# -*- coding: utf-8 -*-
"""下载 Book-Crossing 官方 CSV（BX-CSV-Dump 镜像）"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent / 'raw'
MIRROR = 'https://raw.githubusercontent.com/bigsnarfdude/guide-to-data-mining/master/BX-Dump'

FILES = (
    'BX-Books.csv',
    'BX-Users.csv',
    'BX-Book-Ratings.csv',
)


def download_file(name: str, force: bool = False) -> Path:
    dest = RAW_DIR / name
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force and dest.stat().st_size > 1000:
        print(f'[skip] {name} ({dest.stat().st_size // 1024} KB)')
        return dest
    url = f'{MIRROR}/{name}'
    print(f'[download] {url}')
    req = urllib.request.Request(url, headers={'User-Agent': 'JBOOK/1.0'})
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f'[saved] {dest} ({len(data) // 1024} KB)')
    return dest


def main(force: bool = False):
    for name in FILES:
        download_file(name, force=force)
    print('Book-Crossing raw files ready in:', RAW_DIR)


if __name__ == '__main__':
    main(force='--force' in sys.argv)
