"""Independent audit, not a replacement for the classification algorithms.

Run from the workspace: PYTHONPATH=. python3 ssg_enumeration/audits/deduplication/audit_spin_and_domains.py
"""
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from sympy import ImmutableMatrix as M, Rational as Q, simplify
import ssg_enumeration as s

output = Path(__file__).resolve().parent
spin_rows=[]
for name in ('P1','P2','P21','P3'):
    group=s.example_space_group(name)
    for dim in ('Noncoplanar','Coplanar'):
        if dim=='Noncoplanar':
            records=s.enumerate_noncoplanar_type0(group)+s.enumerate_noncoplanar_type1(group)+s.enumerate_noncoplanar_type2(group)
        else:
            records=s.enumerate_coplanar_type0(group)+s.enumerate_coplanar_type1(group)+s.enumerate_coplanar_type2(group)
        records=tuple(r for r in records if not r.parameter_count)
        buckets=defaultdict(list)
        for i,r in enumerate(records):
            matrices=tuple(r.evaluate(M.eye(3)[:,j],0,embedded=False).applyfunc(simplify) for j in range(3))
            matrices+=tuple(r.evaluate([0,0,0],p,embedded=False).applyfunc(simplify) for p in range(group.order))
            character=tuple((simplify(m.trace()),simplify(m.det())) for m in matrices)
            buckets[character].append((i,matrices))
        duplicates=[]
        comparisons=0
        for bucket in buckets.values():
            for (i,a),(j,b) in combinations(bucket,2):
                comparisons+=1
                if s.spin_equivalent_matrices(a,b):
                    duplicates.append([i,j])
        row={'group':name,'dimension':dim,'discrete_records':len(records),
             'independent_intertwiner_comparisons':comparisons,'residual_duplicate_pairs':duplicates}
        spin_rows.append(row)
        print(row,flush=True)
        (output/'spin_uniqueness.json').write_text(json.dumps(spin_rows,ensure_ascii=False,indent=2)+'\n')

# Exact P41 axial branch: q_z=4u, theta_s=u, u in R/Z.
g=s.example_space_group('P41')
axial=[]
for r in s.enumerate_noncoplanar_type1(g):
    if r.dimension and all(e==1 for e in r.eta):
        _,k,theta=r.symbolic()
        if k[0]==0 and k[1]==0:
            axial.append(r)
assert len(axial)==1
r=axial[0]
assert r.torus.offset==M.zeros(7,1)
assert r.torus.basis==M([0,0,4,0,1,2,3])

def interval_orbits(number):
    # Removing j/number from a circle leaves `number` open intervals.
    # Exact spin inversion u -> -u takes interval j to number-1-j.
    intervals=[(Q(j,number),Q(j+1,number)) for j in range(number)]
    orbits=sorted({tuple(sorted((j,number-1-j))) for j in range(number)})
    return {'cuts':[str(Q(j,number)) for j in range(number)],
            'open_intervals':[[str(a),str(b)] for a,b in intervals],
            'connected_components_before_spin':number,
            'component_orbits_under_spin_inversion':[list(o) for o in orbits],
            'connected_components_after_spin':len(orbits)}

domain={'group':'P41','eta':[1,1,1,1],'k':'(0,0,4u) mod Z^3',
        'theta':'(0,u,2u,3u) mod Z^4','parameter_domain':'u in R/Z',
        'current_axial_general_chart_count':1,
        'excluding_only_zero_k':interval_orbits(4),
        'excluding_all_TRIM_as_in_current_general_stratum':interval_orbits(8),
        'interpretation':'Current chart count is not the count of connected components of the admissible parameter quotient.'}
(output/'continuous_domains.json').write_text(json.dumps(domain,ensure_ascii=False,indent=2)+'\n')
assert all(not row['residual_duplicate_pairs'] for row in spin_rows)
print('Independent discrete spin audit: no duplicate pairs in these examples.',flush=True)
print('P41: one current chart contains four general-domain components modulo spin inversion.',flush=True)
