import unittest
from sympy import ImmutableMatrix as M, Rational as Q
from ssg_enumeration.groups import example_space_group
from ssg_enumeration.type1 import (enumerate_noncoplanar_type1, solve_h1_eta,
    solve_obstructed_1_cocycle, solve_covariant_wavevectors, joint_type1_system)
from ssg_enumeration.exact import is_integral


class Type1Tests(unittest.TestCase):
    def test_p1_continuum_and_boundaries(self):
        records = enumerate_noncoplanar_type1(example_space_group('P1'))
        self.assertEqual(len(records),8)
        f = next(r for r in records if r.dimension)
        self.assertEqual(f.dimension,3)
        self.assertEqual(sum(r.stratum == 'trim' for r in records),7)
        self.assertIsNotNone(f.inversion_relation())
        with self.assertRaises(ValueError): f.point([0,0,0])
        self.assertTrue(f.same_point([Q(1,7),Q(2,9),Q(1,5)],f,[Q(6,7),Q(7,9),Q(4,5)]))
        self.assertFalse(f.same_point([Q(1,7),Q(2,9),Q(1,5)],f,[Q(1,8),Q(2,9),Q(1,5)]))

    def test_h1_removes_gauge(self):
        g = example_space_group('P2')
        self.assertEqual(len(solve_h1_eta(g,(1,1))),2)
        h = solve_h1_eta(g,(1,-1))
        self.assertEqual(len(h),1)
        self.assertEqual(h[0].dimension,0)

    def test_nonsymmorphic_obstruction(self):
        g = example_space_group('P21')
        self.assertEqual(solve_obstructed_1_cocycle(g,(1,-1),M([0,Q(1,2),0])),())
        phases = solve_obstructed_1_cocycle(g,(1,1),M([0,Q(1,2),0]))
        self.assertEqual({t.offset[1] for t in phases},{Q(1,4),Q(3,4)})

    def test_screw_monodromy(self):
        rs = enumerate_noncoplanar_type1(example_space_group('P21'))
        f = next(r for r in rs if r.eta == (1,1) and r.dimension and not r.torus.offset[0] and not r.torus.offset[2])
        # A connected torus covers the k_y circle twice; it is not two disjoint families.
        self.assertEqual(abs(f.torus.basis[1,0]),2)
        self.assertEqual(abs(f.torus.basis[4,0]),1)

    def test_wavevector_to_parameters_preserves_sheets(self):
        rs = enumerate_noncoplanar_type1(example_space_group('P21'))
        f = next(r for r in rs if r.eta == (1,1) and r.dimension and not r.torus.offset[0] and not r.torus.offset[2])
        parameters = f.parameters_at_wavevector([0,Q(1,3),0])
        self.assertEqual(len(parameters),2)
        self.assertEqual({f.point(u)[1][1] for u in parameters},{Q(1,6),Q(2,3)})
        self.assertTrue(all(f.point(u)[0] == M([0,Q(1,3),0]) for u in parameters))

    def test_symbolic_all_relations(self):
        for name in ('P1','P-1','P21','Pc','P41','P31','P212121'):
            g = example_space_group(name)
            for r in enumerate_noncoplanar_type1(g):
                a = joint_type1_system(g,r.eta)
                self.assertTrue(is_integral(a*r.torus.offset),name)
                self.assertEqual(a*r.torus.basis,M.zeros(a.rows,r.parameter_count),name)

    def test_nonorthogonal_reciprocal_basis(self):
        g = example_space_group('P3')
        ts = solve_covariant_wavevectors(g,(1,1,1))
        self.assertTrue(all(all(is_integral(r.T*t.offset-t.offset) for r in g.rotations) for t in ts))


if __name__ == '__main__': unittest.main()
