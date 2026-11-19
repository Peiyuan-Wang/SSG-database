"""Public API audit of every formal name and every standard chart alias."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
from sympy import ImmutableMatrix as M
from ssg_enumeration import parse_label, SSGName, name_for_chart
from ssg_enumeration.naming import _semantic_signature, _chart_name
from ssg_enumeration.serialization import record_data
from ssg_enumeration.xiao import _chart_signature
from audits.naming.build_catalogue import validate_display_grading
from ssg_enumeration.naming import _matrix

ROOT=Path(__file__).resolve().parents[2]


def verify(number):
    named=json.load(gzip.open(ROOT/f'tmp/naming_rule/named_final/{number:03d}.json.gz'))
    rows=named['rows']; aliases=named['chart_ids']; semantic=named['semantic_ids']
    originals=json.load(gzip.open(ROOT/f'tmp/naming_rule/catalogues/{number:03d}.json.gz'))
    row_orbit={ci:row for orbit,row in zip(originals['orbits'],rows) for ci in orbit}
    # Use stored original IDs explicitly: output row order is orbit order.
    for ci,chart in enumerate(originals['charts']):
        assert aliases[f'{number}:{_chart_signature(chart)}']==row_orbit[ci]['id']
        grading=chart.get('grading')
        if grading:
            name=_chart_name(number,chart)
            validate_display_grading(number,_matrix(grading['k']),tuple(grading['section_bits']),tuple(int(m.det()) for m in name.spins))
    for row in rows:
        name=parse_label(row['text'])
        assert name.to_dict()==row['name']
        assert name.latex==row['latex']
        rebuilt=name.to_record()
        assert rebuilt.category==row['id'].split('/')[1]
        assert name_for_chart(number,rebuilt).text==name.text
        key=f'{number}:{_semantic_signature(record_data(rebuilt))}'
        assert semantic[key]==row['id']
    return number,len(rows),len(originals['charts'])


if __name__=='__main__':
    count,charts=0,0
    with ProcessPoolExecutor(max_workers=4) as pool:
        tasks={pool.submit(verify,n):n for n in range(1,231)}
        failures=[]
        for task in as_completed(tasks):
            try:
                n,c,h=task.result();count+=c;charts+=h
                print(n,c,h,flush=True)
            except Exception as exc:
                import traceback
                failures.append(tasks[task]);traceback.print_exception(exc)
        if failures: raise RuntimeError(failures)
    assert (count,charts)==(67475,206288)
    data=json.load(gzip.open(ROOT/'ssg_enumeration/data/ssg_names.json.gz'))
    assert len({r['text'] for r in data['rows']})==67475
    assert len({r['xiao'] for r in data['rows']})==67475
    assert Counter(r['name']['dimension'] for r in data['rows'])=={'L':1421,'P':9542,'N':56512}
    assert sum(bool(r['name']['basis'][0]) for r in data['rows'])==8520
    metadata=data['metadata']
    metadata.update(public_parser_validation_count=count,record_category_roundtrip_count=count,
                    chart_alias_checks=charts,continuous_family_count=8520,
                    source_sha256=hashlib.sha256((ROOT/'ssg_enumeration/naming.py').read_bytes()).hexdigest())
    (ROOT/'ssg_enumeration/data/ssg_names.json.gz').write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
    (ROOT/'audits/naming/validation.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('PASS',metadata,flush=True)
