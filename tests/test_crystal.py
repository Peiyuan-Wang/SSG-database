import unittest
from sympy import ImmutableMatrix as M, Rational as R
from ssg_enumeration.crystal import finite_crystal, affine_crystal, specialize_affine
from ssg_enumeration.type0 import _cyclic_dihedral


class CrystalTests(unittest.TestCase):
    def test_collinear_antitranslation_has_trivial_quotient(self):
        result = finite_crystal((M([[-1]]), M([[1]]), M([[1]])),
                                (M([[1]]), M([[-1]])), ((0, 1), (1, 0)))
        self.assertEqual((result['h_order'], result['k_order'], result['q_order']), (2, 2, 1))
        self.assertEqual(result['kernel'], [0, 1])

    def test_same_abstract_c2_has_distinct_embedded_extensions(self):
        h = (M.diag(1,-1,-1), M.diag(-1,1,-1), M.eye(3))
        r4 = _cyclic_dihedral(4)[1][1]
        a = finite_crystal(h, (M.eye(3),r4), ((0,1),(1,0)))
        b = finite_crystal(h, (M.eye(3),-M.eye(3)), ((0,1),(1,0)))
        c = finite_crystal(h, (M.eye(3),-r4), ((0,1),(1,0)))
        self.assertEqual([x['q_name'] for x in (a,b,c)], ['C2']*3)
        self.assertEqual([x['k_name'] for x in (a,b,c)], ['D4','D2h','D2d'])
        self.assertEqual(len({x['pair_fingerprint'] for x in (a,b,c)}), 3)

    def test_pcc2_generic_rotational_quotient_is_v4(self):
        # q_c=u, theta_x=u/2, theta_y=u/2+1/2, theta_xy=u+1/2.
        translations = (((0,0),0), ((0,0),0), ((0,1),0))
        sections = (((0,0),1,0), ((0,R(1,2)),1,0),
                    ((R(1,2),R(1,2)),1,0), ((R(1,2),1),1,0))
        table = tuple(tuple(a^b for b in range(4)) for a in range(4))
        r = affine_crystal(translations, sections, table, dimension=2)
        self.assertEqual(r['kernel'], [0])
        self.assertEqual(r['q_name'], 'C2 × C2')
        self.assertEqual(r['q_order'], 4)
        # At u=1/3, the translation image is C3, full image C6, quotient C2.
        s = specialize_affine(translations, sections, table, (R(1,3),), dimension=2)
        self.assertEqual((s['h_order'],s['k_order'],s['q_order']), (3,6,2))
        self.assertEqual(s['kernel'], [0,2])

    def test_p21_screw_generic_kernel_is_trivial(self):
        r = affine_crystal((((0,0),0),((0,2),0),((0,0),0)),
                           (((0,0),1,0),((0,1),1,0)), ((0,1),(1,0)), dimension=3)
        self.assertEqual(r['kernel'], [0])
        self.assertEqual(r['q_order'], 2)

    def test_nonhomomorphic_sections_are_rejected(self):
        r3 = _cyclic_dihedral(3)[1][1]
        with self.assertRaises(ValueError):
            finite_crystal((M.eye(3),)*3, (M.eye(3),r3), ((0,1),(1,0)))

    def test_seventh_order_spiral_uses_exact_phase_arithmetic(self):
        # A screw has H=C7 and K=C14 when u=1/14 and q_y=2u.
        result=specialize_affine((((0,0),0),((0,2),0),((0,0),0)),
                                 (((0,0),1,0),((0,1),1,0)),
                                 ((0,1),(1,0)),(R(1,14),),dimension=3)
        self.assertEqual((result['h_order'],result['k_order'],result['q_order']),(7,14,2))
        self.assertEqual(result['k_name'],'C14')


if __name__ == '__main__':
    unittest.main()
