"""Validated chirality-preserving automorphisms and their pullback action.

Input alpha(t*s(p)) = (A*t + u_p)*s(phi(p)). The complete Out+(G)
generators can be computed by normalizers.complete_automorphism_action or
supplied explicitly. They are never guessed from a bounded matrix search.
"""
from dataclasses import dataclass,replace
from sympy import ImmutableMatrix as Matrix, zeros
from .exact import integer_matrix,exact_matrix,mod_vector,is_integral
from .gradings import Grading
from .type1 import Type1Record,gauge_matrix
from .representations import MatrixRepresentation
from .records import SSG


@dataclass(frozen=True)
class SpaceGroupAutomorphism:
    linear: Matrix
    permutation: tuple
    shifts: tuple
    name: str = "alpha"

    def __post_init__(self):
        a = integer_matrix(self.linear)
        shifts = tuple(integer_matrix(u) for u in self.shifts)
        if a.shape != (3,3) or a.det() != 1:
            raise ValueError("Only chirality-preserving unimodular matrices (det A=+1) are allowed.")
        n = len(self.permutation)
        if sorted(self.permutation) != list(range(n)) or len(shifts) != n or any(u.shape != (3,1) for u in shifts):
            raise ValueError("Invalid point permutation or section shifts.")
        object.__setattr__(self,"linear",a)
        object.__setattr__(self,"shifts",shifts)

    def validate(self, group):
        n = group.order
        if len(self.permutation) != n or self.permutation[0] != 0 or any(self.shifts[0]):
            raise ValueError("Automorphism does not preserve the identity section.")
        for p in range(n):
            if self.linear*group.rotations[p] != group.rotations[self.permutation[p]]*self.linear:
                raise ValueError("Automorphism violates the point action on translations.")
        for a in range(n):
            for b in range(n):
                c = group.table[a][b]
                pa,pb = self.permutation[a],self.permutation[b]
                if self.permutation[c] != group.table[pa][pb]:
                    raise ValueError("Point permutation is not a group automorphism.")
                lhs = self.shifts[a]+group.rotations[pa]*self.shifts[b]+group.cocycle[pa][pb]
                rhs = self.linear*group.cocycle[a][b]+self.shifts[c]
                if lhs != rhs:
                    raise ValueError("Automorphism violates the extension cocycle.")
        return self

    def inverse(self):
        a = integer_matrix(self.linear.inv())
        p = tuple(self.permutation.index(i) for i in range(len(self.permutation)))
        return SpaceGroupAutomorphism(a,p,tuple(-a*self.shifts[p[i]] for i in range(len(p))),self.name+"^-1")

    def compose(self, other):
        """self after other."""
        return SpaceGroupAutomorphism(self.linear*other.linear,
            tuple(self.permutation[i] for i in other.permutation),
            tuple(self.linear*u+self.shifts[p] for u,p in zip(other.shifts,other.permutation)),
            self.name+"*"+other.name)


def affine_automorphism(group, linear, origin=(0,0,0), name="affine"):
    """Conjugation by the affine change of coordinates x -> A*x+origin."""
    a,o = integer_matrix(linear),exact_matrix(origin)
    if a.shape != (3,3) or a.det() != 1 or o.shape != (3,1):
        raise ValueError("Expected A in SL(3,Z) and a rational origin column.")
    index = {r:i for i,r in enumerate(group.rotations)}
    phi,shifts = [],[]
    for r,t in zip(group.rotations,group.translations):
        transformed = a*r*a.inv()
        if transformed not in index:
            raise ValueError("The affine map does not normalize the point group.")
        p = index[transformed]
        phi.append(p)
        shifts.append(integer_matrix(a*t+(Matrix.eye(3)-transformed)*o-group.translations[p]))
    return SpaceGroupAutomorphism(a,tuple(phi),tuple(shifts),name).validate(group)


def p1_outer_generators(group):
    """The six elementary transvections generate Out+(Z^3)=SL(3,Z)."""
    if group.order != 1:
        raise ValueError("This complete generator set is only for pure translations P1.")
    out = []
    for i in range(3):
        for j in range(3):
            if i != j:
                a = zeros(3)
                for k in range(3): a[k,k] = 1
                a[i,j] = 1
                out.append(affine_automorphism(group,a,name=f"E{i+1}{j+1}"))
    return tuple(out)


def transform_grading(grading, alpha):
    return Grading(mod_vector(alpha.linear.T*grading.k),
        tuple((grading.bits[p]+int(2*grading.k.dot(u)))%2 for p,u in zip(alpha.permutation,alpha.shifts)))


def type1_pullback_matrix(record, alpha):
    n = len(record.eta)
    raw = zeros(3+n)
    raw[:3,:3] = alpha.linear.T
    for p in range(n):
        raw[3+p,:3] = alpha.shifts[p].T
        raw[3+p,3+alpha.permutation[p]] = 1
    eta = tuple(record.eta[p] for p in alpha.permutation)
    return gauge_matrix(eta)*Matrix(raw)


def transform_representation(rep, alpha):
    if isinstance(rep,Type1Record):
        eta = tuple(rep.eta[p] for p in alpha.permutation)
        return replace(rep,eta=eta,torus=rep.torus.transform(type1_pullback_matrix(rep,alpha)))
    translations = tuple(rep.translation(alpha.linear[:,j]) for j in range(3))
    sections = tuple(rep.translation(u)*rep.sections[p] for p,u in zip(alpha.permutation,alpha.shifts))
    wavevectors = tuple(mod_vector(alpha.linear.T*k) for k in rep.wavevectors)
    kernel = tuple(i for i,m in enumerate(sections) if m == Matrix.eye(rep.spin_dimension)) if rep.kind == 'type0' else ()
    return replace(rep,translations=translations,sections=sections,wavevectors=wavevectors,kernel=kernel)


def transform_ssg(ssg, alpha):
    return SSG(ssg.dimension,
        None if ssg.representation is None else transform_representation(ssg.representation,alpha),
        None if ssg.grading is None else transform_grading(ssg.grading,alpha))

