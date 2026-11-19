"""Exact axis/order labels for the spatial rotations of parent space groups.

The stored settings name only the generators of the conventional HM symbol.
Every other operation of the group is a product of those generators with
lattice translations, so its symbol has to be derived. The previous display
fell back to a literal ``R`` for all of them, which is why every row of the
operation table showed the same text.

Labels follow the naming spec (``docs/label规则.md`` §7): a rotation of order
``n`` about a direction is ``n_dir`` with an optional ``^j`` for the rotation by
``2*pi*j/n``; an improper operation carries a leading minus and the same
direction, that direction being the axis of the improper operation (the normal,
for a mirror); the identity is ``1`` and the inversion ``-1``. Directions are
``x``, ``y``, ``z`` for the conventional axes and ``[u,v,w]`` otherwise, in
units of the conventional lattice vectors. The Seitz-operation table pairs
each rotation label with its exact translation vector, so operations with the
same rotation part and different translations remain distinguishable.
"""
from functools import lru_cache
from math import gcd

from sympy import ImmutableMatrix as M, Rational, pi, simplify, sin, cos, sqrt

from ssg_enumeration.naming import _clean, _parent


def _system(number):
    return ('a' if number<=2 else 'm' if number<=15 else 'o' if number<=74 else
            't' if number<=142 else 'h' if number<=194 else 'c')


def _cartesian(system):
    """Conventional basis vectors as Cartesian columns.

    Any basis consistent with the crystal system's metric works, because a
    symmetry rotation preserves that metric and therefore acts orthogonally in
    the resulting Cartesian frame. Monoclinic uses a generic angle so that no
    two distinct axes become parallel by accident.
    """
    if system=='h': return M([[1,Rational(-1,2),0],[0,sqrt(3)/2,0],[0,0,1]])
    if system=='m':
        return M([[1,0,Rational(-1,4)],[0,1,0],[0,0,sqrt(15)/4]])
    return M.eye(3)


def _unit(vector):
    vector = M(vector)
    return (vector/sqrt(vector.dot(vector))).applyfunc(simplify)


def _primitive_direction(vector):
    """Canonical integer vector along ``vector``, independent of its scale."""
    values = [Rational(x) for x in vector]
    den = 1
    for x in values: den = den*x.q//gcd(den,x.q)
    ints = [int(x*den) for x in values]
    common = 0
    for x in ints: common = gcd(common,abs(x))
    if common > 1: ints = [x//common for x in ints]
    if next(x for x in ints if x) < 0: ints = [-x for x in ints]
    return tuple(ints)


def direction_name(vector):
    """Short name for a lattice direction: x, y, z, or the exact triple.

    The test is exact in lattice coordinates and needs no metric: a direction
    is called ``x`` only when it *is* the first conventional axis.
    """
    ints = _primitive_direction(vector)
    for name,axis in zip('xyz',((1,0,0),(0,1,0),(0,0,1))):
        if ints == axis: return name
    return '['+','.join(str(x) for x in ints)+']'


def _order(rotation):
    """Exact multiplicative order of a point operation."""
    power = M(rotation)
    for n in range(1,13):
        if _clean(power) == M.eye(3): return n
        power = power*rotation
    raise ValueError('Rotation is not crystallographic')


@lru_cache(maxsize=65536)
def _rotation_symbol_cached(rotation, system='o'):
    """Exact HM symbol for one rotation in conventional lattice coordinates."""
    rotation = _clean(M(rotation))
    if rotation.shape != (3,3) or abs(int(rotation.det())) != 1:
        raise ValueError('Spatial operation must be unimodular')
    if rotation == M.eye(3): return '1'
    if rotation == -M.eye(3): return '-1'
    determinant = int(rotation.det())
    proper = determinant*rotation
    axis = (proper-M.eye(3)).nullspace()[0]
    name = direction_name(axis)
    order = _order(proper)
    if determinant == -1 and order == 2:
        # -R_axis(pi) reflects in the plane normal to the axis.
        return 'm_'+name
    # Rotation sense: the Cartesian rotation vector must point along the axis.
    cart = _cartesian(system)
    rotate = (cart*proper*cart.inv()).applyfunc(simplify)
    vector = M([rotate[2,1]-rotate[1,2],rotate[0,2]-rotate[2,0],rotate[1,0]-rotate[0,1]])
    forward = simplify(vector.dot(cart*_unit(axis))) > 0
    power = 1 if forward else order-1
    if order == 2:return '2_'+name
    return ('-' if determinant == -1 else '')+str(order)+'_'+name+('^'+str(power) if power != 1 else '')


@lru_cache(maxsize=512)
def operation_symbols(number):
    """Symbols for all point operations, in conventional coordinates, table order."""
    group,basis = _parent(number)
    system = _system(number)
    symbols = tuple(_rotation_symbol_cached(_clean(basis*rotation*basis.inv()),system)
                    for rotation in group.rotations)
    if len(set(symbols)) != len(symbols):
        raise ValueError('Point operations did not receive distinct symbols')
    return symbols


def rotation_symbol(rotation, system='o'):
    """Exact HM symbol for one rotation in conventional lattice coordinates."""
    return _rotation_symbol_cached(M(rotation), system)


def symbol_for_rotation(rotation, number):
    """Symbol for a point operation given in conventional coordinates."""
    return _rotation_symbol_cached(M(rotation), _system(number))
