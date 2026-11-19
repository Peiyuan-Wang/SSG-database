"""Exact complete proper affine-normalizer examples P1 and P-1.

P1: A in SL(3,Z); origin translations act trivially on the group.
P-1: A in SL(3,Z), and 2*origin in Z^3. Thus the elementary
transvections and three half-origin translations generate the full action.
These are input automorphisms; SSG orbit counts are computed by our package.
"""
from collections import Counter
import json
from pathlib import Path
from sympy import ImmutableMatrix as M,Rational as Q
import ssg_enumeration as s

out=[]
for name in ('P1','P-1'):
    g=s.example_space_group(name)
    raw=s.enumerate_ssg(g)
    actions=[]
    for i in range(3):
        for j in range(3):
            if i!=j:
                a=M.eye(3).as_mutable()
                a[i,j]=1
                actions.append(s.affine_automorphism(g,a,name=f'E{i}{j}'))
    if name=='P-1':
        for i in range(3):
            v=M.zeros(3,1).as_mutable()
            v[i]=Q(1,2)
            actions.append(s.affine_automorphism(g,M.eye(3),v,name=f'half_origin_{i}'))
    quotient=s.deduplicate_automorphisms(raw.charts,actions)
    out.append({'group':name,'before':len(raw),'after_chart_orbits':len(quotient),
        'before_dimensions':dict(Counter(r.label[0] for r in raw)),
        'after_dimensions':dict(Counter(r.label[0] for r in quotient)),
        'before_labels':raw.summary()['labels'],'after_labels':quotient.summary()['labels'],
        'generators':[a.name for a in actions]})
(Path(__file__).parent/'spatial_examples.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert [(r['before'],r['after_chart_orbits']) for r in out]==[(173,17),(985,35)]
print(json.dumps(out,ensure_ascii=False,indent=2))
