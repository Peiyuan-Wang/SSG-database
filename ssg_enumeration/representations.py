"""Evaluable representations with native O(2) or SO(3) matrices."""
from dataclasses import dataclass
from sympy import ImmutableMatrix as Matrix, cos, sin, pi, diag
from .exact import integer_matrix


def rotation_2d(turns):
    c,s = cos(2*pi*turns),sin(2*pi*turns)
    return Matrix([[c,-s],[s,c]])


def embed_o2(m):
    m = Matrix(m)
    if m.shape != (2,2):
        raise ValueError("Expected a 2x2 matrix.")
    return Matrix.diag(m,m.det())


@dataclass(frozen=True)
class MatrixRepresentation:
    translations: tuple
    sections: tuple
    kind: str
    image: str = ""
    wavevectors: tuple = ()
    kernel: tuple = ()

    @property
    def spin_dimension(self):
        return self.sections[0].rows

    @property
    def parameter_count(self):
        return 0

    def translation(self, t):
        t = integer_matrix(t)
        if t.shape != (3,1):
            raise ValueError("Expected a lattice vector.")
        out = Matrix.eye(self.spin_dimension)
        for a,power in zip(self.translations,t):
            out = out * a**int(power)
        return out

    def evaluate(self, t, point, parameters=(), embedded=False):
        if parameters:
            raise ValueError("This representation has no continuous parameters.")
        out = self.translation(t)*self.sections[point]
        return embed_o2(out) if embedded and self.spin_dimension == 2 else out

