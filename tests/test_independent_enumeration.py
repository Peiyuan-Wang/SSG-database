"""Small-group cross checks using direct matrix enumeration, independent of cocycle solvers."""
import unittest
from itertools import product
from sympy import ImmutableMatrix as M,Rational as Q
from ssg_enumeration import (example_space_group,rotation_group_catalog,
    enumerate_noncoplanar_type2,monomial_spin_key,MatrixRepresentation,
    solve_obstructed_1_cocycle,rotation_2d,embed_o2,trim_vectors)
from ssg_enumeration.validation import zero_matrix


class IndependentEnumerationTests(unittest.TestCase):
    def test_type2_direct_octahedral_search(self):
        octahedral = next(m for name,t,m in rotation_group_catalog() if name == 'O')
        # Directly test all commuting pairs of independent pi rotations assigned
        # to lattice translations, then search the full normalizer for s(p).
        klein = (M.eye(3),M.diag(1,-1,-1),M.diag(-1,1,-1),M.diag(-1,-1,1))
        for name in ('P2','P21','Pc'):
            g = example_space_group(name)
            expected = set()
            for images in product(klein,repeat=3):
                generated = {M.eye(3)}
                for a in images:
                    generated |= {x*a for x in tuple(generated)}
                if len(generated) != 4: continue
                for section in octahedral:
                    rep = MatrixRepresentation(images,(M.eye(3),section),'type2','V4')
                    if section*section != rep.translation(g.cocycle[1][1]): continue
                    if any(section*images[j]*section.T != rep.translation(g.rotations[1][:,j]) for j in range(3)): continue
                    expected.add(monomial_spin_key(rep))
            actual = {monomial_spin_key(r) for r in enumerate_noncoplanar_type2(g)}
            self.assertEqual(actual,expected,name)

    def test_type1_fixed_k_against_matrix_search(self):
        for name in ('P2','P21','Pc'):
            g = example_space_group(name)
            for k in trim_vectors():
                for sign in (1,-1):
                    expected = set()
                    # eta=-1 admits a continuous conjugation fixing theta_s=0.
                    angles = (Q(0),) if sign == -1 else tuple(Q(i,4) for i in range(4))
                    for theta in angles:
                        section = embed_o2(rotation_2d(theta)*M.diag(1,sign))
                        def translation(t): return embed_o2(rotation_2d(k.dot(t)))
                        if not zero_matrix(section*section-translation(g.cocycle[1][1])): continue
                        if any(not zero_matrix(section*translation(M.eye(3)[:,j])*section.T-
                                               translation(g.rotations[1][:,j])) for j in range(3)): continue
                        expected.add(theta)
                    actual = {t.offset[1] for t in solve_obstructed_1_cocycle(g,(1,sign),k)}
                    self.assertEqual(actual,expected,(name,k,sign))


if __name__ == '__main__': unittest.main()
