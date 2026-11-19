"""Fresh full-catalogue census with per-stage timings and bounded worker lifetimes."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gc
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import platform
import time
import traceback

from ssg_enumeration import enumerate_ssg
from ssg_enumeration.census import implementation_sha256
from ssg_enumeration.database import load_standard_space_group
from ssg_enumeration.serialization import catalog_dict, matrix_data


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8', buffering=1024*1024) as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    temporary.replace(path)


def run_one(task):
    number, directory, expected, fingerprint = task
    output = Path(directory)
    start = time.perf_counter()
    status_path = output / ('sg%03d.status.json' % number)
    stages = []
    def progress(stage, count=None):
        stages.append(dict(stage=stage, seconds=time.perf_counter()-start, count=count))
        write_json(status_path, dict(number=number, status='running', updated_at=stamp(), stages=stages))
    try:
        progress('loading_parent')
        group, metadata = load_standard_space_group(number)
        result = enumerate_ssg(group, automorphisms='full', verify=True, progress=progress)
        calculated = time.perf_counter()
        counts = Counter(record.label for record in result)
        continuous = Counter(record.label for record in result if record.parameter_count > 0)
        count, chart_count, relation_count = len(result), len(result.charts), len(result.relations)
        assert count == expected['total']
        assert all(counts[label] == n for label, n in expected['labels'].items())
        assert all(continuous[label] == n for label, n in expected['continuous_labels'].items())
        assert result.verified and result.normalizer_certificate['complete']
        progress('building_full_catalogue', count)
        payload = catalog_dict(result)
        payload['parent'] = dict(metadata,
            rotations=[matrix_data(m) for m in group.rotations],
            sections=[matrix_data(m) for m in group.translations],
            point_multiplication_table=group.table,
            section_cocycle=[[matrix_data(m) for m in row] for row in group.cocycle])
        payload['class_representatives'] = [orbit[0] for orbit in result.orbits]
        payload['implementation_sha256'] = fingerprint
        progress('writing_full_catalogue', chart_count)
        path = output / ('sg%03d.catalogue.json' % number)
        write_json(path, payload)
        # Release the exact objects and their JSON representation before parsing the output.
        del payload, result, group
        gc.collect()
        exported = time.perf_counter()
        progress('reading_and_checking_full_catalogue', relation_count)
        with path.open(encoding='utf-8') as stream:
            decoded = json.load(stream)
        assert len(decoded['orbits']) == count
        assert len(decoded['charts']) == chart_count
        assert len(decoded['relations']) == relation_count
        assert sorted(i for orbit in decoded['orbits'] for i in orbit) == list(range(chart_count))
        assert decoded['class_representatives'] == [orbit[0] for orbit in decoded['orbits']]
        assert decoded['parent']['input_sha256'] == metadata['input_sha256'] == expected['input_sha256']
        assert decoded['summary']['verified'] and decoded['summary']['normalizer_certificate']['complete']
        read_counts = Counter(decoded['charts'][i]['label'] for i in decoded['class_representatives'])
        assert read_counts == counts
        read_continuous = Counter(decoded['charts'][i]['label'] for i in decoded['class_representatives']
            if decoded['charts'][i].get('representation', {}).get('parameter_count', 0) > 0)
        assert read_continuous == continuous
        assert all(0 <= rel['source'] < chart_count and 0 <= rel['target'] < chart_count
                   for rel in decoded['relations'])
        del decoded
        gc.collect()
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                digest.update(block)
        finish = time.perf_counter()
        row = dict(number=number, status='complete', classes=count, charts=chart_count, relations=relation_count,
            labels=dict(sorted(counts.items())), continuous_labels=dict(sorted(continuous.items())),
            continuous_family_count=sum(continuous.values()), discrete_count=count-sum(continuous.values()),
            enumerate_seconds=calculated-start, export_seconds=exported-calculated,
            read_check_seconds=finish-exported, total_seconds=finish-start,
            bytes=path.stat().st_size, file=path.name, file_sha256=digest.hexdigest(),
            verified=True, matches_previous_census=True, implementation_sha256=fingerprint)
        write_json(output / ('sg%03d.timing.json' % number), row)
        write_json(status_path, dict(number=number, status='complete', stages=stages, total_seconds=finish-start))
        return row
    except Exception:
        error=dict(number=number, status='failed', seconds=time.perf_counter()-start,
                   traceback=traceback.format_exc(), stages=stages)
        write_json(status_path,error)
        return error


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--numbers',nargs='+',type=int,default=list(range(1,231)))
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert args.workers > 0 and len(set(args.numbers)) == len(args.numbers)
    assert all(1 <= n <= 230 for n in args.numbers)
    args.output.mkdir(parents=True,exist_ok=True)
    if any(args.output.glob('sg*.json')) or (args.output/'run_metadata.json').exists():
        raise SystemExit('Use a fresh output folder: this timing run never resumes old results.')
    root=Path(__file__).resolve().parents[1]
    previous=json.loads((root/'results/sg230_full_out_plus/summary.json').read_text())
    expected={r['number']:r for r in previous['parents']}
    fingerprint=implementation_sha256()
    assert fingerprint == previous['implementation_sha256']
    started_at=stamp(); start=time.perf_counter(); rows=[]
    metadata=dict(started_at=started_at,workers=args.workers,worker_recycling='one parent per process',
        requested_parents=args.numbers,python=platform.python_version(),machine=platform.machine(),
        implementation_sha256=fingerprint,fresh_computation=True,
        timing_scope='parent loading, exact enumeration, full quotient, verification, complete JSON export, read checks and SHA256; wall time also includes worker startup/shutdown',
        export_format='same full JSON schema, streaming indentation and releasing intermediates before readback')
    write_json(args.output/'run_metadata.json',metadata)
    tasks=[(n,str(args.output),expected[n],fingerprint) for n in args.numbers]
    with mp.get_context('spawn').Pool(args.workers,maxtasksperchild=1) as pool:
        for row in pool.imap_unordered(run_one,tasks,chunksize=1):
            rows.append(row)
            completed=[r for r in rows if r['status']=='complete']
            write_json(args.output/'progress.json',dict(finished=len(rows),completed=len(completed),
                requested=len(tasks),wall_seconds=time.perf_counter()-start,
                classes=sum(r['classes'] for r in completed),bytes=sum(r['bytes'] for r in completed),
                failures=[r['number'] for r in rows if r['status']!='complete'],last_number=row['number']))
            print(json.dumps(dict(number=row['number'],status=row['status'],finished=len(rows),
                classes=row.get('classes'),total_seconds=row.get('total_seconds'),
                wall_seconds=time.perf_counter()-start)),flush=True)
    wall=time.perf_counter()-start
    completed=[r for r in rows if r['status']=='complete']
    labels=Counter(); continuous=Counter()
    for row in completed:
        labels.update(row['labels']);continuous.update(row['continuous_labels'])
    summary=dict(metadata,ended_at=stamp(),wall_seconds=wall,completed_parents=len(completed),
        status='complete' if len(completed)==len(tasks) else 'failed',
        total_classes=sum(r['classes'] for r in completed),labels=dict(sorted(labels.items())),
        dimensions={d:sum(v for k,v in labels.items() if k.startswith(d)) for d in 'LPN'},
        continuous_family_count=sum(continuous.values()),
        continuous_labels={label:continuous[label] for label in previous['labels']},
        discrete_count=sum(r['discrete_count'] for r in completed),total_bytes=sum(r['bytes'] for r in completed),
        task_seconds={key:sum(r[key] for r in completed) for key in
            ['enumerate_seconds','export_seconds','read_check_seconds','total_seconds']},
        rows=sorted(rows,key=lambda r:r['number']))
    if set(args.numbers)==set(range(1,231)) and len(completed)==230:
        assert summary['total_classes']==67475
        assert summary['labels']==previous['labels']
        assert summary['continuous_labels']==previous['continuous_labels']
    write_json(args.output/'timing_summary.json',summary)
    print('FINAL '+json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
    if summary['status']!='complete': raise SystemExit(1)

if __name__=='__main__':
    main()
