import unittest
from itertools import product
from random import Random
from sympy import ImmutableMatrix as M, Rational as Q
from ssg_enumeration.gf2 import solve_gf2
from ssg_enumeration.torus import solve_torus, smith_decomposition, AffineTorus, parameter_relation


class AlgebraTests(unittest.TestCase):
    def test_binary_against_exhaustive(self):
        rng = Random(431)
        for n in range(1, 6):
            for _ in range(25):
                a = [[rng.randrange(2) for _ in range(n)] for _ in range(6)]
                b = [rng.randrange(2) for _ in a]
                expected = {v for v in product((0, 1), repeat=n)
                            if all(sum(x*y for x, y in zip(r, v)) % 2 == z for r, z in zip(a,b))}
                got = solve_gf2(a,b)
                self.assertEqual(set(got) if got else set(), expected)

    def test_smith_certificates(self):
        rng = Random(12)
        for m, n in ((3,4), (5,2), (3,3), (0,3), (3,0)):
            for _ in range(10):
                a = M(m,n,[rng.randrange(-5,6) for _ in range(m*n)])
                d,u,v = smith_decomposition(a)
                self.assertEqual(u*a*v,d)
                self.assertEqual(abs(v.det()),1)

    def test_obstruction_and_torsion(self):
        self.assertEqual(solve_torus(M([[0]]),M([Q(1,2)])), ())
        ts = solve_torus(M([[2,0],[0,3]]))
        self.assertEqual(len(ts),6)
        self.assertTrue(all(t.dimension == 0 for t in ts))
        self.assertTrue(all(t.contains(t.offset) for t in ts))

    def test_row_lattice_not_rational_rowspace(self):
        self.assertEqual(len(solve_torus(M([[2],[4]]))),2)
        self.assertEqual(len(solve_torus(M([[2],[3]]))),1)
        self.assertEqual(len(solve_torus(M([[2],[4]]),M([Q(1,2),0]))),2)

    def test_continuous_and_reparametrization(self):
        a = AffineTorus(M([0,0]),M([[1],[2]]))
        b = AffineTorus(M([Q(1,2),0]),M([[-2],[-4]]))
        self.assertEqual(a.key,b.key)
        self.assertEqual(a.dimension,1)
        self.assertEqual(len(a.intersect(M([[2,0]]),M([0]))),2)
        self.assertTrue(parameter_relation(a,a,-M.eye(2)).holds([Q(1,3)],[Q(2,3)]))


if __name__ == '__main__':
    unittest.main()
