import unittest
from itertools import product
from sympy import simplify, zeros
from ssg_enumeration.groups import example_space_group
from ssg_enumeration.type0 import enumerate_noncoplanar_type0,rotation_group_catalog
from ssg_enumeration.finite import normal_subgroups,find_isomorphism


class Type0Tests(unittest.TestCase):
    def test_known_counts(self):
        for name,count in [('P1',1),('P2',2),('P3',2),('P4',3),('P6',4),('P222',5),('P23',3),('P432',4)]:
            records = enumerate_noncoplanar_type0(example_space_group(name))
            self.assertEqual(len(records),count,name)

    def test_full_multiplication(self):
        for name in ('P222','P6','P23','P432'):
            g = example_space_group(name)
            for r in enumerate_noncoplanar_type0(g):
                for a,b in product(range(g.order),repeat=2):
                    self.assertEqual((r.sections[a]*r.sections[b]-r.sections[g.table[a][b]]).applyfunc(simplify),zeros(3))

    def test_catalog(self):
        for name,table,matrices in rotation_group_catalog():
            self.assertTrue(all(m.det().simplify() == 1 for m in matrices),name)
            self.assertIsNotNone(find_isomorphism(table,table),name)

    def test_small_bruteforce_kernels(self):
        # Every map C2xC2 -> D2 is a pair of commuting involutions.
        g = example_space_group('P222')
        table = next(t for name,t,m in rotation_group_catalog() if name == 'D2')
        kernels = set()
        for a,b in product(range(4),repeat=2):
            images = (0,a,b,table[a][b])
            kernels.add(tuple(i for i,v in enumerate(images) if v == 0))
        self.assertEqual(kernels,{r.kernel for r in enumerate_noncoplanar_type0(g)})


if __name__ == '__main__': unittest.main()
