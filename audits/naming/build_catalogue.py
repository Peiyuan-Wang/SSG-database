"""Reproducible migration of the existing 67,475 classes; no new census."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import time

from sympy import ImmutableMatrix as M
from ssg_enumeration.naming import (_chart_name, _parent, _matrix, _clean,
    canonical_torus, _affine_sections, SSGName, parse_label, _settings)
from ssg_enumeration.naming import _semantic_signature
from ssg_enumeration.serialization import record_data
from ssg_enumeration.torus import AffineTorus
from ssg_enumeration.xiao import _chart_signature, xiao_correspondences
from ssg_enumeration.exact import is_integral

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'tmp/naming_rule/named_final'
OUT.mkdir(exist_ok=True)


@lru_cache(maxsize=32768)
def validate_spin(name):
    name.validate()
    return True


@lru_cache(maxsize=4096)
def validate_grading(number,q,bits):
    g,_ = _parent(number)
    assert is_integral(2*q)
    for p in range(g.order):
        assert is_integral(g.rotations[p].T*q-q)
        for r in range(g.order):
            assert (bits[p]+bits[r]-bits[g.table[p][r]]-int(2*q.dot(g.cocycle[p][r]))) % 2 == 0


@lru_cache(maxsize=32768)
def validate_display_grading(number,q,bits,signs):
    for atom,sign in zip(_settings()[str(number)]['atoms'],signs):
        exponent=bits[atom['point']]+int(2*q.dot(M(atom['shift'])))
        assert sign==(-1 if exponent%2 else 1)


@lru_cache(maxsize=32768)
def reconstructed(name):
    return _affine_sections(name)[0] if name.translation_kind == 'axial' else name._sections(())


def audit(chart,name):
    """Exact all-section equality after the documented common spin gauge.

    Check the proper representation and its grading independently. This avoids
    repeating the same matrix proof once for every Z2 character.
    """
    g,_ = _parent(name.space_group)
    grading = chart.get('grading')
    if grading:
        validate_grading(name.space_group,_matrix(grading['k']),tuple(grading['section_bits']))
        validate_display_grading(name.space_group,_matrix(grading['k']),tuple(grading['section_bits']),tuple(int(m.det()) for m in name.spins))
    proper = replace(name,dimension='P' if name.dimension=='P' else 'N',
                     grading_q=M.zeros(3,1),spins=tuple(int(m.det())*m for m in name.spins))
    validate_spin(proper)
    r = chart.get('representation')
    if not r: return
    actual = reconstructed(proper)
    if 'offset' in r:
        torus = canonical_torus(AffineTorus(_matrix(r['offset']),_matrix(r['basis'])))
        off,bas,eta = torus.offset,torus.basis,r['eta']
        q = off[:3,:].row_join(bas[:3,:])
        phases = off[3:,:].row_join(bas[3:,:])
        pivot = eta.index(-1) if -1 in eta else None
        gauge = phases[pivot,:]-g.translations[pivot].T*q if pivot is not None and name.translation_kind=='axial' else M.zeros(1,phases.cols)
        if name.translation_kind == 'axial':
            assert name.q == off[:3,:] and name.basis == bas[:3,:]
            for p,(ph,ep,cp) in enumerate(actual):
                delta = ph-(phases[p,:]-(1-eta[p])//2*gauge)
                assert delta[0].is_integer and not any(delta[:,1:]) and ep==eta[p] and cp==1,(name.space_group,p,delta)
        else:
            from ssg_enumeration.representations import embed_o2,rotation_2d
            for p,m in enumerate(actual):
                expected = embed_o2(rotation_2d(off[3+p])*M.diag(1,eta[p]))
                assert _clean(m-expected)==M.zeros(3)
    else:
        from ssg_enumeration.representations import embed_o2
        sections = tuple(_matrix(x) for x in r['sections'])
        if sections[0].rows == 2: sections=tuple(embed_o2(x) for x in sections)
        assert all(_clean(a-b)==M.zeros(3) for a,b in zip(actual,sections))


def build(number):
    target = OUT/f'{number:03d}.json.gz'
    settings_hash=hashlib.sha256(json.dumps(_settings()[str(number)],sort_keys=True).encode()
                                +(ROOT/'ssg_enumeration/naming.py').read_bytes()).hexdigest()
    if target.exists():
        old=json.load(gzip.open(target))
        if old.get('settings_hash')==settings_hash and 'semantic_ids' in old: return number,'cached'
    start=time.monotonic()
    data=json.load(gzip.open(ROOT/f'tmp/naming_rule/catalogues/{number:03d}.json.gz'))
    rows=xiao_correspondences(space_group=number)
    orbit_rows={row.orbit_index:row for row in rows}
    named,aliases,semantic={},{},{}
    for oi,orbit in enumerate(data['orbits']):
        row=orbit_rows[oi]
        candidates=[]
        for ci in orbit:
            chart=data['charts'][ci]
            name=_chart_name(number,chart)
            audit(chart,name)
            candidates.append((name.exact_key,ci,name))
            aliases[f'{number}:{_chart_signature(chart)}']=row.our_label
            key=f'{number}:{_semantic_signature(chart)}'
            if key in semantic: assert semantic[key]==row.our_label
            semantic[key]=row.our_label
        _,ci,best=min(candidates,key=lambda x:(x[0],x[1]))
        # Parse without the catalogue lookup: the actual printed information
        # must suffice to reconstruct the name.
        restored=parse_label(best.text,validate=False)
        assert restored.text==best.text
        assert restored.spins==best.spins and restored.q==best.q and restored.basis==best.basis
        assert restored.grading_q==best.grading_q and restored.translation_spins==best.translation_spins
        rebuilt=restored.to_record()
        rebuilt_name=_chart_name(number,record_data(rebuilt))
        assert rebuilt_name.text==best.text,('Name/record/name failed',number,row.our_label,best.text,rebuilt_name.text)
        key=f'{number}:{_semantic_signature(record_data(rebuilt))}'
        if key in semantic: assert semantic[key]==row.our_label
        semantic[key]=row.our_label
        named[row.our_label]={'id':row.our_label,'xiao':row.xiao_label,'text':best.text,
                              'latex':best.latex,'name':best.to_dict(),'selected_chart':ci}
    payload={'rows':list(named.values()),'chart_ids':aliases,'semantic_ids':semantic,'settings_hash':settings_hash,
             'seconds':time.monotonic()-start,'charts':len(data['charts'])}
    target.write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0))
    return number,{'classes':len(named),'charts':len(aliases),'seconds':round(payload['seconds'],2)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--start',type=int,default=1)
    parser.add_argument('--end',type=int,default=230)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks={pool.submit(build,n):n for n in range(args.start,args.end+1)}
        failures=[]
        for task in as_completed(tasks):
            try: print(task.result(),flush=True)
            except Exception as exc:
                import traceback
                print('FAILED',tasks[task],repr(exc),flush=True)
                traceback.print_exception(exc)
                failures.append(tasks[task])
        if failures: raise RuntimeError(('Failed parents',failures))
    if args.start!=1 or args.end!=230: return
    rows,aliases,semantic=[],{},{}
    for n in range(1,231):
        data=json.load(gzip.open(OUT/f'{n:03d}.json.gz'))
        rows.extend(data['rows']);aliases.update(data['chart_ids']);semantic.update(data['semantic_ids'])
    texts={}
    for row in rows:
        if row['text'] in texts: raise ValueError(('Name collision',row['id'],texts[row['text']],row['text']))
        texts[row['text']]=row['id']
    assert len(rows)==67475
    payload={'metadata':{'naming_version':'1.1','catalogue':'full_export_230_20261029',
        'class_count':len(rows),'chart_count':len(aliases),'parent_count':230,
        'unique_names':True,'exact_all_section_roundtrip':True,
        'symbolic_family_check':True,'all_chart_aliases_checked':True,
        'generator_relations_checked':True,'name_record_name_roundtrip':True,
        'liu_seitz_origin_transforms_checked':230},'rows':rows,'chart_ids':aliases,'semantic_ids':semantic}
    path=ROOT/'ssg_enumeration/data/ssg_names.json.gz'
    path.write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0))
    (ROOT/'audits/naming/validation.json').write_text(json.dumps(payload['metadata'],indent=2)+'\n')
    print('SAVED',path,flush=True)


if __name__=='__main__': main()
