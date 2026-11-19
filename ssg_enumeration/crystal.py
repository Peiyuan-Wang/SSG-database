"""Exact effective-spin images H ⊲ K, the quotient, and the point-group kernel.

For a continuous chart, affine phases are elements of Q + Q*u_1 + ...,
modulo integer constants. Independence of (1,u_1,...) is explicitly a
generic-parameter convention, not a statement about every member of a family.
"""
from collections import Counter
from functools import lru_cache
from hashlib import sha256
from itertools import product
import json
from math import lcm

from sympy import ImmutableMatrix as M, Rational, expand, factorint, symbols
from sympy.matrices.normalforms import hermite_normal_form

from .finite import element_order, quotient_group, small_generating_set, find_isomorphism
from .representations import rotation_2d, embed_o2


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',',':')).encode()).hexdigest()[:24]


@lru_cache(maxsize=131072)
def _mul(a, b):
    return (a*b).applyfunc(expand)


@lru_cache(maxsize=16384)
def _closure(generators):
    identity = M.eye(generators[0].rows)
    found = {identity}
    pending = [identity]
    for a in pending:
        for g in generators:
            b = _mul(a,g)
            if b not in found:
                found.add(b); pending.append(b)
                if len(found)>768:
                    raise ValueError('Finite spin image exceeds the supported exact bound')
    return tuple(sorted(found, key=lambda a:(a!=identity,tuple(map(str,a)))))


@lru_cache(maxsize=4096)
def _matrix_table(elements):
    index={a:i for i,a in enumerate(elements)}
    try:
        return tuple(tuple(index[_mul(a,b)] for b in elements) for a in elements)
    except KeyError as exc:
        raise ValueError('Spin image is not a group') from exc


