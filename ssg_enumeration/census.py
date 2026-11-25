"""Reproducible 230-parent census computed by enumerate_ssg, with checkpoints.

The census uses the complete proper spatial quotient for EVERY parent. A
punctured continuous parameter domain counts once, irrespective of connectivity.
Only parent crystallographic operations are imported; all SSGs are computed here.
"""
import argparse
import csv
import hashlib
import json
import multiprocessing
import platform
import time
import traceback
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from . import __version__
from .database import load_standard_space_group
from .enumerate import enumerate_ssg
from .labels import LABELS


def implementation_sha256():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def _worker(task):
    number,directory,code_hash = task
    directory = Path(directory)
    start = time.monotonic()
    modules = []
    status_path = directory/f'sg{number:03d}.status.json'
    try:
        group,meta = load_standard_space_group(number)
        def progress(module,count):
            modules.append({'module':module,'count':count,'seconds':round(time.monotonic()-start,3)})
            _write_json(status_path,{'number':number,'status':'running','modules':modules})
        _write_json(status_path,{'number':number,'status':'loading_complete','modules':modules})
        result = enumerate_ssg(group,automorphisms='full',verify=True,progress=progress)
        all_counts = Counter(record.label for record in result)
        continuous = Counter(record.label for record in result if record.parameter_count > 0)
        discrete = all_counts-continuous
        dimensions = Counter(record.label[0] for record in result)
        row = {**meta,'status':'complete','spatial_scope':result.spatial_scope,'verified':result.verified,
               'normalizer_certificate':result.normalizer_certificate,
               'spin_chart_count':len(result.charts),
               'continuous_family_convention':'one punctured parameter domain, regardless of connected components',
               'package_version':__version__,'implementation_sha256':code_hash,
               'seconds':round(time.monotonic()-start,3),'modules':modules,
               'L':dimensions['L'],'P':dimensions['P'],'N':dimensions['N'],'total':len(result),
               'discrete_count':sum(discrete.values()),'continuous_family_count':sum(continuous.values()),
               'labels':{label:all_counts[label] for label in LABELS},
               'discrete_labels':{label:discrete[label] for label in LABELS},
               'continuous_labels':{label:continuous[label] for label in LABELS}}
        assert row['L']+row['P']+row['N'] == row['total'] == sum(row['labels'].values())
        assert row['total'] == row['discrete_count']+row['continuous_family_count']
        _write_json(directory/f'sg{number:03d}.json',row)
        _write_json(status_path,{'number':number,'status':'complete','seconds':row['seconds'],'modules':modules})
        return row
    except Exception:
        error = {'number':number,'status':'failed','traceback':traceback.format_exc(),
                 'seconds':round(time.monotonic()-start,3),'modules':modules,'implementation_sha256':code_hash}
        _write_json(status_path,error)
        return error


def aggregate_census(rows, requested_numbers, code_hash):
    rows = sorted((r for r in rows if r['status'] == 'complete'),key=lambda r:r['number'])
    labels = {label:sum(r['labels'][label] for r in rows) for label in LABELS}
    continuous = {label:sum(r['continuous_labels'][label] for r in rows) for label in LABELS}
    discrete = {label:labels[label]-continuous[label] for label in LABELS}
    totals = {key:sum(r[key] for r in rows) for key in ('L','P','N','total','discrete_count','continuous_family_count')}
    complete = {r['number'] for r in rows} == set(requested_numbers)
    scopes = {r.get('spatial_scope','spin_only') for r in rows}
    if len(scopes)>1: raise ValueError('Cannot mix different spatial quotients in one census.')
    scope = next(iter(scopes),'full_out_plus')
    full = bool(rows) and scope == 'full_out_plus' and all(r.get('normalizer_certificate',{}).get('complete') for r in rows)
    return {'status':'complete' if complete else 'partial','counting_unit':'discrete representations plus continuous parameter-family charts',
            'spatial_scope':scope,'full_out_plus_applied':full,
            'continuous_family_convention':'one punctured parameter domain, regardless of connected components',
            'parent_space_group_numbers':list(requested_numbers),'completed_parents':len(rows),
            'package_version':__version__,'implementation_sha256':code_hash,
            'generated_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'python_version':platform.python_version(),'totals':totals,'labels':labels,
            'discrete_labels':discrete,'continuous_labels':continuous,
            'coverage':{label:sum(r['labels'][label] > 0 for r in rows) for label in LABELS},'parents':rows}


def write_census_tables(summary, output):
    output = Path(output)
    _write_json(output/'summary.json',summary)
    rows = summary['parents']
    prefix = ['number','international_short','hall_number','point_group','point_order','L','P','N','total','discrete_count','continuous_family_count']
    with (output/'by_space_group.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=prefix+list(LABELS))
        writer.writeheader()
        writer.writerows({**{key:r[key] for key in prefix},**r['labels']} for r in rows)
    with (output/'by_type.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['type','total','discrete','continuous_families','parent_groups_with_type'])
        writer.writerows([label,summary['labels'][label],summary['discrete_labels'][label],
                         summary['continuous_labels'][label],summary['coverage'][label]] for label in LABELS)


def run_census(output, numbers=range(1,231), workers=4, resume=True):
    """Compute each parent using this package, verify every module, then aggregate."""
    numbers = tuple(sorted(set(numbers)))
    if not numbers or any(not isinstance(n,int) or not 1<=n<=230 for n in numbers):
        raise ValueError('Expected international numbers in 1..230.')
    if workers < 1:
        raise ValueError('workers must be positive.')
    output = Path(output).resolve()
    checkpoint = output/'groups'
    checkpoint.mkdir(parents=True,exist_ok=True)
    code_hash = implementation_sha256()
    rows,pending = [],[]
    for n in numbers:
        path = checkpoint/f'sg{n:03d}.json'
        if resume and path.exists():
            row = json.loads(path.read_text())
            if (row.get('implementation_sha256') == code_hash and row.get('verified')
                    and row.get('spatial_scope') == 'full_out_plus'
                    and row.get('normalizer_certificate',{}).get('complete')):
                rows.append(row)
                continue
        pending.append((n,str(checkpoint),code_hash))
    failures = []
    write_census_tables(aggregate_census(rows,numbers,code_hash),output)
    with multiprocessing.get_context('spawn').Pool(processes=workers,maxtasksperchild=1) as pool:
        for row in pool.imap_unordered(_worker,pending,chunksize=1):
            if row['status'] != 'complete':
                failures.append(row)
                print(f"FAILED SG {row['number']}: {row['traceback']}",flush=True)
            else:
                rows.append(row)
                print(f"{len(rows)}/{len(numbers)} SG {row['number']:03d} {row['international_short']} "
                      f"L={row['L']} P={row['P']} N={row['N']} total={row['total']} ({row['seconds']}s)",flush=True)
            write_census_tables(aggregate_census(rows,numbers,code_hash),output)
    if failures:
        _write_json(output/'failures.json',failures)
        raise RuntimeError(f'{len(failures)} parent groups failed; summary is explicitly partial.')
    return aggregate_census(rows,numbers,code_hash)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--first',type=int,default=1)
    parser.add_argument('--last',type=int,default=230)
    parser.add_argument('--no-resume',action='store_true')
    args = parser.parse_args()
    result = run_census(args.output,range(args.first,args.last+1),args.workers,not args.no_resume)
    print(json.dumps({'status':result['status'],'totals':result['totals'],'labels':result['labels']},indent=2),flush=True)


if __name__ == '__main__': main()
