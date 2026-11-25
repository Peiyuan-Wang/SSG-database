"""MD modules 5--7. Conjugations remain in O(2), never swap the normal axis."""
from functools import lru_cache
from dataclasses import replace
from itertools import combinations
from sympy import ImmutableMatrix as Matrix
from .gradings import point_gradings
from .type1 import solve_h1_eta,Type1Record,enumerate_noncoplanar_type1,deduplicate_type1
from .torus import AffineTorus
from .exact import trim_vectors,is_integral
from .type2 import (invariant_kernel_vectors,annihilator_trims,induced_permutations,
    solve_twisted_binary_cocycle,build_monomial_representation,deduplicate_monomial)


@lru_cache(maxsize=128)
def enumerate_coplanar_type0(group):
    out = []
    for eta in point_gradings(group):
        for theta in solve_h1_eta(group,eta):
            torus = AffineTorus(Matrix.zeros(3,1).col_join(theta.offset),
                                Matrix.zeros(3,theta.parameter_count).col_join(theta.basis))
            out.append(Type1Record(eta,torus,"zero",2))
    return deduplicate_type1(out)


def enumerate_coplanar_type1(group, cached_type1=None):
    records = enumerate_noncoplanar_type1(group) if cached_type1 is None else cached_type1
    return tuple(replace(r,spin_dimension=2) for r in records)


@lru_cache(maxsize=128)
def enumerate_coplanar_type2(group):
    out = []
    # D1 branch: the zero character is fixed by convention, not omitted.
    for k in trim_vectors(nonzero=True):
        if not all(is_integral(r.T*k-k) for r in group.rotations):
            continue
        ks = (Matrix.zeros(3,1),k)
        perms = ((0,1),)*group.order
        solutions = solve_twisted_binary_cocycle(group,ks,perms)
        if solutions is not None:
            out.extend(build_monomial_representation(group,ks,perms,bits,image="D1") for bits in solutions)
    # V4 branch: all THREE unordered pairs must be tested for every kernel.
    for t0 in invariant_kernel_vectors(group):
        for ks in combinations(annihilator_trims(t0),2):
            perms = induced_permutations(group,ks)
            if perms is None:
                continue
            solutions = solve_twisted_binary_cocycle(group,ks,perms)
            if solutions is not None:
                out.extend(build_monomial_representation(group,ks,perms,bits) for bits in solutions)
    return deduplicate_monomial(out)

