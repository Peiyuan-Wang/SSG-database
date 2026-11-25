"""Optional standard parent-space-group input from spglib, never SSG counts.

Conventional Hall operations are converted to the full primitive translation
lattice exactly before passing them to the package's enumeration algorithms.
"""
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
from sympy import ImmutableMatrix as Matrix, Rational, ilcm
from sympy.matrices.normalforms import hermite_normal_form
from .exact import integer_matrix, mod_vector
from .groups import SpaceGroup


def _spglib():
    try:
        import spglib
    except ImportError as exc:
        raise ImportError("Standard parent input requires the optional spglib dependency.") from exc
    return spglib


@lru_cache(maxsize=1)
def standard_hall_numbers():
    """One deterministic Hall setting (first database setting) per ITA number."""
    spglib = _spglib()
    choices = {}
    for hall in range(1,531):
        info = spglib.get_spacegroup_type(hall)
        if info is None:
            raise ValueError(f"Missing Hall type {hall}.")
        choices.setdefault(int(info.number),hall)
    if set(choices) != set(range(1,231)):
        raise ValueError("The input database does not cover all 230 space-group types.")
    return choices


def _database_rational(x):
    value = Fraction(float(x)).limit_denominator(48)
    if abs(float(value)-float(x)) > 1e-12:
        raise ValueError("Database translation cannot be recovered as a small exact rational.")
    return Rational(value.numerator,value.denominator)


def primitive_operations(rotations, translations):
    """Return primitive basis, distinct rotations and reduced section shifts."""
    identity = Matrix.eye(3)
    rotations = tuple(integer_matrix(r) for r in rotations)
    translations = tuple(Matrix(t) for t in translations)
    if len(rotations) != len(translations):
        raise ValueError("Operation counts differ.")
    centering = tuple(t for r,t in zip(rotations,translations) if r == identity)
    if not centering:
        raise ValueError("No translation coset in the input operations.")
    columns = Matrix.hstack(identity,*centering)
    den = 1
    for x in columns:
        den = ilcm(den,x.q)
    basis = Matrix(hermite_normal_form(integer_matrix(columns*den)))/den
    if abs(basis.det())*len(centering) != 1:
        raise ValueError("Centering multiplicity and primitive lattice index disagree.")
    inverse = basis.inv()
    sections = {}
    for r,t in zip(rotations,translations):
        rp,tp = integer_matrix(inverse*r*basis),mod_vector(inverse*t)
        if rp in sections and sections[rp] != tp:
            raise ValueError("Distinct translations remain for the same rotation after primitive conversion.")
        sections[rp] = tp
    if identity not in sections or any(sections[identity]):
        raise ValueError("Invalid primitive identity section.")
    ordered = [identity]+[r for r in sections if r != identity]
    return basis,tuple(ordered),tuple(sections[r] for r in ordered)


def load_standard_space_group(number, hall_number=None):
    """Return (SpaceGroup, provenance) for one of ITA numbers 1..230."""
    if not isinstance(number,int) or isinstance(number,bool) or not 1 <= number <= 230:
        raise ValueError("The international space-group number must be in 1..230.")
    spglib = _spglib()
    hall = standard_hall_numbers()[number] if hall_number is None else int(hall_number)
    info = spglib.get_spacegroup_type(hall)
    if info is None or int(info.number) != number:
        raise ValueError("Hall setting does not belong to the requested space-group type.")
    ops = spglib.get_symmetry_from_database(hall)
    if ops is None:
        raise ValueError("No symmetry operations returned.")
    rs = tuple(integer_matrix(r.tolist()) for r in ops['rotations'])
    ts = tuple(Matrix([_database_rational(x) for x in t]) for t in ops['translations'])
    basis,rotations,translations = primitive_operations(rs,ts)
    group = SpaceGroup(rotations,translations,f"{number}: {info.international_short}")
    fingerprint = sha256(repr([(tuple(r),tuple(t)) for r,t in zip(rotations,translations)]).encode()).hexdigest()
    metadata = {'number':number,'international_short':info.international_short,'hall_number':hall,
                'hall_symbol':info.hall_symbol,'setting_choice':info.choice,
                'point_group':info.pointgroup_international,'point_order':group.order,
                'conventional_operation_count':len(rs),'centering_index':int(1/abs(basis.det())),
                'primitive_basis':[[str(x) for x in row] for row in basis.tolist()],
                'input_sha256':fingerprint,'parent_source':'spglib.get_symmetry_from_database',
                'spglib_version':spglib.__version__}
    return group,metadata


def space_group_from_number(number, hall_number=None):
    """Convenience input for enumerate_ssg; SSGs are computed by this package."""
    return load_standard_space_group(number,hall_number)[0]
