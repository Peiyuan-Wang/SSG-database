"""MD section 8: the 17 labels describe strata, not whole unsplit parameter tori."""
from .type1 import Type1Record

LABELS = ('L.0.1','L.0.2','P.0','P.1.1','P.1.2','P.2.1','P.2.2',
          'N.0.1','N.0.2','N.1.1','N.1.2','N.1.3','N.1.4','N.1.5',
          'N.2.1','N.2.2','N.2.3')


def label_17(dimension, representation=None, grading=None):
    if dimension == 'Collinear':
        if grading is None:
            raise ValueError("A collinear record requires its grading.")
        return 'L.0.2' if any(grading.k) else 'L.0.1'
    if dimension == 'Coplanar':
        if representation.spin_dimension != 2:
            raise ValueError("Coplanar representations must be native O(2) matrices.")
        if representation.kind == 'type0': return 'P.0'
        if representation.kind == 'type1':
            return 'P.1.1' if representation.stratum == 'trim' else 'P.1.2'
        return 'P.2.1' if representation.image == 'D1' else 'P.2.2'
    if dimension != 'Noncoplanar' or grading is None or representation.spin_dimension != 3:
        raise ValueError("Invalid dimension, representation or missing grading.")
    kchi = grading.k
    if representation.kind == 'type0': return 'N.0.2' if any(kchi) else 'N.0.1'
    if representation.kind == 'type1':
        trim = representation.stratum == 'trim'
        if not any(kchi): return 'N.1.1' if trim else 'N.1.2'
        if not trim: return 'N.1.5'
        return 'N.1.3' if kchi == representation.torus.offset[:3,:] else 'N.1.4'
    if not any(kchi): return 'N.2.1'
    return 'N.2.2' if kchi in representation.wavevectors else 'N.2.3'

