"""Measure fresh exact enumeration and full JSON export; does not reuse census objects."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import platform
import time

from ssg_enumeration import enumerate_ssg
from ssg_enumeration.census import implementation_sha256
from ssg_enumeration.database import load_standard_space_group
from ssg_enumeration.serialization import catalog_dict, matrix_data


def run_one(number, output, expected):
    start = time.perf_counter()
    group, metadata = load_standard_space_group(number)
    result = enumerate_ssg(group, automorphisms='full', verify=True)
    calculated = time.perf_counter()
    counts = Counter(s.label for s in result)
    assert len(result) == expected['total']
    assert all(counts[k] == v for k, v in expected['labels'].items())
    payload = catalog_dict(result)
    payload['parent'] = dict(metadata, rotations=[matrix_data(m) for m in group.rotations],
                             sections=[matrix_data(m) for m in group.translations],
                             point_multiplication_table=group.table,
                             section_cocycle=[[matrix_data(m) for m in row] for row in group.cocycle])
    payload['class_representatives'] = [orbit[0] for orbit in result.orbits]
    payload['implementation_sha256'] = implementation_sha256()
    path = Path(output) / ('sg%03d.catalogue.json' % number)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
    exported = time.perf_counter()
    decoded = json.loads(path.read_text())
    assert len(decoded['orbits']) == len(result)
    assert len(decoded['charts']) == len(result.charts)
    assert len(decoded['relations']) == len(result.relations)
    assert sorted(i for orbit in decoded['orbits'] for i in orbit) == list(range(len(result.charts)))
    assert decoded['parent']['input_sha256'] == expected['input_sha256']
    assert decoded['summary']['verified']
    finish = time.perf_counter()
    row = dict(number=number, classes=len(result), charts=len(result.charts), relations=len(result.relations),
               enumerate_seconds=calculated-start, export_seconds=exported-calculated,
               read_check_seconds=finish-exported, total_seconds=finish-start,
               bytes=path.stat().st_size, historical_seconds=expected['seconds'])
    (Path(output)/('sg%03d.timing.json'%number)).write_text(json.dumps(row,indent=2)+'\n')
    return row


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--numbers',nargs='+',type=int,default=[47,123,229,225,14,76,146,168,195,1])
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--output',type=Path,default=Path('recomputed_results/full_export_benchmark'))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    old=json.loads((root/'results/sg230_full_out_plus/summary.json').read_text())
    expected={r['number']:r for r in old['parents']}
    assert implementation_sha256()==old['implementation_sha256']
    start=time.perf_counter(); rows=[]
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        jobs=[executor.submit(run_one,n,str(args.output),expected[n]) for n in args.numbers]
        for future in as_completed(jobs):
            row=future.result(); rows.append(row)
            print(json.dumps(row),flush=True)
    summary=dict(wall_seconds=time.perf_counter()-start,workers=args.workers,python=platform.python_version(),
                 machine=platform.machine(),implementation_sha256=implementation_sha256(),
                 rows=sorted(rows,key=lambda r:r['number']),historical_all_task_seconds=sum(r['seconds'] for r in old['parents']))
    (args.output/'timing_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('WALL_SECONDS',summary['wall_seconds'],flush=True)

if __name__=='__main__':
    main()
