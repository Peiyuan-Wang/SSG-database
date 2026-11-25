"""Check the representation dictionary in XIAO_CONTINUOUS_EQUIVALENCE_PROOF_ZH.

The expected paper blocks are built from their translation characters and
section phases, independently of SSG.evaluate's determinant-twist assembly.
"""
import unittest

from sympy import ImmutableMatrix as M, Rational as Q, trigsimp

from ssg_enumeration import example_space_group
from ssg_enumeration.exact import is_integral, mod_vector
from ssg_enumeration.gradings import enumerate_gradings
from ssg_enumeration.records import combine
from ssg_enumeration.representations import rotation_2d
from ssg_enumeration.type1 import enumerate_noncoplanar_type1


class PaperDictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.group = example_space_group('P-1')
        cls.record = next(r for r in enumerate_noncoplanar_type1(cls.group)
                          if r.parameter_count == 3 and -1 in r.eta)
        cls.parameters = tuple(Q(j + 1, 7) for j in range(3))
        cls.q, cls.theta = cls.record.point(cls.parameters)

    def test_all_determinant_twists_recover_the_paper_blocks(self):
        r, g = self.record, self.group
        for chi in enumerate_gradings(g):
            kappa = mod_vector(self.q + chi.k)
            phi = mod_vector(self.theta + M([Q(b, 2) for b in chi.bits]))
            full = combine(r, chi)
            for n in ([0, 0, 0], [1, 0, 0], [0, 1, 0], [1, -1, 1]):
                for p in range(g.order):
                    beta = rotation_2d(kappa.dot(M(n)) + phi[p]) * M.diag(1, r.eta[p])
                    nu = chi.evaluate(n, p) * r.eta[p]
                    expected = M.diag(beta, nu)
                    residual = (full.evaluate(n, p, self.parameters) - expected).applyfunc(trigsimp)
                    self.assertEqual(residual, M.zeros(3))
                    self.assertEqual(trigsimp(beta.det() * nu), chi.evaluate(n, p))
            self.assertEqual(mod_vector(kappa - chi.k), self.q)
            self.assertEqual(mod_vector(phi - M([Q(b, 2) for b in chi.bits])), self.theta)

    def test_shifted_phases_are_allowed_little_group_characters(self):
        # A screw group exercises the nonzero extension cocycle, which would
        # be lost by identifying only wavevectors or only point-group phases.
        g = example_space_group('P21')
        r = next(r for r in enumerate_noncoplanar_type1(g)
                 if r.parameter_count == 1 and all(e == 1 for e in r.eta))
        q, theta = r.point([Q(1, 7)])
        for chi in enumerate_gradings(g):
            kappa = mod_vector(q + chi.k)
            phi = mod_vector(theta + M([Q(b, 2) for b in chi.bits]))
            for a in range(g.order):
                for b in range(g.order):
                    character_residual = (phi[a] + phi[b] - phi[g.table[a][b]]
                                          - kappa.dot(g.cocycle[a][b]))
                    self.assertTrue(is_integral(M([character_residual])))


if __name__ == '__main__':
    unittest.main()
