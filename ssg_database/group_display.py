"""Exact spin and spatial operations in the database's fixed coordinate setting."""
from sympy import Matrix, simplify
from ssg_enumeration.naming import SSGName, _parent


def point_operation_rows(detail,parameters=None,approximate=False):
    """Representatives for G/T, not the generally larger spin quotient G/kerρ.

    Rotations and translations are in conventional coordinates. Spin matrices
    are in the name's fixed spin frame, with symbolic parameters if necessary.
    """
    name=SSGName.from_dict(detail['name_data'],validate=False)
    group,basis=_parent(name.space_group)
    values=name.parameters if parameters is None else tuple(parameters)
    if len(values)!=name.parameter_count:raise ValueError('Incorrect number of parameters')
    if parameters is None and name.translation_kind=='axial':
        # Reconstruct the same sections from their affine phases.  Expanding
        # repeated trigonometric matrix products produces enormous expressions
        # for nonsymmorphic groups even though each section has one phase.
        from ssg_enumeration.naming import _affine_sections
        from sympy import cos,sin,pi
        phases,_=_affine_sections(name)
        coefficients=(1,)+tuple(values)
        spins=[]
        for phase,eta,chi in phases:
            angle=2*pi*sum(a*b for a,b in zip(phase,coefficients))
            c,s=cos(angle),sin(angle)
            spins.append(chi*Matrix([[c,-eta*s,0],[s,eta*c,0],[0,0,eta]]))
        spins=tuple(spins)
    elif approximate:
        substitutions=dict(zip(name.parameters,values))
        spins=tuple(m.subs(substitutions).evalf(10,chop=True) for m in name._sections(name.parameters))
    else:spins=name._sections(values)
    return [{'index':p+1,'point':p,'spin':spins[p],
             'rotation':(basis*group.rotations[p]*basis.inv()).applyfunc(simplify),
             'translation':(basis*group.translations[p]).applyfunc(simplify)}
            for p in range(group.order)]


def finite_quotient_rows(detail,parameters=None):
    """Represent G/kerρ by exact spin images, including translational cosets."""
    if detail['crystal']['mode'] != 'finite' and parameters is None:
        raise ValueError('Specify parameters for a continuous family; its generic image may be infinite.')
    if parameters is not None and detail['crystal']['mode'] != 'finite':
        return _rational_axial_quotient_rows(detail,parameters)
    from sympy import eye, zeros
    name=SSGName.from_dict(detail['name_data'],validate=False)
    parameters=()
    group,basis=_parent(name.space_group)
    sections=name._sections(parameters)
    gens=[(0,Matrix([int(i==j) for i in range(3)]),name._translation(Matrix([int(i==j) for i in range(3)]),parameters)) for j in range(3)]
    gens.extend((p,zeros(3,1),sections[p]) for p in range(group.order))
    identity=eye(3);items=[(0,zeros(3,1),identity)];seen={tuple(identity)}
    for p,t,spin in items:
        for q,u,spin2 in gens:
            newspin=(spin*spin2).applyfunc(simplify);key=tuple(newspin)
            if key in seen:continue
            seen.add(key)
            if len(seen)>4096:
                raise ValueError('The group image exceeds the display limit of 4096; choose smaller denominators.')
            if detail['crystal']['mode']=='finite' and len(seen)>detail['crystal']['k_order']:
                raise ValueError('The calculated image order disagrees with the catalogue')
            v=t+group.rotations[p]*u+group.cocycle[p][q]
            items.append((group.table[p][q],v,newspin))
    if detail['crystal']['mode']=='finite' and len(items)!=detail['crystal']['k_order']:
        raise ValueError('The calculated image order disagrees with the catalogue')
    rows=[]
    for i,(p,t,spin) in enumerate(items,1):
        actual=name.evaluate(tuple(t),p,parameters)
        if (actual-spin).applyfunc(simplify)!=zeros(3):
            raise ValueError('Spin and spatial operation representatives are inconsistent')
        rows.append({'index':i,'point':p,'spin':spin,
                     'rotation':(basis*group.rotations[p]*basis.inv()).applyfunc(simplify),
                     'translation':(basis*(t+group.translations[p])).applyfunc(simplify)})
    return rows


