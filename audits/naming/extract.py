"""Extract only charts and orbits; never materialize multi-GB relation arrays."""
import gzip
import json
from pathlib import Path
import ijson

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'tmp/naming_rule/catalogues'
TARGET.mkdir(parents=True, exist_ok=True)
total = 0
for number in range(1, 231):
    target = TARGET / f'{number:03d}.json.gz'
    if target.exists():
        continue
    source = ROOT / f'recomputed_results/full_export_230_20261029/sg{number:03d}.catalogue.json'
    # The exporter writes charts and orbits before its large relation array.
    data = {}
    with source.open('rb') as handle:
        for key, value in ijson.kvitems(handle, ''):
            data[key] = value
            if key == 'orbits':
                break
    with gzip.open(target, 'wt') as handle:
        json.dump(data, handle, separators=(',', ':'))
    total += len(data['charts'])
    print(number, len(data['charts']), len(data['orbits']), flush=True)
print('extracted charts', total)
