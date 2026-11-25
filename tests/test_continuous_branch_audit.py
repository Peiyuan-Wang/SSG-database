"""Targeted evidence for P41 punctures and the screw phase cover."""
import unittest
from audits.continuous_branches.check_p41 import audit


class ContinuousBranchAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=audit()

    def test_full_representation_and_point_equivalence(self):
        self.assertEqual(self.data['samples'][0]['k'],self.data['samples'][1]['k'])
        self.assertNotEqual(self.data['samples'][0]['theta'],self.data['samples'][1]['theta'])
        self.assertEqual(self.data['point_equivalence']['status'],'distinct')

    def test_component_orbits_under_spin_and_spatial_actions(self):
        self.assertEqual(set(self.data['relation_signs']),{-1,1})
        self.assertEqual(len(self.data['nonzero_k']['component_orbits_under_sign']),2)
        self.assertEqual(len(self.data['general_chart']['component_orbits_under_sign']),4)
        self.assertEqual(self.data['general_chart']['current_family_count'],1)

    def test_p21_cover_retains_phase_sheet(self):
        self.assertEqual(self.data['p21_unpunctured_cover_degree'],2)

if __name__=='__main__':
    unittest.main()
