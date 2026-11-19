import unittest
from sympy import ImmutableMatrix as M,Rational as Q,sqrt
from ssg_enumeration.enumerate import enumerate_ssg
from ssg_enumeration.groups import example_space_group
from ssg_enumeration.automorphisms import p1_outer_generators,transform_ssg,affine_automorphism
from ssg_enumeration.deduplication import (spin_key,equivalence_loci,stabilizer_loci,
    rational_p1_wavevector_orbit_key,deduplicate_automorphisms,verify_equivalence_witness)


class DeduplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = example_space_group('P1')
        cls.spin = enumerate_ssg(cls.g)
        cls.full = enumerate_ssg(cls.g,'p1_full')

    def test_p1_full_outer_counts(self):
        self.assertEqual(len(self.spin),173)
        self.assertEqual(len(self.full),17)
        self.assertEqual(len(set(s.label for s in self.full)),17)
        self.assertEqual(self.full.spatial_scope,'full_out_plus_P1')
        self.assertEqual(self.spin.spatial_scope,'spin_only')

    def test_action_closure(self):
        for s in self.full.charts:
            for a in p1_outer_generators(self.g):
                self.assertIsNotNone(self.full.locate(transform_ssg(s,a)))

    def test_continuous_points_are_not_family_labels(self):
        i = next(i for i,s in enumerate(self.full.charts) if s.label == 'P.1.2')
        a = self.full.equivalent_points(i,[Q(1,3),0,0],i,[0,Q(1,3),0])
        self.assertEqual(a.status,'equivalent')
        b = self.full.equivalent_points(i,[Q(1,3),0,0],i,[Q(1,4),0,0])
        self.assertEqual(b.status,'distinct')
        self.assertEqual(self.full.equivalent_points(i,[Q(1,31),0,0],i,[Q(1,29),0,0],max_states=2).status,'unknown')

    def test_irrational_evaluation_and_unknown(self):
        i = next(i for i,s in enumerate(self.full.charts) if s.label == 'P.1.2')
        s = self.full.charts[i]
        matrix = s.evaluate([1,0,0],parameters=[sqrt(2),0,0])
        self.assertEqual(matrix.shape,(3,3))
        decision = self.full.equivalent_points(i,[sqrt(2),0,0],i,[sqrt(3),0,0])
        self.assertEqual(decision.status,'unknown')

    def test_special_loci_exact(self):
        s = next(s for s in self.spin if s.label == 'P.1.2')
        loci = stabilizer_loci(s.representation,spin_sign=-1)
        self.assertEqual(len(loci),8) # all TRIM, excluded from this general stratum
        self.assertTrue(all(x.dimension == 0 for x in loci))
        eq = equivalence_loci(s,s)
        self.assertEqual(len(eq),2) # diagonal and inversion graph
        self.assertTrue(all(x.dimension == 3 for x in eq))

    def test_exact_irrational_spatial_witness(self):
        s = self.full.by_label('P.1.2')[0]
        alpha = affine_automorphism(self.g,M([[0,1,0],[0,0,1],[1,0,0]]))
        self.assertTrue(verify_equivalence_witness(self.g,s,[sqrt(2),0,0],s,[0,sqrt(2),0],[alpha]))
        self.assertFalse(verify_equivalence_witness(self.g,s,[sqrt(2),0,0],s,[0,sqrt(3),0],[alpha]))

    def test_no_false_complete_quotient(self):
        s = next(s for s in self.spin if s.label == 'L.0.2')
        with self.assertRaises(ValueError):
            deduplicate_automorphisms((s,),p1_outer_generators(self.g))

    def test_rational_p1_invariant(self):
        self.assertEqual(rational_p1_wavevector_orbit_key([Q(1,6),Q(1,4),0]),12)
        self.assertEqual(rational_p1_wavevector_orbit_key([Q(5,12),0,0]),12)


if __name__ == '__main__': unittest.main()
