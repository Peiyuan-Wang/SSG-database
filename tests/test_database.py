import unittest
import importlib.util
from collections import Counter
from ssg_enumeration import (standard_hall_numbers,load_standard_space_group,
    example_space_group,enumerate_ssg)


@unittest.skipUnless(importlib.util.find_spec('spglib'), 'Optional spglib input dependency missing')
class DatabaseTests(unittest.TestCase):
    def test_230_primitive_extensions(self):
        self.assertEqual(set(standard_hall_numbers()),set(range(1,231)))
        indices = set()
        for number in range(1,231):
            group,meta = load_standard_space_group(number)
            self.assertEqual(meta['conventional_operation_count'],meta['centering_index']*group.order)
            self.assertIn(group.order,(1,2,3,4,6,8,12,16,24,48))
            indices.add(meta['centering_index'])
        self.assertEqual(indices,{1,2,3,4})

    def test_reference_examples(self):
        for number,name in ((1,'P1'),(2,'P-1'),(3,'P2'),(4,'P21'),(6,'Pm'),(7,'Pc'),(16,'P222'),(19,'P212121'),(75,'P4'),(76,'P41'),(143,'P3'),(144,'P31')):
            group,_ = load_standard_space_group(number)
            actual = enumerate_ssg(group).summary()
            expected = enumerate_ssg(example_space_group(name)).summary()
            self.assertEqual(actual['labels'],expected['labels'],(number,name))
            self.assertEqual(actual['continuous_chart_orbits'],expected['continuous_chart_orbits'])

    def test_bad_setting(self):
        with self.assertRaises(ValueError): load_standard_space_group(1,hall_number=530)
        with self.assertRaises(ValueError): load_standard_space_group(231)


if __name__ == '__main__': unittest.main()
