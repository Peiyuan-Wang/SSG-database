import unittest
from itertools import permutations,product
from sympy import ImmutableMatrix as M
from ssg_enumeration.groups import example_space_group
from ssg_enumeration.type2 import enumerate_noncoplanar_type2,annihilator_trims,invariant_kernel_vectors
from ssg_enumeration.exact import oriented_permutation
from ssg_enumeration.validation import validate_representation,spin_equivalent_matrices


class Type2Tests(unittest.TestCase):
    def test_p1_seven_kernels(self):
        g = example_space_group('P1')
        self.assertEqual(len(enumerate_noncoplanar_type2(g)),7)
        for t in invariant_kernel_vectors(g):
            self.assertEqual(len(annihilator_trims(t)),3)

    def test_oriented_lift_is_homomorphism(self):
        for a,b in product(permutations(range(3)),repeat=2):
            self.assertEqual(oriented_permutation(a)*oriented_permutation(b),oriented_permutation(tuple(a[b[i]] for i in range(3))))
            self.assertEqual(oriented_permutation(a).det(),1)

    def test_all_defining_relations(self):
        for name in ('P1','P21','Pc','P3','P4','P23','P212121'):
            g = example_space_group(name)
            for rep in enumerate_noncoplanar_type2(g):
                self.assertTrue(validate_representation(g,rep),name)

    def test_global_conjugation(self):
        r = enumerate_noncoplanar_type2(example_space_group('P1'))[0]
        q = M([[0,0,1],[1,0,0],[0,1,0]])
        matrices = r.translations+r.sections
        self.assertTrue(spin_equivalent_matrices(matrices,tuple(q*m*q.T for m in matrices)))


if __name__ == '__main__': unittest.main()
