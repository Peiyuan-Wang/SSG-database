import unittest
from sympy import ImmutableMatrix as M, Rational as Q
from ssg_enumeration.groups import example_space_group
from ssg_enumeration.automorphisms import (affine_automorphism,p1_outer_generators,
    transform_representation,transform_grading,SpaceGroupAutomorphism)
from ssg_enumeration.type1 import enumerate_noncoplanar_type1
from ssg_enumeration.type2 import enumerate_noncoplanar_type2
from ssg_enumeration.gradings import enumerate_gradings
from ssg_enumeration.validation import validate_representation


class AutomorphismTests(unittest.TestCase):
    def test_p1_complete_generators(self):
        g = example_space_group('P1')
        for a in p1_outer_generators(g):
            a.validate(g)
            a.inverse().validate(g)
            self.assertEqual(a.compose(a.inverse()).linear,M.eye(3))
            for rep in enumerate_noncoplanar_type1(g)+enumerate_noncoplanar_type2(g):
                self.assertTrue(validate_representation(g,transform_representation(rep,a)))

    def test_origin_shift_phase_and_grading(self):
        g = example_space_group('P-1')
        a = affine_automorphism(g,M.eye(3),[Q(1,2),0,0])
        self.assertEqual(a.shifts[1],M([1,0,0]))
        for chi in enumerate_gradings(g):
            changed = transform_grading(chi,a)
            self.assertEqual(changed.signs[1],chi.evaluate([1,0,0],1))
        for rep in enumerate_noncoplanar_type1(g):
            self.assertTrue(validate_representation(g,transform_representation(rep,a)))

    def test_reject_chirality_and_invalid_extension(self):
        g = example_space_group('P21')
        with self.assertRaises(ValueError): affine_automorphism(g,-M.eye(3))
        with self.assertRaises(ValueError):
            SpaceGroupAutomorphism(M.eye(3),(0,1),(M.zeros(3,1),M([0,1,0]))).validate(g)


if __name__ == '__main__': unittest.main()
