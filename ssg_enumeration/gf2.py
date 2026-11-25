"""Bitset Gaussian elimination over GF(2), including all affine solutions."""
from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class BinarySolution:
    particular: tuple
    basis: tuple

    @property
    def dimension(self):
        return len(self.basis)

    @property
    def count(self):
        return 1 << self.dimension

    def __iter__(self):
        for coeffs in product((0, 1), repeat=self.dimension):
            v = list(self.particular)
            for a, b in zip(coeffs, self.basis):
                if a:
                    v = [x ^ y for x, y in zip(v, b)]
            yield tuple(v)


def solve_gf2(matrix, rhs, nvars=None):
    """Return an affine solution space, or None if inconsistent."""
    rows = [list(row) for row in matrix]
    rhs = list(rhs)
    if len(rows) != len(rhs):
        raise ValueError("Inconsistent row counts.")
    n = len(rows[0]) if rows else (0 if nvars is None else nvars)
    if any(len(row) != n for row in rows):
        raise ValueError("Ragged matrix.")
    if any(int(x) != x for row in rows for x in row) or any(int(x) != x for x in rhs):
        raise ValueError("GF(2) coefficients must be integers.")
    packed = [sum((int(v) % 2) << j for j, v in enumerate(row)) |
              ((int(b) % 2) << n) for row, b in zip(rows, rhs)]
    pivots = []
    r = 0
    for c in range(n):
        pivot = next((i for i in range(r, len(packed)) if packed[i] >> c & 1), None)
        if pivot is None:
            continue
        packed[r], packed[pivot] = packed[pivot], packed[r]
        for i in range(len(packed)):
            if i != r and packed[i] >> c & 1:
                packed[i] ^= packed[r]
        pivots.append(c)
        r += 1
    mask = (1 << n) - 1
    if any((row & mask) == 0 and (row >> n & 1) for row in packed):
        return None
    particular = [0] * n
    for i, c in enumerate(pivots):
        particular[c] = packed[i] >> n & 1
    basis = []
    for free in set(range(n)) - set(pivots):
        v = [0] * n
        v[free] = 1
        for i, c in enumerate(pivots):
            v[c] = packed[i] >> free & 1
        basis.append(tuple(v))
    return BinarySolution(tuple(particular), tuple(basis))

