from pathlib import Path
from dataharvest.config import Config
import sys

base = Path('configs')
files = sorted(base.glob('*.yaml'))
print('Checking', len(files), 'files')
issues = []
for p in files:
    try:
        Config(p)
        print('OK:', p.name)
    except Exception as e:
        issues.append((p.name, type(e).__name__, str(e)))
        print('ERROR:', p.name, '->', type(e).__name__, str(e))
if issues:
    sys.exit(1)
