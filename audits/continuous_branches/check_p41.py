"""Reproduce the P4_1 continuation audit without changing the census algorithm."""
import json
from fractions import Fraction
from pathlib import Path
from sympy import ImmutableMatrix as M, Rational as Q
import ssg_enumeration as s
from ssg_enumeration.census import implementation_sha256
from ssg_enumeration.type1 import Type1Record, enumerate_noncoplanar_type1


def component_orbits(cuts):
    # Intervals j/N<u<(j+1)/N.  u -> -u maps j to N-1-j.
    return sorted({tuple(sorted((j, cuts-1-j))) for j in range(cuts)})


def audit():
    group=s.example_space_group('P41')
    result=s.enumerate_ssg(group,automorphisms='full',verify=True)
    def relevant(chart):
        rep=chart.representation
        return (chart.dimension=='Noncoplanar' and isinstance(rep,Type1Record)
                and rep.dimension==1 and rep.eta==(1,1,1,1)
                and rep.torus.offset==M.zeros(7,1)
                and rep.torus.basis==M([0,0,4,0,1,2,3])
                and chart.grading.key==((0,0,0),(0,0,0,0)))
    matches=[(i,c) for i,c in enumerate(result.charts) if relevant(c)]
    assert len(matches)==1
    index,chart=matches[0]
    orbit=next(orbit for orbit in result.orbits if index in orbit)
    assert orbit==(index,)
    relations=[rel for rel in result.relations if rel.source==index]
    assert len(relations)==1+2*len(result.automorphisms)
    signs=[]
    for relation in relations:
        assert relation.target==index and relation.parameters is not None
        a,b,c=relation.parameters.source,relation.parameters.target,relation.parameters.rhs
        assert c==M.zeros(c.rows,1)
        if a == -b: signs.append(1)
        elif a == b: signs.append(-1)
        else: raise AssertionError('Nontrivial phase shift or parameter action: '+relation.name)
        # The coefficient of u in the screw phase is 1; there is no hidden multi-valued solution.
        assert abs(a[4,0])==abs(b[4,0])==1
    assert set(signs)=={-1,1}
    samples=[]
    for u in (Q(1,16),Q(5,16)):
        k,theta=chart.representation.point([u])
        assert k==M([0,0,Q(1,4)])
        samples.append({'u':str(u),'k':[str(v) for v in k],
                        'theta':[str(v) for v in theta]})
    decision=result.equivalent_points(index,[Q(1,16)],index,[Q(5,16)])
    assert decision.status=='distinct'
    # Direct implementation returns one continuous chart, without splitting its punctures.
    assert sum(relevant(c) for c in result.charts)==1
    assert component_orbits(4)==[(0,3),(1,2)]
    assert component_orbits(8)==[(0,7),(1,6),(2,5),(3,4)]
    p21=enumerate_noncoplanar_type1(s.example_space_group('P21'))
    f=next(r for r in p21 if r.eta==(1,1) and r.dimension and
           not r.torus.offset[0] and not r.torus.offset[2])
    assert abs(f.torus.basis[1,0])==2 and abs(f.torus.basis[4,0])==1
    return {'group':'P41','number':76,'grading':'trivial','eta':[1,1,1,1],
       'chart_index':index,'chart_orbit':list(orbit),'parameterization':'k=(0,0,4u), theta=(0,u,2u,3u), u in R/Z',
       'spatial_generator_count':len(result.automorphisms),
       'normalizer_certificate':result.normalizer_certificate,
       'relation_signs':signs,'samples':samples,
       'point_equivalence':{'status':decision.status,'reason':decision.reason},
       'nonzero_k':{'excluded_u':[str(Fraction(j,4)) for j in range(4)],
                    'components':4,'component_orbits_under_sign':component_orbits(4)},
       'general_chart':{'excluded_u':[str(Fraction(j,8)) for j in range(8)],
                        'components':8,'component_orbits_under_sign':component_orbits(8),
                        'current_family_count':1},
       'p21_unpunctured_cover_degree':2,'implementation_sha256':implementation_sha256()}

if __name__=='__main__':
    data=audit()
    out=Path(__file__).with_name('p41_evidence.json')
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(data,ensure_ascii=False,indent=2))
