import unittest
from itertools import product
from sympy import ImmutableMatrix as M, Rational as Q
from ssg_enumeration.groups import example_space_group, from_generators
from ssg_enumeration.gradings import enumerate_gradings


class GroupGradingTests(unittest.TestCase):
    def test_extension(self):
        for name in ('P1','P-1','P21','Pc','P212121','P31','P41'):
            self.assertTrue(example_space_group(name).validate_cocycle(),name)
        self.assertEqual(example_space_group('P21').cocycle[1][1],M([0,1,0]))

    def test_expected_grading_counts(self):
        for name,count in [('P1',8),('P-1',16),('P2',16),('P21',8),('Pm',16),('Pc',8)]:
            self.assertEqual(len(enumerate_gradings(example_space_group(name))),count,name)

    def test_all_grading_relations(self):
        for name in ('P21','P31','P41','P212121'):
            g = example_space_group(name)
            for chi in enumerate_gradings(g):
                for a,b in product(range(g.order),repeat=2):
                    x,y = (M([1,-1,2]),a),(M([-2,1,3]),b)
                    self.assertEqual(chi.evaluate(*x)*chi.evaluate(*y),chi.evaluate(*g.multiply(x,y)))

    def test_reject_nonprimitive_and_float(self):
        with self.assertRaises(ValueError):
            from_generators([(M.eye(3),[Q(1,2),0,0])])
        with self.assertRaises(ValueError):
            from_generators([(M.diag(-1,1,-1),[0,0.5,0])])


if __name__ == '__main__': unittest.main()
