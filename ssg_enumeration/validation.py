"""Exhaustive defining-relation checks and independent spin equivalence tests."""
from itertools import product
from sympy import Matrix, ImmutableMatrix, symbols, simplify
from .exact import is_integral
from .type1 import Type1Record,joint_type1_system


def zero_matrix(m):
    return all(simplify(x) == 0 for x in m)


def validate_representation(group, rep):
    """Check every defining relation, symbolically for a whole continuous family."""
    if isinstance(rep,Type1Record):
        a = joint_type1_system(group,rep.eta)
        return is_integral(a*rep.torus.offset) and zero_matrix(a*rep.torus.basis)
    d = rep.spin_dimension
    identity = Matrix.eye(d)
    all_matrices = rep.translations+rep.sections
    if any(not zero_matrix(m.T*m-identity) for m in all_matrices):
        return False
    if d == 3 and any(simplify(m.det()-1) != 0 for m in all_matrices):
        return False
    for a,b in product(rep.translations,repeat=2):
        if not zero_matrix(a*b-b*a):
            return False
    for p in range(group.order):
        for j in range(3):
            if not zero_matrix(rep.sections[p]*rep.translations[j]*rep.sections[p].T-rep.translation(group.rotations[p][:,j])):
                return False
    for a,b in product(range(group.order),repeat=2):
        if not zero_matrix(rep.sections[a]*rep.sections[b]-rep.translation(group.cocycle[a][b])*rep.sections[group.table[a][b]]):
            return False
    return True


def spin_equivalent_matrices(first, second):
    """Exact simultaneous O(d) equivalence via invertible intertwiners.

    For SO(3) representations O(3) and SO(3) conjugacy coincide: negate
    an orientation-reversing intertwiner. No random sampling is used.
    """
    if len(first) != len(second) or not first:
        return False
    d = first[0].rows
    if any(a.shape != (d,d) or b.shape != (d,d) for a,b in zip(first,second)):
        return False
    if any(simplify(a.trace()-b.trace()) != 0 for a,b in zip(first,second)):
        return False
    unknowns = symbols(f"z0:{d*d}")
    x = Matrix(d,d,unknowns)
    equations = Matrix([v for a,b in zip(first,second) for v in (a*x-x*b)])
    coefficient = equations.jacobian(unknowns)
    basis = coefficient.nullspace()
    if not basis:
        return False
    parameters = symbols(f"v0:{len(basis)}")
    candidate = sum((t*Matrix(d,d,b) for t,b in zip(parameters,basis)),Matrix.zeros(d))
    return simplify(candidate.det().expand()) != 0

