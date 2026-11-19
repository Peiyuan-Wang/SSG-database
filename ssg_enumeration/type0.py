"""MD module 2: normal kernels and crystallographic finite SO(3) quotients."""
from functools import lru_cache
from itertools import permutations, product
from sympy import ImmutableMatrix as Matrix
from .exact import permutation_matrix
from .representations import rotation_2d, embed_o2, MatrixRepresentation
from .finite import normal_subgroups, quotient_group, find_isomorphism


def _cyclic_dihedral(n, dihedral=False):
    from sympy import Rational
    pairs = [(i,j) for j in range(2 if dihedral else 1) for i in range(n)]
    lookup = {p:i for i,p in enumerate(pairs)}
    table = tuple(tuple(lookup[((a+(-1)**b*c)%n,(b+d)%2)] for c,d in pairs) for a,b in pairs)
    matrices = tuple(embed_o2(rotation_2d(Rational(a,n))*Matrix.diag(1,(-1)**b)) for a,b in pairs)
    return table,matrices


@lru_cache(maxsize=1)
def rotation_group_catalog():
    """C1,C2,C3,C4,C6; D2,D3,D4,D6; tetrahedral T; octahedral O."""
    out = []
    for n in (1,2,3,4,6):
        out.append((f"C{n}",*_cyclic_dihedral(n)))
    for n in (2,3,4,6):
        out.append((f"D{n}",*_cyclic_dihedral(n,True)))
    for name in ("T","O"):
        matrices = []
        for perm in permutations(range(3)):
            p = permutation_matrix(perm)
            if name == "T" and p.det() != 1:
                continue
            for signs in product((-1,1),repeat=3):
                m = Matrix.diag(*signs)*p
                if m.det() == 1:
                    matrices.append(m)
        matrices.sort(key=lambda m:(m != Matrix.eye(3),tuple(m)))
        idx = {m:i for i,m in enumerate(matrices)}
        table = tuple(tuple(idx[a*b] for b in matrices) for a in matrices)
        out.append((name,table,tuple(matrices)))
    return tuple(out)


@lru_cache(maxsize=128)
def enumerate_noncoplanar_type0(group):
    out = []
    for h in normal_subgroups(group.table):
        q,projection = quotient_group(group.table,h)
        for name,table,matrices in rotation_group_catalog():
            if len(table) != len(q):
                continue
            phi = find_isomorphism(q,table)
            if phi is not None:
                out.append(MatrixRepresentation((Matrix.eye(3),)*3,
                    tuple(matrices[phi[projection[p]]] for p in range(group.order)),
                    "type0",name,kernel=tuple(sorted(h))))
    return tuple(out)

