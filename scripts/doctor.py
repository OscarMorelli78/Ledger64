"""Read-only environment diagnostic; no network or installation."""
import importlib.metadata as md
import shutil
import sqlite3
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
errors = []
print('Python:', sys.version.split()[0], '| SQLite:', sqlite3.sqlite_version)
if sys.version_info[:2] != (3, 13):
    errors.append('Python 3.13 is the tested runtime')
for file in ('requirements.txt','requirements-dev.txt'):
    for line in (root/file).read_text().splitlines():
        if '==' not in line or line.strip().startswith('#'):
            continue
        name, expected = line.strip().split('==', 1)
        try:
            actual = md.version(name)
        except md.PackageNotFoundError:
            actual = 'missing'
        print(f'{name}: {actual} (expected {expected})')
        if actual != expected:
            errors.append(name)
for command in ('node','tesseract','docker'):
    available = shutil.which(command)
    print(f'{command}: {available or "not installed"}')
    if not available and command != 'docker':
        errors.append(command)
if not shutil.which('docker'):
    print('Docker acceptance unavailable; use an authorized CI runner.')
if errors:
    print('Check required:', ', '.join(errors))
    raise SystemExit(1)
print('Local prerequisites OK; no production certification implied.')
