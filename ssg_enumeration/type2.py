"""MD module 4: invariant translation kernels, S3 action and twisted GF(2)."""
from functools import lru_cache
from itertools import product,permutations
from sympy import ImmutableMatrix as Matrix
from .exact import trim_vectors,mod_vector,is_integral,oriented_permutation,permutation_matrix
from .gf2 import solve_gf2
from .representations import MatrixRepresentation


@lru_cache(maxsize=128)
def invariant_kernel_vectors(group):
    return tuple(Matrix(t) for t in product((0,1),repeat=3)
                 if any(t) and all(mod_vector(r*Matrix(t)-Matrix(t),2) == Matrix.zeros(3,1) for r in group.rotations))


def annihilator_trims(t0):
    t0 = Matrix(t0)
    if t0.shape != (3,1) or not is_integral(t0) or not any(mod_vector(t0,2)):
        raise ValueError("t0 must be a nonzero element of Z^3/2Z^3.")
    return tuple(k for k in trim_vectors(nonzero=True) if k.dot(t0).is_integer is True)


def induced_permutations(group, wavevectors):
    ks = tuple(mod_vector(k) for k in wavevectors)
    if len(set(ks)) != len(ks):
        raise ValueError("Wavevector characters must be distinct.")
    index = {k:i for i,k in enumerate(ks)}
    try:
        return tuple(tuple(index[mod_vector(r*k)] for k in ks) for r in group.reciprocal_rotations)
    except KeyError:
        return None


def build_twisted_binary_system(group, wavevectors, permutations, determinant_one=False):
    d,n = len(wavevectors),group.order
    rows,rhs = [],[]
    for a in range(n):
        inverse = [permutations[a].index(i) for i in range(d)]
        for b in range(n):
            for i,k in enumerate(wavevectors):
                row = [0]*(n*d)
                for j in (a*d+i,b*d+inverse[i],group.table[a][b]*d+i):
                    row[j] ^= 1
                rows.append(row)
                rhs.append(int(2*k.dot(group.cocycle[a][b]))%2)
    if determinant_one:
        for p in range(n):
            row = [0]*(n*d)
            row[p*d:(p+1)*d] = [1]*d
            rows.append(row)
            rhs.append(0)
    return rows,rhs


def solve_twisted_binary_cocycle(group, wavevectors, permutations, determinant_one=False):
    a,b = build_twisted_binary_system(group,wavevectors,permutations,determinant_one)
    return solve_gf2(a,b)


@lru_cache(maxsize=8192)
def monomial_spin_key(rep):
    """Exact conjugacy canonical form for standard Type 2 images.

    Includes ALL translations and ALL sections under a single conjugation.
    For coplanar reps only signed 2D permutations are allowed.
    """
    d = rep.spin_dimension
    matrices = rep.translations+rep.sections
    keys = []
    for perm in permutations(range(d)):
        for signs in product((-1,1),repeat=d):
            # Q and -Q act identically. In odd dimension one is in SO(3).
            if signs[0] != 1:
                continue
            keys.append(tuple(signs[i]*signs[j]*m[perm[i],perm[j]]
                              for m in matrices for i in range(d) for j in range(d)))
    return d,rep.kind,min(keys)


def deduplicate_monomial(records):
    return tuple({monomial_spin_key(r):r for r in records}.values())


def build_monomial_representation(group, wavevectors, perms, bits, oriented=False, image="V4"):
    d = len(wavevectors)
    translations = tuple(Matrix.diag(*[(-1)**int(2*k[j]) for k in wavevectors]) for j in range(3))
    sections = []
    for p in range(group.order):
        diagonal = Matrix.diag(*[(-1)**bits[p*d+i] for i in range(d)])
        lift = oriented_permutation(perms[p]) if oriented else permutation_matrix(perms[p])
        sections.append(diagonal*lift)
    return MatrixRepresentation(translations,tuple(sections),"type2",image,tuple(wavevectors))


@lru_cache(maxsize=128)
def enumerate_noncoplanar_type2(group):
    out = []
    for t0 in invariant_kernel_vectors(group):
        ks = annihilator_trims(t0)
        perms = induced_permutations(group,ks)
        if perms is None:
            raise ArithmeticError("Invariant kernel has a noninvariant annihilator.")
        solutions = solve_twisted_binary_cocycle(group,ks,perms,True)
        if solutions is not None:
            out.extend(build_monomial_representation(group,ks,perms,bits,True) for bits in solutions)
    return deduplicate_monomial(out)

