"""Public full-ID lookup, full bijection and live standard-representative lookup."""
from collections import Counter
import unittest

from ssg_enumeration import (to_xiao_label, from_xiao_label, xiao_correspondences,
    xiao_mapping_metadata, xiao_label_for_record, enumerate_ssg, load_standard_space_group)


class XiaoMappingTests(unittest.TestCase):
    def test_complete_bijection_roundtrip(self):
        rows = xiao_correspondences()
        self.assertEqual(len(rows), 67475)
        self.assertEqual(len({r.our_label for r in rows}), 67475)
        self.assertEqual(len({r.xiao_label for r in rows}), 67475)
        self.assertEqual(Counter(r.xiao_label[0] for r in rows), {'L':1421,'P':9542,'N':56512})
        for row in rows:
            self.assertEqual(to_xiao_label(row.our_label), row.xiao_label)
            self.assertEqual(from_xiao_label(row.xiao_label), row.our_label)

    def test_published_full_serial_not_category_only(self):
        expected = ['N143.5.1', 'N143.5.2', 'N143.5.3']
        rows = xiao_correspondences(space_group=143, category='N.1.2')
        self.assertEqual([r.xiao_label for r in rows], expected)
        self.assertEqual(to_xiao_label('N.1.2',space_group=143,class_index=2),'N143.5.2')
        self.assertEqual(from_xiao_label('N143.5.2'),'SG143/N.1.2/0002')

    def test_ambiguous_and_invalid_inputs(self):
        for label in ('N.1.2', 'P.0'):
            with self.assertRaises(ValueError): to_xiao_label(label)
        for number in (0, 231, True, '143'):
            with self.assertRaises(ValueError): xiao_correspondences(space_group=number)
        with self.assertRaises(KeyError): to_xiao_label('SG143/N.1.2/9999')
        with self.assertRaises(KeyError): from_xiao_label('N143.5.999')
        with self.assertRaises(ValueError): to_xiao_label('N.1.2',space_group=143,class_index=0)

    def test_metadata_is_independent_and_complete(self):
        meta = xiao_mapping_metadata()
        self.assertEqual(meta['second_parameter_checked'],8520)
        self.assertEqual(len(meta['parents']),230)
        self.assertTrue(meta['paper_id_set_verified'])
        meta['parents'].clear()
        self.assertEqual(len(xiao_mapping_metadata()['parents']),230)

    def test_live_enumeration_representatives(self):
        group, _ = load_standard_space_group(143)
        result = enumerate_ssg(group, automorphisms='full')
        rows = xiao_correspondences(space_group=143)
        self.assertEqual(len(result.records),len(rows))
        for record, row in zip(result.records,rows):
            self.assertEqual(xiao_label_for_record(143,record),row.xiao_label)


if __name__ == '__main__':
    unittest.main()
