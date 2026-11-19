"""Package the verified matching; never assign a Xiao serial by row order."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re

from ssg_enumeration.labels import LABELS
from ssg_enumeration.xiao import _chart_signature

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'software/paclet/official_sources/iso_ir/XiaoO3RepresentationSource.json'
CATALOGUES = ROOT / 'recomputed_results/full_export_230_20261029'


def main():
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes)
    rows, keys, parents = [], {}, []
    second_count = 0
    for number in range(1, 231):
        audit = json.loads((ROOT / f'audits/xiao_mapping/results/sg{number:03d}.json').read_text())
        assert audit['matched'] == audit['expected'] == audit['unique_orbits']
        assert not audit['failures'] and not audit['collisions']
        second_count += audit['second_parameter_checked']
        raw = (CATALOGUES / f'sg{number:03d}.catalogue.json').read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        timing = json.loads((CATALOGUES / f'sg{number:03d}.timing.json').read_text())
        assert digest == timing['file_sha256']
        data = json.loads(raw)
        del raw
        matched = {r['orbit']: r['xiao_label'] for r in audit['rows']}
        assert set(matched) == set(range(len(data['orbits'])))
        counts = Counter()
        for orbit, chart_index in enumerate(data['class_representatives']):
            assert chart_index in data['orbits'][orbit]
            chart = data['charts'][chart_index]
            category = chart['label']
            counts[category] += 1
            label = f'SG{number:03d}/{category}/{counts[category]:04d}'
            published = matched[orbit]
            src = source['XiaoRecords'][published]
            assert src['ParentSpaceGroup'] == number and published[0] == category[0]
            alternative = src['Alternatives'][src['CanonicalAlternative']]
            parameters = chart.get('representation', {}).get('parameter_count', 0)
            rows.append([label, number, category, counts[category], published,
                         alternative['Constituents'], parameters, orbit, chart_index])
            key = f'{number}:{_chart_signature(chart)}'
            assert key not in keys
            keys[key] = published
        parents.append({'space_group': number, 'classes': len(matched),
                        'catalogue_sha256': digest, 'origin_shift': audit['origin_shift']})
        del data
        if number % 25 == 0:
            print('Exported', number, len(rows), flush=True)
    assert len(rows) == len(keys) == 67475
    assert len({r[0] for r in rows}) == len({r[4] for r in rows}) == 67475
    assert {r[4] for r in rows} == set(source['XiaoRecords'])
    # Independent transcription check against all full IDs in the paper PDF.
    paper = (ROOT / 'tmp/xiao_full_layout.txt').read_text()
    paper_ids = set(re.findall(r'\b[LPN]\d{1,3}\.\d{1,2}\.\d+\b', paper))
    assert paper_ids == {r[4] for r in rows}
    assert second_count == sum(r[6] > 0 for r in rows) == 8520
    metadata = {
        'schema': 'ssgclassify-xiao-correspondence-1',
        'catalogue_version': 'full_export_230_20261029',
        'class_count': len(rows), 'parent_count': 230,
        'magnetic_order_counts': dict(Counter(r[4][0] for r in rows)),
        'continuous_count': second_count, 'discrete_count': 67475-second_count,
        'first_parameters': ['1/101', '3/101', '7/101'],
        'second_parameters': ['2/101', '5/101', '11/101'],
        'second_parameter_checked': second_count,
        'paper_id_set_verified': True,
        'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'source_archive_sha256': hashlib.sha256((ROOT/'reference/O3_Rep_Class.zip').read_bytes()).hexdigest(),
        'source_metadata': source['Sources'],
        'paper_url': 'https://doi.org/10.1103/PhysRevX.14.031037',
        'supplement_url': 'https://journals.aps.org/prx/supplemental/10.1103/PhysRevX.14.031037',
        'baseline_implementation_sha256': timing['implementation_sha256'],
        'matching_method': 'Coordinate and origin alignment; spin normalization; exact integer phase membership in computed charts; stored automorphism orbits.',
        'numeric_spin_tolerance': 2e-8, 'phase_grid_denominator': 144*101,
        'phase_grid_scaled_tolerance': 1e-6,
        'verification_scope': 'All source canonical representatives matched bijectively; continuous classes checked at two parameter values. Numeric orthogonal bases and rational phase recovery are not a symbolic all-parameter certificate.',
        'local_id_definition': 'SG{parent:03d}/{category}/{one-based index within category:04d}, indexed in saved class_representatives order.',
        'parents': parents,
    }
    payload = {'rows': rows, 'representative_keys': keys, 'metadata': metadata}
    target = ROOT / 'ssg_enumeration/data/xiao_correspondence.json.gz'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    summary = []
    for category in LABELS:
        subset = [r for r in rows if r[2] == category]
        types = Counter(int(r[4].split('.')[1]) for r in subset)
        summary.append([category, ', '.join(f'{t}: {n}' for t,n in sorted(types.items())),
                        len(subset), sum(r[6] > 0 for r in subset)])
    table = {'headers': ['我们的完整编号','母空间群','我们的类型','类型内序号','Xiao 完整编号',
                         'Xiao 表示类型','ISO-IR 表示组成','连续参数个数'],
             'rows': [[*r[:5],int(r[4].split('.')[1]),' + '.join(r[5]),r[6]] for r in rows],
             'summary': summary, 'metadata': metadata}
    (ROOT/'audits/xiao_mapping/table_data.json').write_text(json.dumps(table,ensure_ascii=False))
    (ROOT/'audits/xiao_mapping/verification.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print('PACKAGED', len(rows), 'continuous', second_count, 'bytes', target.stat().st_size, flush=True)


if __name__ == '__main__':
    main()
