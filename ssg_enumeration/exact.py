"""Exact arithmetic helpers; no floating point is used to decide equivalence."""
from itertools import product
from sympy import ImmutableMatrix as Matrix, Rational, eye, floor, sympify, Float


def exact_matrix(value):
    m = Matrix(value)
    if any(x.is_Rational is not True for x in m):
        raise ValueError("Use exact integers/rationals (e.g. Rational(1, 2)), not floats.")
    return m


def integer_matrix(value):
    m = exact_matrix(value)
    if any(x.q != 1 for x in m):
        raise ValueError("An integer matrix is required.")
    return Matrix(m.rows, m.cols, [int(x) for x in m])


def exact_point(value):
    """Exact real parameter values, including irrational algebraic numbers."""
    m = Matrix(value)
    if any(x.has(Float) or x.free_symbols or x.is_real is not True for x in m):
        raise ValueError("Use exact real values (Rational, sqrt, pi); use symbolic() for free parameters.")
    return m


def mod1(x):
    x = sympify(x)
    return x - floor(x)


def mod_vector(v, modulus=1):
    v = Matrix(v)
    return Matrix(v.rows, v.cols, [x % modulus for x in v])


def is_integral(v):
    return all(x.is_integer is True for x in v)


def matrix_key(m):
    return (m.rows, m.cols, tuple(m))


def trim_vectors(nonzero=False):
    return tuple(Matrix([Rational(a, 2) for a in bits])
                 for bits in product((0, 1), repeat=3) if not nonzero or any(bits))


def is_trim(k):
    return is_integral(2 * Matrix(k))


def permutation_matrix(perm):
    """Column j is e_perm[j]."""
    if sorted(perm) != list(range(len(perm))):
        raise ValueError("Not a permutation.")
    return Matrix(len(perm), len(perm), lambda i, j: int(i == perm[j]))


def oriented_permutation(perm):
    """S3 -> SO(3), sigma -> sign(sigma) P_sigma, a genuine homomorphism."""
    if len(perm) != 3:
        raise ValueError("This SO(3) lift requires three axes.")
    p = permutation_matrix(perm)
    return p.det() * p

