"""Complete proper affine-normalizer actions for 3D crystallographic groups.

The algorithm uses the rational representation type of the point group, exact
lattice isometries or a finite lattice orbit, then a finite extension-class
orbit and Schreier generators. There is no arbitrary integer-matrix cutoff.
Continuous origin translations centralizing G and inner lattice translations
can be omitted because they act trivially on spin-conjugacy classes.
"""
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from itertools import product, permutations
from math import gcd, isqrt
from sympy import ImmutableMatrix as M, Rational, ilcm
from sympy.matrices.normalforms import hermite_normal_form
from .exact import integer_matrix, mod_vector, is_integral
from .torus import smith_decomposition, annihilator, solve_torus
from .automorphisms import affine_automorphism


def _unique_generators(generators):
    """Drop only identities, duplicates and inverses (no heuristic pruning)."""
    result=[]
    seen={M.eye(3)}
    for a in generators:
        a=integer_matrix(a)
        if a not in seen:
            result.append(a)
            seen.add(a)
            seen.add(integer_matrix(a.inv()))
    return tuple(result)


def _symmetric_generators(generators):
    return tuple(dict.fromkeys(tuple(generators)+tuple(integer_matrix(a.inv()) for a in generators)))


def _matrix_group(generators):
    """Closure for a group already proved finite by a positive metric."""
    seen={M.eye(3)}
    pending=[M.eye(3)]
    while pending:
        a=pending.pop()
        for s in generators:
            b=s*a
            if b not in seen:
                seen.add(b)
                pending.append(b)
    return frozenset(seen)


def _finite_generators(elements):
    elements=frozenset(elements)
    generators=[]
    generated=frozenset({M.eye(3)})
    for a in sorted(elements,key=lambda a:tuple(a)):
        if a not in generated:
            generators.append(a)
            generated=_matrix_group(generators)
    if generated != elements:
        raise ArithmeticError('Finite normalizer elements are not closed.')
    return tuple(generators)


def _integer_kernel(a):
    d,_,v=smith_decomposition(a)
    rank=sum(d[i,i]!=0 for i in range(min(d.shape)))
    return v[:,rank:]