def _direct_c2(table):
    n=len(table)
    return tuple(tuple(table[a%n][b%n]+n*((a//n)^(b//n)) for b in range(2*n)) for a in range(2*n))


@lru_cache(maxsize=8192)
def abstract_group_name(table):
    n=len(table)
    orders=tuple(element_order(table,i) for i in range(n))
    if all(table[a][b]==table[b][a] for a in range(n) for b in range(n)):
        if n==1: return '1'
        factors=[]
        for prime,exponent in factorint(n).items():
            previous=0; ranks=[]
            for j in range(1,exponent+2):
                count=sum(prime**j % o==0 for o in orders)
                power=0
                while count>1: count//=prime;power+=1
                ranks.append(power-previous);previous=power
            primary=[]
            for j in range(1,len(ranks)):
                primary.extend([int(prime)**j]*(ranks[j-1]-ranks[j]))
            if len(primary)>len(factors): factors=[1]*(len(primary)-len(factors))+factors
            primary=[1]*(len(factors)-len(primary))+primary
            factors=[a*b for a,b in zip(factors,primary)]
        return ' × '.join(f'C{x}' for x in factors)
    from .type0 import rotation_group_catalog
    for name, candidate,_ in rotation_group_catalog():
        for label,t in ((name,candidate),(name+' × C2',_direct_c2(candidate))):
            if len(t)==n and find_isomorphism(table,t) is not None:
                return 'S3' if label=='D3' else label
    return 'Q'+str(n)+'['+_digest(table)[:8]+']'


@lru_cache(maxsize=4096)
def _proper_name(elements):
    if len(elements)==1: return 'C1'
    table=_matrix_table(elements)
    maximum=max(element_order(table,i) for i in range(len(table)))
    n=len(elements)
    if n==maximum: return f'C{n}'
    if n==2*maximum: return f'D{maximum}'
    if (n,maximum)==(12,3): return 'T'
    if (n,maximum)==(24,4): return 'O'
    if (n,maximum)==(60,5): return 'I'
    raise ValueError('Unrecognized proper finite image')


@lru_cache(maxsize=4096)
def finite_image_name(elements):
    d=elements[0].rows
    positive=tuple(a for a in elements if a.det()==1)
    if d==1: return '1' if len(elements)==1 else 'C2'
    if d==2:
        return f'C{len(positive)}' if len(positive)==len(elements) else f'D{len(positive)}'
    proper=_proper_name(positive)
    if len(positive)==len(elements): return '1' if proper=='C1' else proper
    if -M.eye(3) in elements:
        if proper=='C1': return 'Ci'
        if proper[0]=='C':
            n=int(proper[1:]);return f'C{n}h' if n%2==0 else f'S{2*n}'
        if proper[0]=='D':
            n=int(proper[1:]);return f'D{n}'+('h' if n%2==0 else 'd')
        return proper+'h'
    projected=tuple(sorted({int(a.det())*a for a in elements},key=lambda a:(a!=M.eye(3),tuple(map(str,a)))))
    full=_proper_name(projected)
    if full.startswith('C'):
        n=int(full[1:])
        return 'Cs' if n==2 else f'S{n}' if n%4==0 else f'C{n//2}h'
    if full.startswith('D'):
        n=int(full[1:])
        if proper==f'C{n}': return f'C{n}v'
        m=n//2
        return f'D{m}'+('d' if m%2==0 else 'h')
    if full=='O' and proper=='T': return 'Td'
    raise ValueError('Unrecognized improper finite image')


def _validate_projection(table, kernel):
    qt,projection=quotient_group(table,kernel)
    if len(qt)*len(kernel)!=len(table):
        raise ArithmeticError('Quotient order mismatch')
    return qt,projection


@lru_cache(maxsize=32768)
def finite_crystal(translations, sections, point_table):
    """Compute a finite embedded pair and ker(P -> K/H), with exact checks."""
    h=_closure(tuple(translations))
    hs=set(h)
    k=tuple(sorted({_mul(a,b) for a in h for b in sections},
                   key=lambda a:(a!=M.eye(a.rows),tuple(map(str,a)))))
    ks=set(k)
    generators=small_generating_set(point_table)
    for s in set(sections):
        if any(_mul(_mul(s,a),s.T) not in hs for a in translations):
            raise ValueError('Translation image is not normal')
    for p,s in enumerate(sections):
        for r in generators:
            defect=_mul(_mul(s,sections[r]),sections[point_table[p][r]].T)
            if defect not in hs:
                raise ValueError('Point-section products do not induce a quotient homomorphism')
    kernel=tuple(i for i,s in enumerate(sections) if s in hs)
    qt,projection=_validate_projection(point_table,kernel)
    if len(k)!=len(h)*len(qt): raise ValueError('Image/quotient order mismatch')
    kt=_matrix_table(k)
    colors=tuple((str(a.trace()),int(a.det()),int(a in hs),element_order(kt,i)) for i,a in enumerate(k))
    fingerprint=_digest((k[0].rows,sorted(colors)))
    return dict(mode='finite',h_order=len(h),k_order=len(k),q_order=len(qt),
                h_name=finite_image_name(h),k_name=finite_image_name(k),q_name=abstract_group_name(qt),
                kernel=list(kernel),projection=list(projection),q_table=qt,
                pair_fingerprint=fingerprint,
                pair={'dimension':k[0].rows,'table':kt,'colors':colors,
                      'h_indices':[i for i,a in enumerate(k) if a in hs],
                      'matrices':[[[str(x) for x in row] for row in a.tolist()] for a in k]},
                verified=True)


def conjugate_finite_pairs(left, right):
    """Certificate: a trace-preserving group isomorphism carrying H onto H'.

    Equality of real characters implies equivalence of the real orthogonal
    representations; polar decomposition gives an orthogonal intertwiner.
    Thus this is a two-sided criterion for simultaneous orthogonal conjugacy.
    """
    a,b=left['table'],right['table']
    ca,cb=left['colors'],right['colors']
    if left['dimension']!=right['dimension'] or len(a)!=len(b) or sorted(ca)!=sorted(cb): return None
    if a==b and ca==cb: return tuple(range(len(a)))
    gens=small_generating_set(a)
    choices=[[j for j,c in enumerate(cb) if tuple(c)==tuple(ca[g])] for g in gens]
    for images in product(*choices):
        mapping={0:0};inverse={0:0};pending=[0];valid=True
        for x in pending:
            if not valid: break
            for g,h in zip(gens,images):
                y,z=a[x][g],b[mapping[x]][h]
                if y in mapping:
                    if mapping[y]!=z: valid=False;break
                elif z in inverse or tuple(ca[y])!=tuple(cb[z]): valid=False;break
                else: mapping[y]=z;inverse[z]=y;pending.append(y)
        if valid and len(mapping)==len(a):
            phi=tuple(mapping[i] for i in range(len(a)))
            if all(phi[a[x][y]]==b[phi[x]][phi[y]] for x in range(len(a)) for y in range(len(a))): return phi
    return None


@lru_cache(maxsize=32768)
def rational_lattice(columns):
    """Canonical Z-module of rational columns (not its real span)."""
    a=M.hstack(*(M(v) for v in columns))
    den=1
    for x in a: den=lcm(den,int(x.q))
    integral=M(a.rows,a.cols,[int(x*den) for x in a])
    return M(hermite_normal_form(integral))/den


def lattice_contains(basis, vector):
    try:
        solution,params=basis.gauss_jordan_solve(M(vector))
    except ValueError:
        return False
    return not params.rows and all(x.is_integer is True for x in solution)


def _phase_column(phase, bit):
    return tuple(map(Rational,phase))+(Rational(bit),)


def affine_image_name(module, dimension, reflection_bits=()):
    u=(Rational(1),)+symbols(f'u0:{module.rows-2}')
    generators=[]
    for j in range(module.cols):
        coefficients=list(module[:-1,j]);coefficients[0]%=1
        angle=expand(sum(a*b for a,b in zip(coefficients,u)))
        bit=int(module[-1,j])%2
        if angle==0 and not bit: continue
        term='r('+str(angle).replace(' ','')+')' if angle!=0 else ''
        if bit and dimension==3: term+=('·' if term else '')+'j'
        if term: generators.append(term)
    if reflection_bits:
        generators.append(('σ' if dimension==2 else 'x')+('j' if reflection_bits==[1] else ''))
    return '⟨'+', '.join(generators)+'⟩'


@lru_cache(maxsize=32768)
def affine_crystal(translations, sections, point_table, dimension=3):
    """Exact generic quotient using affine phases and parity, without sampling."""
    width=len(translations[0][0])
    units=((Rational(1),)+(Rational(0),)*width,
           (Rational(0),)*width+(Rational(2),))
    h=rational_lattice(tuple(_phase_column(ph,bit) for ph,bit in translations)+units)
    kernel=tuple(p for p,(ph,eta,bit) in enumerate(sections)
                 if eta==1 and lattice_contains(h,_phase_column(ph,bit)))
    qt,projection=_validate_projection(point_table,kernel)
    gens=small_generating_set(point_table)
    for p,(ph,eta,bit) in enumerate(sections):
        for r in gens:
            rh,er,br=sections[r];sh,es,bs=sections[point_table[p][r]]
            delta=tuple(a+eta*b-c for a,b,c in zip(ph,rh,sh))
            if eta*er!=es or not lattice_contains(h,_phase_column(delta,bit+br-bs)):
                raise ValueError('Affine section products fail in K/H')
    # Remove a common reflection phase by one global spin conjugation.
    pivot=next((ph for ph,e,b in sections if e==-1),None)
    normalized=[]
    for ph,e,b in sections:
        normalized.append((tuple(x-y for x,y in zip(ph,pivot)) if e==-1 else ph,e,b))
    rotational=tuple(_phase_column(ph,b) for ph,e,b in normalized if e==1)
    k0=rational_lattice(tuple(tuple(h[:,i]) for i in range(h.cols))+rotational)
    reflection_bits=sorted({b for ph,e,b in normalized if e==-1})
    if reflection_bits and any(int(k0[-1,i])%2 for i in range(k0.cols)):
        reflection_bits=[0,1]
    profile={'dimension':dimension,'h_module':[[str(x) for x in row] for row in h.tolist()],
             'k_rotation_module':[[str(x) for x in row] for row in k0.tolist()],
             'reflection_bits':reflection_bits,'parameter_count':width-1}
    k_description=affine_image_name(k0,dimension,reflection_bits)
    return dict(mode='generic',h_order=None,k_order=None,q_order=len(qt),
                h_name=affine_image_name(h,dimension),k_name=k_description,
                q_name=abstract_group_name(qt),kernel=list(kernel),projection=list(projection),
                q_table=qt,pair_fingerprint=_digest(profile),pair=profile,verified=True,
                assumption='1,u0,... are rationally independent; special values are computed separately',
                translations=[([str(x) for x in ph],bit) for ph,bit in translations],
                sections=[([str(x) for x in ph],e,b) for ph,e,b in sections])


def specialize_affine(translations, sections, point_table, parameters, dimension=3):
    values=(Rational(1),)+tuple(Rational(x) for x in parameters)
    if len(values)!=len(translations[0][0]): raise ValueError('Wrong number of parameters')
    if parameters:
        ts=tuple((sum(a*b for a,b in zip(ph,values))%1,1,bit) for ph,bit in translations)
        ss=tuple((sum(a*b for a,b in zip(ph,values))%1,e,bit) for ph,e,bit in sections)
        return finite_axial_crystal(ts,ss,point_table,dimension)
    def spin(ph,e,bit):
        angle=sum(a*b for a,b in zip(ph,values))
        plane=rotation_2d(angle)*M.diag(1,e)
        return plane if dimension==2 else (-1)**bit*embed_o2(plane)
    ts=tuple(spin(ph,1,b) for ph,b in translations)
    ss=tuple(spin(ph,e,b) for ph,e,b in sections)
    return finite_crystal(ts,ss,point_table)


def finite_axial_crystal(translations, sections, point_table, dimension=3):
    """Finite specialization by rational angles, including noncrystallographic n.

    The explicit finite image is capped before group closure; no result is
    truncated. Large images can still be described by the original generators.
    """
    identity=(Rational(0),1,0)
    def mul(a,b):return ((a[0]+a[1]*b[0])%1,a[1]*b[1],(a[2]+b[2])%2)
    def inv(a):return ((-a[1]*a[0])%1,a[1],a[2])
    denominator=1
    for a in translations+sections:denominator=lcm(denominator,int(a[0].q))
    if denominator>4096:raise ValueError('Finite specialization exceeds the explicit-image limit (phase denominator 4096)')
    h={identity};pending=[identity]
    for a in pending:
        for b in translations:
            c=mul(a,b)
            if c not in h:h.add(c);pending.append(c)
    k={mul(a,b) for a in h for b in sections}
    kernel=tuple(i for i,s in enumerate(sections) if s in h)
    qt,projection=_validate_projection(point_table,kernel)
    gens=small_generating_set(point_table)
    if any(mul(mul(s,sections[r]),inv(sections[point_table[p][r]])) not in h
           for p,s in enumerate(sections) for r in gens):raise ValueError('Specialized quotient relation fails')
    if len(k)!=len(h)*len(qt):raise ValueError('Specialized quotient order mismatch')
    def proper_name(es):
        if len(es)==1:return 'C1'
        maximum=max((lcm(int(a.q),2 if bit else 1) if e==1 else 2) for a,e,bit in es)
        return f'C{len(es)}' if maximum==len(es) else f'D{len(es)//2}'
    def image_name(es):
        if dimension==2:
            n=sum(e==1 for a,e,b in es)
            return f'C{n}' if n==len(es) else f'D{n}'
        positive={t for t in es if t[2]==0};proper=proper_name(positive)
        if len(positive)==len(es):return '1' if proper=='C1' else proper
        if (Rational(0),1,1) in es:
            if proper=='C1':return 'Ci'
            n=int(proper[1:])
            if proper[0]=='C':return f'C{n}h' if n%2==0 else f'S{2*n}'
            return f'D{n}'+('h' if n%2==0 else 'd')
        full=proper_name({(a,e,0) for a,e,b in es});n=int(full[1:])
        if full[0]=='C':return 'Cs' if n==2 else f'S{n}' if n%4==0 else f'C{n//2}h'
        if proper==f'C{n}':return f'C{n}v'
        return f'D{n//2}'+('d' if (n//2)%2==0 else 'h')
    elements=sorted(k)
    return dict(mode='finite',h_order=len(h),k_order=len(k),q_order=len(qt),
                h_name=image_name(h),k_name=image_name(k),q_name=abstract_group_name(qt),
                kernel=list(kernel),projection=list(projection),q_table=qt,verified=True,
                pair={'dimension':dimension,'axial_elements':[[str(a),e,b] for a,e,b in elements],
                      'h_indices':[i for i,t in enumerate(elements) if t in h],
                      'convention':'(turns,eta,inversion_bit); Rz(2*pi*turns) Rx(pi)^((1-eta)/2) (-I)^bit; O(2) uses reflection for eta=-1'})


def analyze_chart(chart, parent, parameters=None):
    """Analyze an exported chart in its fixed primitive basis and section."""
    from .naming import _matrix
    table=tuple(tuple(row) for row in parent['table'])
    dim={'Collinear':1,'Coplanar':2,'Noncoplanar':3}[chart['dimension']]
    grading=chart.get('grading',{})
    qchi=_matrix(grading['k']) if grading else M.zeros(3,1)
    bits=tuple(grading.get('section_bits',[0]*len(table)))
    rep=chart.get('representation')
    if rep and 'offset' in rep:
        off,bas=_matrix(rep['offset']),_matrix(rep['basis'])
        phases=off.row_join(bas)
        ts=tuple((tuple(phases[i,:]),int(2*qchi[i])) for i in range(3))
        ss=tuple((tuple(phases[3+p,:]),int(rep['eta'][p]),bits[p]) for p in range(len(table)))
        if bas.cols and parameters is None: return affine_crystal(ts,ss,table,dim)
        pars=() if parameters is None else tuple(map(Rational,parameters))
        if len(pars)!=bas.cols: raise ValueError('Wrong number of parameters')
        q=off[:3,:]+bas[:3,:]*(M(pars) if pars else M.zeros(0,1))
        if rep['stratum']=='general' and all((2*x).is_integer for x in q):
            raise ValueError('This parameter value is excluded; it belongs to a separate class')
        return specialize_affine(ts,ss,table,pars,dim)
    if parameters: raise ValueError('This record has no parameters')
    ts=tuple(_matrix(a) for a in rep['translations']) if rep else (M.eye(dim),)*3
    ss=tuple(_matrix(a) for a in rep['sections']) if rep else (M.eye(dim),)*len(table)
    ts=tuple((-1)**int(2*qchi[i])*a for i,a in enumerate(ts))
    ss=tuple((-1)**bits[i]*a for i,a in enumerate(ss))
    return finite_crystal(ts,ss,table)


def spin_crystal_class(label, *, parameters=None):
    """Compute H, K, Q, and ker(rho_P) from a bundled SSG or Xiao label.

    The database is not required. With no parameters, a continuous label
    returns the exact generic-parameter result, explicitly marked as such.
    """
    from .naming import name_for_label, _settings
    from .serialization import record_data
    name=name_for_label(label)
    return analyze_chart(record_data(name.to_record()),_settings()[str(name.space_group)],parameters)
