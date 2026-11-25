"""Public SSG records and composition of spin homomorphisms with Z2 gradings."""
from dataclasses import dataclass
from sympy import ImmutableMatrix as Matrix
from .labels import label_17


@dataclass(frozen=True)
class SSG:
    dimension: str
    representation: object = None
    grading: object = None

    @property
    def label(self):
        return label_17(self.dimension,self.representation,self.grading)

    @property
    def type(self):
        return self.label

    @property
    def category(self):
        """The 17-category field; distinct from a complete formal name."""
        return self.label

    def name(self, space_group):
        """Return the canonical, evaluable name in the standard catalogue."""
        from .naming import label_for_record, name_for_label
        return name_for_label(label_for_record(space_group,self))

    @property
    def parameter_count(self):
        return 0 if self.representation is None else self.representation.parameter_count

    def evaluate(self, translation, point=0, parameters=(), embedded=True):
        """Return varrho(t s(p)); collinear reps use chi*I3 as in the MD."""
        if self.dimension == 'Collinear':
            if parameters:
                raise ValueError("Collinear records have no parameters.")
            return self.grading.evaluate(translation,point)*Matrix.eye(3)
        rho = self.representation.evaluate(translation,point,parameters,embedded=embedded)
        return rho if self.grading is None else self.grading.evaluate(translation,point)*rho


def build_collinear_ssgs(gradings):
    return tuple(SSG('Collinear',grading=chi) for chi in gradings)


def combine(representation, grading):
    return SSG('Noncoplanar',representation,grading)

