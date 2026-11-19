import unittest
from collections import Counter
from ssg_enumeration.groups import example_space_group
from ssg_enumeration.coplanar import enumerate_coplanar_type0,enumerate_coplanar_type1,enumerate_coplanar_type2
from ssg_enumeration.validation import validate_representation
from ssg_enumeration.gradings import enumerate_gradings
from ssg_enumeration.type0 import enumerate_noncoplanar_type0
from ssg_enumeration.type1 import enumerate_noncoplanar_type1
from ssg_enumeration.type2 import enumerate_noncoplanar_type2
from ssg_enumeration.records import SSG,combine,build_collinear_ssgs
from ssg_enumeration.labels import LABELS


class CoplanarTests(unittest.TestCase):
    def test_p1_21_v4_and_7_d1(self):
        g = example_space_group('P1')
        rs = enumerate_coplanar_type2(g)
        self.assertEqual(Counter(r.image for r in rs),{'V4':21,'D1':7})
        self.assertEqual(len(enumerate_coplanar_type0(g)),1)
        self.assertEqual(len(enumerate_coplanar_type1(g)),8)

    def test_all_relations(self):
        for name in ('P1','P21','P3','P4','Pc','P222','P212121'):
            g = example_space_group(name)
            for r in enumerate_coplanar_type0(g)+enumerate_coplanar_type1(g)+enumerate_coplanar_type2(g):
                self.assertTrue(validate_representation(g,r),name)

    def test_all_seventeen_labels(self):
        g = example_space_group('P1')
        gradings = enumerate_gradings(g)
        records = list(build_collinear_ssgs(gradings))
        for r in enumerate_noncoplanar_type0(g)+enumerate_noncoplanar_type1(g)+enumerate_noncoplanar_type2(g):
            records.extend(combine(r,chi) for chi in gradings)
        records.extend(SSG('Coplanar',r) for r in enumerate_coplanar_type0(g)+enumerate_coplanar_type1(g)+enumerate_coplanar_type2(g))
        self.assertEqual(set(r.label for r in records),set(LABELS))


if __name__ == '__main__': unittest.main()
