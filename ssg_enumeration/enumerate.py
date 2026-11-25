"""MD main algorithm: modular enumeration, reuse, verification and quotient."""
from dataclasses import replace
from .gradings import enumerate_gradings
from .type0 import enumerate_noncoplanar_type0
from .type1 import enumerate_noncoplanar_type1
from .type2 import enumerate_noncoplanar_type2
from .coplanar import enumerate_coplanar_type0,enumerate_coplanar_type1,enumerate_coplanar_type2
from .records import SSG,combine,build_collinear_ssgs
from .validation import validate_representation
from .deduplication import deduplicate_automorphisms
from .automorphisms import p1_outer_generators
from .normalizers import complete_automorphism_action, CompleteAutomorphismAction


def enumerate_ssg(group, automorphisms=None, verify=True, progress=None):
    """Enumerate all three dimensions according to the supplied MD.

    automorphisms=None: spin quotient only, explicitly reported.
    automorphisms='full': complete proper affine-normalizer action for any 3D space group.
    automorphisms='p1_full': legacy full Out+(Z^3) presentation for P1.
    automorphisms=iterable: quotient by exactly the supplied subgroup generators.
    progress(module_name, count) is called after each module passes verification.
    """
    scope = None
    certificate = None
    if isinstance(automorphisms,str):
        if automorphisms == 'full':
            automorphisms = complete_automorphism_action(group)
        elif automorphisms == 'p1_full':
            automorphisms = p1_outer_generators(group)
            scope = 'full_out_plus_P1'
        else:
            raise ValueError("Expected 'full', 'p1_full', None, or automorphism generators.")
    if isinstance(automorphisms,CompleteAutomorphismAction):
        certificate = automorphisms.certificate
        scope = automorphisms.scope
        automorphisms = automorphisms.generators
    actions = tuple(automorphisms or ())
    for a in actions:
        a.validate(group)
    if progress and certificate is not None: progress('complete_spatial_automorphisms',len(actions))
    def checked(name,records):
        if verify:
            for r in records:
                if not validate_representation(group,r):
                    raise ArithmeticError(f"Homomorphism verification failed in {name}.")
        if progress:
            progress(name,len(records))
        return records
    gradings = enumerate_gradings(group)
    if progress: progress('gradings',len(gradings))
    records = list(build_collinear_ssgs(gradings))
    type0 = checked('noncoplanar_type0',enumerate_noncoplanar_type0(group))
    type1 = checked('noncoplanar_type1',enumerate_noncoplanar_type1(group))
    type2 = checked('noncoplanar_type2',enumerate_noncoplanar_type2(group))
    records.extend(combine(r,chi) for r in type0+type1+type2 for chi in gradings)
    p0 = checked('coplanar_type0',enumerate_coplanar_type0(group))
    p1 = checked('coplanar_type1',enumerate_coplanar_type1(group,type1))
    p2 = checked('coplanar_type2',enumerate_coplanar_type2(group))
    records.extend(SSG('Coplanar',r) for r in p0+p1+p2)
    result = deduplicate_automorphisms(records,actions,scope,verified=verify)
    result = replace(result,normalizer_certificate=certificate)
    if progress: progress('quotient_and_labels',len(result))
    return result