def _primitive_vector(v):
    den=1
    for x in v: den=ilcm(den,x.q)
    entries=[int(x*den) for x in v]
    common=0
    for x in entries: common=gcd(common,abs(x))
    entries=[x//common for x in entries]
    if next(x for x in entries if x) < 0: entries=[-x for x in entries]
    return M(entries)


def invariant_metric_dimension(rotations):
    """Dimension of invariant real symmetric forms: 6,4,3,2,1 in dimension 3."""
    columns=[]
    for i in range(3):
        for j in range(i,3):
            e=M(3,3,lambda a,b:int((a,b)==(i,j) or (a,b)==(j,i)))
            form=sum((r.T*e*r for r in rotations),M.zeros(3))
            columns.append(M([form[a,b] for a in range(3) for b in range(a,3)]))
    return M.hstack(*columns).rank()


def lattice_isometries(metric):
    """All A in GL(3,Z) with A.T*Q*A=Q, using proven ellipsoid bounds."""
    metric=M(metric)
    if metric.shape!=(3,3) or metric!=metric.T or metric.is_positive_definite is not True:
        raise ValueError('Expected an exact positive definite 3D metric.')
    inverse=metric.inv()
    columns=[]
    bounds=[]
    for j in range(3):
        bound=[]
        for i in range(3):
            value=metric[j,j]*inverse[i,i]
            bound.append(isqrt(int(value.p)//int(value.q)))
        bounds.append(tuple(bound))
        vectors=[]
        for raw in product(*(range(-b,b+1) for b in bound)):
            v=M(raw)
            if (v.T*metric*v)[0]==metric[j,j]: vectors.append(v)
        columns.append(vectors)
    result=[]
    for a in columns[0]:
        for b in columns[1]:
            if (a.T*metric*b)[0]!=metric[0,1]: continue
            for c in columns[2]:
                if (a.T*metric*c)[0]!=metric[0,2] or (b.T*metric*c)[0]!=metric[1,2]: continue
                matrix=M.hstack(a,b,c)
                if abs(matrix.det())!=1 or matrix.T*metric*matrix!=metric:
                    raise ArithmeticError('Invalid lattice-isometry certificate.')
                result.append(matrix)
    return tuple(result),tuple(bounds)


def _normalizes(a, rotations):
    inverse=a.inv()
    return {a*r*inverse for r in rotations}==set(rotations)


def _monoclinic_normalizer(rotations):
    r=next(r for r in rotations if r not in (M.eye(3),-M.eye(3)))
    if r*r!=M.eye(3): raise ArithmeticError('Unexpected monoclinic point action.')
    eigenspaces=[_integer_kernel(r-sign*M.eye(3)) for sign in (1,-1)]
    plane=next(b for b in eigenspaces if b.cols==2)
    axis=next(b for b in eigenspaces if b.cols==1)
    change=M.hstack(plane,axis)
    inverse=change.inv()
    # GL(2,Z) x {+/-1} on the saturated eigenlattices. The parent lattice
    # may be an overlattice of their direct sum; take its exact stabilizer.
    ambient=(M([[0,1,0],[1,0,0],[0,0,1]]),
             M([[1,1,0],[0,1,0],[0,0,1]]),
             M.diag(-1,1,1),M.diag(1,1,-1))
    den=abs(int(change.det()))
    def key(t):
        return tuple(hermite_normal_form(integer_matrix(den*t*inverse)))
    base=key(M.eye(3))
    transversals={base:M.eye(3)}
    queue=deque([base])
    generators=[]
    for_s=_symmetric_generators(ambient)
    while queue:
        x=queue.popleft()
        t=transversals[x]
        for s in for_s:
            candidate=s*t
            y=key(candidate)
            if y not in transversals:
                transversals[y]=candidate
                queue.append(y)
            h=transversals[y].inv()*candidate
            if key(h)!=base: raise ArithmeticError('Invalid lattice Schreier element.')
            a=integer_matrix(change*h*inverse)
            if not _normalizes(a,rotations): raise ArithmeticError('Invalid monoclinic normalizer.')
            generators.append(a)
    return _unique_generators(generators),{'eigenlattice_index':den,'lattice_orbit_size':len(transversals)}


@lru_cache(maxsize=128)
def point_normalizer_generators(rotations):
    """Complete generators of N_GL(3,Z)(P), with a structural certificate."""
    rotations=tuple(M(r) for r in rotations)
    dimension=invariant_metric_dimension(rotations)
    certificate={'invariant_metric_dimension':dimension}
    if dimension==6:
        if any(r not in (M.eye(3),-M.eye(3)) for r in rotations):
            raise ArithmeticError('Scalar representation check failed.')
        gens=[]
        for i in range(3):
            for j in range(3):
                if i!=j:
                    a=M.eye(3).as_mutable();a[i,j]=1
                    gens.append(M(a))
        gens.append(M.diag(-1,1,1))
        certificate['method']='scalar_GL3Z'
        return tuple(gens),certificate
    if dimension==4:
        gens,detail=_monoclinic_normalizer(rotations)
        certificate.update(detail)
        certificate['method']='eigenlattice_GL2Z_stabilizer'
        return gens,certificate
    if dimension==3:
        spaces=[M.eye(3)]
        for r in rotations:
            split=[]
            for space in spaces:
                for sign in (1,-1):
                    kernel=(r-sign*M.eye(3))*space
                    vectors=kernel.nullspace()
                    if vectors: split.append(space*M.hstack(*vectors))
            spaces=split
        if len(spaces)!=3 or any(b.cols!=1 for b in spaces):
            raise ArithmeticError('Expected three distinct rational eigenlines.')
        change=M.hstack(*(_primitive_vector(b[:,0]) for b in spaces))
        elements=[]
        for perm in permutations(range(3)):
            for signs in product((-1,1),repeat=3):
                a=M.hstack(*(signs[j]*change[:,perm[j]] for j in range(3)))*change.inv()
                if is_integral(a) and abs(a.det())==1 and _normalizes(a,rotations):
                    elements.append(integer_matrix(a))
        certificate.update(method='primitive_eigenline_permutations',finite_order=len(elements))
        return _finite_generators(elements),certificate
    if dimension not in (1,2):
        raise NotImplementedError('Unsupported point representation; no incomplete normalizer is returned.')
    metric=sum((r.T*r for r in rotations),M.zeros(3))
    elements,bounds=lattice_isometries(metric)
    normalizer=tuple(a for a in elements if _normalizes(a,rotations))
    certificate.update(method='complete_invariant_metric_isometries',
                       finite_order=len(normalizer),isometry_order=len(elements),ellipsoid_bounds=bounds)
    return _finite_generators(normalizer),certificate


def proper_linear_generators(generators):
    """Kernel of determinant via index-two Schreier; never discard negatives."""
    generators=tuple(generators)
    negative=next((a for a in generators if a.det()==-1),None)
    if negative is None: return _unique_generators(generators)
    transversal={1:M.eye(3),-1:negative}
    result=[]
    for t in transversal.values():
        for s in _symmetric_generators(generators):
            candidate=s*t
            h=transversal[int(candidate.det())].inv()*candidate
            if h.det()!=1: raise ArithmeticError('Orientation-kernel certificate failed.')
            result.append(h)
    return _unique_generators(result)


@dataclass(frozen=True)
class CompleteAutomorphismAction:
    generators: tuple
    certificate: dict
    scope: str = 'full_out_plus'


def _sections_under_linear(group, a, sections):
    index={r:i for i,r in enumerate(group.rotations)}
    inverse=a.inv()
    out=[None]*group.order
    for p,r in enumerate(group.rotations):
        out[index[a*r*inverse]]=mod_vector(a*sections[p])
    return tuple(out)


def _origin_system(group):
    return M.vstack(*(M.eye(3)-r for r in group.rotations))


@lru_cache(maxsize=128)
def complete_automorphism_action(group):
    """Full proper affine-normalizer action, modulo spin-trivial inner actions.

    Completeness follows from complete point-normalizer generators, complete
    finite extension-class orbit Schreier generators, and the entire origin
    kernel. Every returned generator is independently checked on G's cocycle.
    """
    canonical_rotations=tuple(sorted(group.rotations,key=lambda r:tuple(r)))
    point_gens,point_certificate=point_normalizer_generators(canonical_rotations)
    proper=proper_linear_generators(point_gens)
    origin_matrix=_origin_system(group)
    characters=annihilator(origin_matrix)
    def flatten(sections): return M.vstack(*sections)
    def extension_key(sections): return tuple(mod_vector(characters*flatten(sections)))
    base=extension_key(group.translations)
    transversals={base:M.eye(3)}
    sections={base:group.translations}
    pending=deque([base])
    stabilizer=[]
    edges=0
    for_s=_symmetric_generators(proper)
    while pending:
        x=pending.popleft()
        t=transversals[x]
        for a in for_s:
            moved=_sections_under_linear(group,a,sections[x])
            y=extension_key(moved)
            candidate=a*t
            if y not in transversals:
                transversals[y]=candidate
                sections[y]=moved
                pending.append(y)
            h=integer_matrix(transversals[y].inv()*candidate)
            if extension_key(_sections_under_linear(group,h,group.translations))!=base:
                raise ArithmeticError('Invalid extension Schreier generator.')
            stabilizer.append(h)
            edges+=1
    actions=[]
    for i,a in enumerate(_unique_generators(stabilizer)):
        rhs=flatten(group.translations)-flatten(_sections_under_linear(group,a,group.translations))
        origins=solve_torus(origin_matrix,rhs)
        if not origins:
            raise ArithmeticError('A certified extension stabilizer has no affine lift.')
        actions.append(affine_automorphism(group,a,origins[0].offset,name=f'linear_lift_{i}'))
    origin_kernel=solve_torus(origin_matrix)
    for i,t in enumerate(origin_kernel):
        if origin_matrix*t.basis!=M.zeros(origin_matrix.rows,t.parameter_count):
            raise ArithmeticError('Continuous origin kernel is not pointwise central.')
        if any(t.offset):
            actions.append(affine_automorphism(group,M.eye(3),t.offset,name=f'origin_{i}'))
    # Remove only identical automorphisms and the literal identity.
    unique={}
    for action in actions:
        key=(action.linear,action.permutation,action.shifts)
        if action.linear==M.eye(3) and action.permutation==tuple(range(group.order)) and not any(any(v) for v in action.shifts):
            continue
        unique.setdefault(key,action)
    certificate={**point_certificate,'point_generator_count':len(point_gens),
        'proper_point_generator_count':len(proper),'extension_orbit_size':len(transversals),
        'schreier_edges_checked':edges,'origin_kernel_components':len(origin_kernel),
        'continuous_origin_dimension':origin_kernel[0].dimension if origin_kernel else 0,
        'generator_count':len(unique),'orientation':'det=+1',
        'modded_out':'inner lattice translations and pointwise-central continuous origins',
        'complete':True,'algorithm':'3d_rational_blocks_and_finite_schreier_v1'}
    return CompleteAutomorphismAction(tuple(unique.values()),certificate)