def _rational_axial_quotient_rows(detail,parameters):
    """Close rational axial phases without comparing trigonometric matrices."""
    from sympy import Rational, eye, zeros, lcm
    from ssg_enumeration.naming import _affine_sections
    from ssg_enumeration.representations import rotation_2d,embed_o2
    name=SSGName.from_dict(detail['name_data'],validate=False)
    parameters=tuple(Rational(v) for v in parameters)
    if len(parameters)!=name.parameter_count:raise ValueError('Incorrect number of parameters')
    q=name.q+name.basis*Matrix(parameters)
    if name.general and all((2*x).is_integer for x in q):
        raise ValueError('These parameters correspond to a separately classified special point')
    group,basis=_parent(name.space_group)
    coefficients=(Rational(1),)+parameters
    phases,_=_affine_sections(name)
    section_values=[(sum(a*b for a,b in zip(phase,coefficients))%1,eta,int(chi==-1))
                    for phase,eta,chi in phases]
    trans_values=[(q[j]%1,1,int(2*name.grading_q[j])%2) for j in range(3)]
    return _phase_quotient_rows(group,basis,trans_values,section_values)


def _phase_quotient_rows(group,basis,trans_values,section_values):
    from sympy import Rational, eye, zeros, lcm
    from ssg_enumeration.representations import rotation_2d,embed_o2
    denominator=1
    for phase,_,_ in section_values+trans_values:denominator=lcm(denominator,int(phase.q))
    if denominator>4096:raise ValueError('The common phase denominator exceeds 4096')
    gens=[(0,eye(3)[:,j],trans_values[j]) for j in range(3)]
    gens.extend((p,zeros(3,1),section_values[p]) for p in range(group.order))
    identity=(Rational(0),1,0);items=[(0,zeros(3,1),identity)];seen={identity}
    for p,t,(phase,eta,bit) in items:
        for r,v,(a,e,b) in gens:
            key=((phase+eta*a)%1,eta*e,(bit+b)%2)
            if key in seen:continue
            seen.add(key)
            if len(seen)>4096:raise ValueError('The group exceeds the display limit of 4096 elements')
            shift=t+group.rotations[p]*v+group.cocycle[p][r]
            items.append((group.table[p][r],shift,key))
    rows=[]
    for i,(p,t,(phase,eta,bit)) in enumerate(items,1):
        plane=rotation_2d(phase)*Matrix.diag(1,eta)
        spin=(-1)**bit*embed_o2(plane)
        terms=(['1̅'] if bit else [])+(['Rz(2π×'+str(phase)+')'] if phase else [])+(['2_x'] if eta==-1 else [])
        label=' '.join(terms) or '1'
        rows.append({'index':i,'point':p,'spin':spin,'spin_label':label,'primitive_translation':t,
                     'rotation':(basis*group.rotations[p]*basis.inv()).applyfunc(simplify),
                     'translation':(basis*(t+group.translations[p])).applyfunc(simplify)})
    return rows


def translation_generator_rows(detail,parameters=None,approximate=False):
    """Primitive translations and their actual parameterized spin images."""
    from sympy import eye
    name=SSGName.from_dict(detail['name_data'],validate=False)
    _,basis=_parent(name.space_group)
    values=name.parameters if parameters is None else tuple(parameters)
    if len(values)!=name.parameter_count:raise ValueError('Incorrect number of parameters')
    def spin(j):
        if approximate:
            return name._translation(eye(3)[:,j],name.parameters).subs(dict(zip(name.parameters,values))).evalf(10,chop=True)
        return name._translation(eye(3)[:,j],values).applyfunc(simplify)
    return [{'index':j+1,'point':0,'spin':spin(j),
             'rotation':eye(3),'translation':basis[:,j]} for j in range(3)]


def matched_section_rows(detail,match):
    """Spatial point sections and translations in the matched chart's frame."""
    from sympy import Rational,eye,zeros
    from ssg_enumeration.naming import _matrix
    from ssg_enumeration.representations import rotation_2d,embed_o2
    name=SSGName.from_dict(detail['name_data'],validate=False)
    group,basis=_parent(name.space_group);chart=match['chart'];rep=chart.get('representation') or {}
    grading=chart.get('grading') or {};chi=_matrix(grading['k']) if grading else zeros(3,1)
    bits=grading.get('section_bits',[0]*group.order)
    pars=tuple(Rational(v) for v in match['parameters'])
    if 'offset' in rep:
        off,bas=_matrix(rep['offset']),_matrix(rep['basis'])
        if len(pars)!=bas.cols:raise ValueError('Incorrect number of matched parameters')
        values=off+bas*Matrix(pars) if pars else off
        def axial(phase,eta,bit):return (-1)**bit*embed_o2(rotation_2d(phase)*Matrix.diag(1,eta))
        ts=[axial(values[j],1,int(2*chi[j])%2) for j in range(3)]
        ss=[axial(values[3+p],int(rep['eta'][p]),int(bits[p])%2) for p in range(group.order)]
    else:
        dim={'Collinear':1,'Coplanar':2,'Noncoplanar':3}[chart['dimension']]
        def embed(mat):return mat[0,0]*eye(3) if dim==1 else embed_o2(mat) if dim==2 else mat
        ts=[(-1)**int(2*chi[j])*embed(_matrix(rep['translations'][j])) if rep else (-1)**int(2*chi[j])*eye(3) for j in range(3)]
        ss=[(-1)**int(bits[p])*embed(_matrix(rep['sections'][p])) if rep else (-1)**int(bits[p])*eye(3) for p in range(group.order)]
    sections=[{'index':p+1,'point':p,'spin':ss[p],
               'rotation':(basis*group.rotations[p]*basis.inv()).applyfunc(simplify),
               'translation':(basis*group.translations[p]).applyfunc(simplify)} for p in range(group.order)]
    translations=[{'index':j+1,'point':0,'spin':ts[j], 'rotation':eye(3),'translation':basis[:,j]} for j in range(3)]
    return sections,translations


