"""Primitive-lattice space groups and exact Seitz multiplication."""
from dataclasses import dataclass
from functools import cached_property
from itertools import product
from sympy import ImmutableMatrix as Matrix, Rational
from .exact import integer_matrix, exact_matrix, mod_vector, is_integral, matrix_key


@dataclass(frozen=True, eq=False)
class SpaceGroup:
    """R acts on direct lattice columns. Reciprocal action is R^(-T).

    Supply one section per point-group operation in a primitive basis, identity first.
    Out+(G) is separate, explicit input to the enumeration driver.
    """
    rotations: tuple
    translations: tuple
    name: str = "custom"

    def __post_init__(self):
        rs = tuple(integer_matrix(r) for r in self.rotations)
        ts = tuple(exact_matrix(t) for t in self.translations)
        if not rs or len(rs) != len(ts):
            raise ValueError("One translation is required per point operation.")
        if any(r.shape != (3,3) or abs(r.det()) != 1 for r in rs):
            raise ValueError("Rotations must belong to GL(3,Z).")
        if any(t.shape != (3,1) for t in ts):
            raise ValueError("Translations must be three-dimensional columns.")
        if rs[0] != Matrix.eye(3) or ts[0] != Matrix.zeros(3,1):
            raise ValueError("The first section must be (I,0).")
        if len(set(rs)) != len(rs):
            raise ValueError("Repeated rotations: convert a centered conventional cell to a primitive basis.")
        object.__setattr__(self, "rotations", rs)
        object.__setattr__(self, "translations", ts)
        _ = self.table, self.cocycle

    @property
    def order(self):
        return len(self.rotations)

    @cached_property
    def table(self):
        index = {r:i for i,r in enumerate(self.rotations)}
        try:
            return tuple(tuple(index[a*b] for b in self.rotations) for a in self.rotations)
        except KeyError as exc:
            raise ValueError("Point operations are not closed.") from exc

    @cached_property
    def inverse(self):
        return tuple(row.index(0) for row in self.table)

    @cached_property
    def reciprocal_rotations(self):
        return tuple(integer_matrix(r.inv().T) for r in self.rotations)

    @cached_property
    def cocycle(self):
        out = []
        for a in range(self.order):
            row = []
            for b in range(self.order):
                t = self.translations[a] + self.rotations[a]*self.translations[b] - self.translations[self.table[a][b]]
                if not is_integral(t):
                    raise ValueError("Nonintegral section cocycle: sections do not define a primitive space group.")
                row.append(integer_matrix(t))
            out.append(tuple(row))
        return tuple(out)

    def multiply(self, g, h):
        """Multiply (integer translation, point index) pairs."""
        t,a = g
        u,b = h
        t,u = integer_matrix(t),integer_matrix(u)
        if t.shape != (3,1) or u.shape != (3,1):
            raise ValueError("Lattice translations must have three components.")
        return t + self.rotations[a]*u + self.cocycle[a][b], self.table[a][b]

    def validate_cocycle(self):
        for a,b,c in product(range(self.order),repeat=3):
            if self.cocycle[a][b]+self.cocycle[self.table[a][b]][c] != self.rotations[a]*self.cocycle[b][c]+self.cocycle[a][self.table[b][c]]:
                return False
        return True


def from_generators(generators, name="custom", max_order=48):
    """Close Seitz generators modulo primitive translations; reject hidden centering."""
    items = [(Matrix.eye(3), Matrix.zeros(3,1))]
    gens = [(integer_matrix(r),mod_vector(exact_matrix(t))) for r,t in generators]
    index = {items[0][0]:items[0][1]}
    cursor = 0
    while cursor < len(items):
        a,t = items[cursor]
        cursor += 1
        for b,u in gens:
            r,v = a*b,mod_vector(t+a*u)
            if r in index:
                if index[r] != v:
                    raise ValueError("Generators create a fractional pure translation; use a primitive basis.")
                continue
            if len(items) >= max_order:
                raise ValueError("Point group exceeds max_order or is infinite.")
            index[r] = v
            items.append((r,v))
    return SpaceGroup(tuple(r for r,t in items),tuple(t for r,t in items),name)


def example_space_group(name="P1"):
    """Small exact regression/example groups, not a 230-space-group database."""
    z = Matrix.zeros(3,1)
    c2 = Matrix.diag(-1,1,-1)
    c4 = Matrix([[0,-1,0],[1,0,0],[0,0,1]])
    c6 = Matrix([[1,-1,0],[1,0,0],[0,0,1]])
    mirror = Matrix.diag(1,-1,1)
    generators = {
        "P1": [], "P-1": [(-Matrix.eye(3),z)],
        "P2": [(c2,z)], "P21": [(c2,Matrix([0,Rational(1,2),0]))],
        "Pm": [(mirror,z)], "Pc": [(mirror,Matrix([0,0,Rational(1,2)]))],
        "P222": [(Matrix.diag(1,-1,-1),z),(c2,z)],
        "P212121": [(Matrix.diag(1,-1,-1),Matrix([Rational(1,2),Rational(1,2),0])),
                     (c2,Matrix([0,Rational(1,2),Rational(1,2)]))],
        "P4": [(c4,z)], "P41": [(c4,Matrix([0,0,Rational(1,4)]))],
        "P3": [(c6**2,z)], "P31": [(c6**2,Matrix([0,0,Rational(1,3)]))],
        "P6": [(c6,z)],
        "P23": [(Matrix([[0,0,1],[1,0,0],[0,1,0]]),z),(Matrix.diag(1,-1,-1),z)],
        "P432": [(Matrix([[0,0,1],[1,0,0],[0,1,0]]),z),(c4,z)],
    }
    if name not in generators:
        raise ValueError(f"Unknown example {name}; choices: {tuple(generators)}")
    return from_generators(generators[name],name)

