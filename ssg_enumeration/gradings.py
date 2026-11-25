"""MD module 1: H^1(G,Z2), including nonsymmorphic extension constraints."""
from dataclasses import dataclass
from functools import lru_cache
from sympy import ImmutableMatrix as Matrix
from .exact import trim_vectors, is_integral
from .gf2 import solve_gf2


@dataclass(frozen=True)
class Grading:
    k: Matrix
    bits: tuple

    @property
    def signs(self):
        return tuple((-1)**b for b in self.bits)

    def evaluate(self, translation, point):
        phase = 2 * (self.k.dot(Matrix(translation)))
        if phase.is_integer is not True:
            raise ValueError("Translation must be a lattice vector.")
        return (-1)**((int(phase)+self.bits[point]) % 2)

    @property
    def key(self):
        return tuple(self.k), self.bits


def build_grading_system(group, k):
    k = Matrix(k)
    rows,rhs = [],[]
    for a in range(group.order):
        for b in range(group.order):
            row = [0]*group.order
            for p in (a,b,group.table[a][b]):
                row[p] ^= 1
            rows.append(row)
            value = 2*k.dot(group.cocycle[a][b])
            if value.is_integer is not True:
                raise ValueError("The grading wavevector must be a TRIM.")
            rhs.append(int(value)%2)
    return rows,rhs


@lru_cache(maxsize=128)
def enumerate_gradings(group):
    out = []
    for k in trim_vectors():
        if not all(is_integral(r.T*k-k) for r in group.rotations):
            continue
        a,b = build_grading_system(group,k)
        solutions = solve_gf2(a,b)
        if solutions is not None:
            out.extend(Grading(k,bits) for bits in solutions)
    return tuple(out)


@lru_cache(maxsize=128)
def point_gradings(group):
    return tuple(g.signs for g in enumerate_gradings(group) if not any(g.k))

