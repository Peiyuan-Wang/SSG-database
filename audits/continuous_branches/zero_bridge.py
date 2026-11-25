"""Certificates for continuation in a fixed completed joint (k, theta) component.

These certify the algebraic continuation, not pointwise equivalence and not
permission to switch the generic little group at an exceptional point.
"""
from collections import Counter
import json
import multiprocessing as mp
from pathlib import Path
import time
from sympy import ImmutableMatrix as M, ZZ
from sympy.matrices.normalforms import smith_normal_form
from ssg_enumeration.census import implementation_sha256
from ssg_enumeration.database import load_standard_space_group
from ssg_enumeration.exact import is_integral
from ssg_enumeration.type1 import enumerate_noncoplanar_type1, joint_type1_system
from ssg_enumeration.representations import rotation_2d, embed_o2


def component_certificate(group, record, equations=None):
    a=joint_type1_system(group,record.eta) if equations is None else equations
    offset,basis=record.torus.offset,record.torus.basis
    d=record.parameter_count
    assert d>0 and record.stratum=='general'
    assert is_integral(a*offset)
    assert a*basis==M.zeros(a.rows,d)
    assert basis.rank()==basis[:3,:].rank()==d
    full_smith=smith_normal_form(basis,domain=ZZ)
    assert all(abs(full_smith[i,i])==1 for i in range(d))
    wave_smith=smith_normal_form(basis[:3,:],domain=ZZ)
    degree=1
    for i in range(d): degree*=abs(int(wave_smith[i,i]))
    return dict(dimension=d,eta=list(record.eta),projection_cover_degree=degree,
                offset_satisfies_congruences=True,directions_satisfy_exact_equations=True,
                full_parameter_embedding_primitive=True,projection_has_finite_fibers=True)


def path_certificate(group,record,u0,u1):
    component_certificate(group,record)
    u0,u1=M(u0),M(u1)
    assert u0.shape==u1.shape==(record.parameter_count,1)
    record.point(tuple(u0));record.point(tuple(u1))  # generic endpoints only
    start=record.torus.offset+record.torus.basis*u0
    direction=record.torus.basis*(u1-u0)
    a=joint_type1_system(group,record.eta)
    assert is_integral(a*start) and a*direction==M.zeros(a.rows,1)
    return start,direction


def completed_evaluate(record,parameters,translation,point):
    # Evaluate the same formula at special points of the completed family;
    # Type1Record.point deliberately rejects them as generic catalogue members.
    x=record.torus.evaluate(parameters)
    matrix=rotation_2d(x[:3,:].dot(M(translation))+x[3+point])*M.diag(1,record.eta[point])
    return embed_o2(matrix) if record.spin_dimension==3 else matrix


def worker(number):
    group,_=load_standard_space_group(number)
    records=[r for r in enumerate_noncoplanar_type1(group) if r.parameter_count]
    matrices={}
    certificates=[]
    for record in records:
        if record.eta not in matrices:matrices[record.eta]=joint_type1_system(group,record.eta)
        certificates.append(component_certificate(group,record,matrices[record.eta]))
    return dict(number=number,continuous_components=len(records),certificates=certificates)


def main():
    start=time.perf_counter();rows=[]
    with mp.get_context('spawn').Pool(4,maxtasksperchild=1) as pool:
        for row in pool.imap_unordered(worker,range(1,231)):
            rows.append(row)
            if len(rows)%25==0:print('Checked',len(rows),'parents',flush=True)
    certificates=[c for row in rows for c in row['certificates']]
    summary=dict(scope='all noncoplanar Type1 positive-dimensional charts before spatial quotient; coplanar uses the identical joint tori',
       completed_parents=len(rows),components=len(certificates),
       dimensions=dict(sorted(Counter(c['dimension'] for c in certificates).items())),
       cover_degrees=dict(sorted(Counter(c['projection_cover_degree'] for c in certificates).items())),
       seconds=time.perf_counter()-start,implementation_sha256=implementation_sha256(),
       rows=sorted(rows,key=lambda row:row['number']))
    out=Path(__file__).with_name('zero_bridge_230.json')
    out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