def matched_quotient_rows(detail,match):
    """Exact matched-chart operations; chart parameters are not name parameters."""
    from sympy import Rational,eye,zeros
    from ssg_enumeration.naming import _matrix
    from ssg_enumeration.representations import rotation_2d,embed_o2
    name=SSGName.from_dict(detail['name_data'],validate=False)
    group,basis=_parent(name.space_group)
    chart=match['chart'];rep=chart.get('representation') or {}
    grading=chart.get('grading') or {}
    chi=_matrix(grading['k']) if grading else zeros(3,1)
    bits=grading.get('section_bits',[0]*group.order)
    pars=tuple(Rational(v) for v in match['parameters'])
    if 'offset' in rep:
        off,bas=_matrix(rep['offset']),_matrix(rep['basis'])
        if len(pars)!=bas.cols:raise ValueError('Incorrect number of parameters for the matched representative')
        values=off+bas*Matrix(pars) if pars else off
        tv=[(values[j]%1,1,int(2*chi[j])%2) for j in range(3)]
        sv=[(values[3+p]%1,int(rep['eta'][p]),int(bits[p])%2) for p in range(group.order)]
        rows=_phase_quotient_rows(group,basis,tv,sv)
        trans=[]
        for j,(phase,eta,bit) in enumerate(tv):
            spin=(-1)**bit*embed_o2(rotation_2d(phase)*Matrix.diag(1,eta))
            trans.append({'index':j+1,'point':0,'spin':spin,'spin_label':('1̅ ' if bit else '')+('Rz(2π×'+str(phase)+')' if phase else '1'),
                          'rotation':eye(3),'translation':basis[:,j]})
    else:
        dim={'Collinear':1,'Coplanar':2,'Noncoplanar':3}[chart['dimension']]
        def embed(mat):
            if dim==1:return mat[0,0]*eye(3)
            return embed_o2(mat) if dim==2 else mat
        ts=[(-1)**int(2*chi[j])*embed(_matrix(rep['translations'][j])) if rep else (-1)**int(2*chi[j])*eye(3) for j in range(3)]
        ss=[(-1)**int(bits[p])*embed(_matrix(rep['sections'][p])) if rep else (-1)**int(bits[p])*eye(3) for p in range(group.order)]
        gens=[(0,eye(3)[:,j],ts[j]) for j in range(3)]+[(p,zeros(3,1),ss[p]) for p in range(group.order)]
        items=[(0,zeros(3,1),eye(3))];seen={tuple(eye(3))}
        for p,t,spin in items:
            for r,v,u in gens:
                z=(spin*u).applyfunc(simplify);key=tuple(z)
                if key in seen:continue
                seen.add(key)
                if len(seen)>4096:raise ValueError('The group exceeds the display limit of 4096 elements')
                items.append((group.table[p][r],t+group.rotations[p]*v+group.cocycle[p][r],z))
        rows=[]
        for i,(p,t,spin) in enumerate(items,1):
            actual=ss[p]
            for j in range(3):actual=ts[j]**int(t[j])*actual
            if (actual-spin).applyfunc(simplify)!=zeros(3):raise ValueError('The matched representative has inconsistent spin and spatial operations')
            rows.append({'index':i,'point':p,'spin':spin,
                         'rotation':(basis*group.rotations[p]*basis.inv()).applyfunc(simplify),
                         'translation':(basis*(t+group.translations[p])).applyfunc(simplify)})
        trans=[{'index':j+1,'point':0,'spin':ts[j],'rotation':eye(3),'translation':basis[:,j]} for j in range(3)]
    if len(rows)!=match['crystal']['k_order']:
        raise ValueError('The matched group image order disagrees with the search result')
    return rows,trans
