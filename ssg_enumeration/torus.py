"""Exact affine subtori of R^n/Z^n, including torsion and parameter identifications."""
from dataclasses import dataclass
from functools import cached_property
from itertools import product
from math import prod
from sympy import ImmutableMatrix as Matrix, Rational, ZZ, ilcm, zeros, symbols
from sympy.matrices.normalforms import hermite_normal_form, smith_normal_decomp
from .exact import exact_matrix, exact_point, integer_matrix, mod_vector, is_integral, matrix_key


def smith_decomposition(a):
    """Return D,U,V with U*A*V=D; verify the certificates, including unimodularity."""
    a = integer_matrix(a)
    if not a.rows or not a.cols:
        return a, Matrix.eye(a.rows), Matrix.eye(a.cols)
    d, u, v = map(Matrix, smith_normal_decomp(a, domain=ZZ))
    if u * a * v != d or abs(u.det()) != 1 or abs(v.det()) != 1:
        raise ArithmeticError("Invalid Smith certificate from the algebra backend.")
    return d, u, v


def reduce_congruences(a, b):
    """Compress the integer row lattice without discarding torsion constraints."""
    a, b = integer_matrix(a), exact_matrix(b)
    if b.shape != (a.rows, 1):
        raise ValueError("rhs must be a column with one entry per equation.")
    if a.rows == 0:
        return a, b
    den = 1
    for x in b:
        den = ilcm(den, x.q)
    h = hermite_normal_form(integer_matrix(a.row_join(b * den).T)).T
    return Matrix(h[:, :a.cols]), Matrix(h[:, a.cols:]) / den


def annihilator(basis):
    """Primitive integer equations for the connected image of an integer matrix."""
    basis = integer_matrix(basis)
    _, _, v = smith_decomposition(basis.T)
    rank = basis.rank()
    c = v[:, rank:].T
    return Matrix(hermite_normal_form(c.T).T) if c.rows else Matrix.zeros(0, basis.rows)


@dataclass(frozen=True)
class AffineTorus:
    """x = offset + basis*u mod 1, u in R^d/Z^d; basis is integral."""
    offset: Matrix
    basis: Matrix

    def __post_init__(self):
        o, b = exact_matrix(self.offset), integer_matrix(self.basis)
        if o.cols != 1 or b.rows != o.rows:
            raise ValueError("Invalid affine torus shapes.")
        object.__setattr__(self, "offset", mod_vector(o))
        object.__setattr__(self, "basis", b)

    @property
    def dimension(self):
        return self.basis.rank()

    @property
    def parameter_count(self):
        return self.basis.cols

    @cached_property
    def constraints(self):
        c = annihilator(self.basis)
        return c, mod_vector(c * self.offset)

    @cached_property
    def key(self):
        c, b = self.constraints
        return matrix_key(c), tuple(b)

    def contains(self, x):
        x = exact_point(x)
        c, b = self.constraints
        return x.shape == self.offset.shape and is_integral(c * x - b)

    def evaluate(self, parameters=()):
        if len(parameters) != self.parameter_count:
            raise ValueError("Wrong number of torus parameters.")
        u = exact_point(parameters) if len(parameters) else Matrix.zeros(0, 1)
        return mod_vector(self.offset + self.basis * u)

    def symbolic(self, prefix="u"):
        params = symbols(f"{prefix}0:{self.parameter_count}", real=True)
        u = Matrix(params) if params else Matrix.zeros(0, 1)
        return params, self.offset + self.basis * u

    def transform(self, linear, shift=None):
        linear = integer_matrix(linear)
        shift = Matrix.zeros(linear.rows, 1) if shift is None else exact_matrix(shift)
        return AffineTorus(linear * self.offset + shift, linear * self.basis)

    def intersect(self, a, b, max_components=100000):
        a, b = integer_matrix(a), exact_matrix(b)
        return tuple(AffineTorus(self.offset + self.basis * t.offset, self.basis * t.basis)
                     for t in solve_torus(a * self.basis, b - a * self.offset,
                                          max_components=max_components))


def solve_torus(a, b=None, max_components=100000):
    """All connected components of A*x=b mod 1, without sampling.

    Resource limits raise explicitly; no truncated result is returned.
    """
    a = integer_matrix(a)
    b = Matrix.zeros(a.rows, 1) if b is None else exact_matrix(b)
    a, b = reduce_congruences(a, b)
    d, u, v = smith_decomposition(a)
    rhs = u * b
    rank = sum(d[i, i] != 0 for i in range(min(d.shape)))
    if not is_integral(rhs[rank:, :]):
        return ()
    orders = [abs(int(d[i, i])) for i in range(rank)]
    if max_components is not None and prod(orders) > max_components:
        raise OverflowError("Too many torsion components; raise max_components explicitly.")
    out = []
    for digits in product(*(range(n) for n in orders)):
        y = zeros(a.cols, 1)
        for i, digit in enumerate(digits):
            y[i] = (rhs[i] + digit) / d[i, i]
        out.append(AffineTorus(Matrix(v * y), Matrix(v[:, rank:])))
    return tuple(out)


@dataclass(frozen=True)
class ParameterRelation:
    """Exact relation A*u + B*v = rhs mod 1 between two parameter charts."""
    source: Matrix
    target: Matrix
    rhs: Matrix

    def holds(self, u, v):
        u = exact_matrix(u) if u else Matrix.zeros(0, 1)
        v = exact_matrix(v) if v else Matrix.zeros(0, 1)
        return is_integral(self.source * u + self.target * v - self.rhs)

    def solution_components(self):
        return solve_torus(self.source.row_join(self.target), self.rhs)


def parameter_relation(source, target, linear=None):
    """Relate target(v)=linear*source(u), including covering and monodromy."""
    linear = Matrix.eye(source.offset.rows) if linear is None else integer_matrix(linear)
    return ParameterRelation(linear * source.basis, -target.basis,
                             target.offset - linear * source.offset)

