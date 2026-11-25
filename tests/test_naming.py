"""Exact naming boundaries: phases, coverings, centred cells and O(2) lifts."""
import unittest
from sympy import ImmutableMatrix as M, Rational as Q
from ssg_enumeration import (AffineTorus, canonical_torus, parse_label,
    name_for_label, to_xiao_label, from_xiao_label, naming_setting,
    label_for_record, name_for_chart, xiao_label_for_record)
from ssg_enumeration.representations import embed_o2, rotation_2d


class NamingAlgebraTests(unittest.TestCase):
    def test_improper_spin_rotation_is_typeset_with_overbar(self):
        from ssg_enumeration.naming import _spin_latex
        self.assertEqual(_spin_latex(M([[0,1,0],[-1,0,0],[0,0,-1]])),r'\overline{4}_{z}')

    def test_lexicographic_offset_keeps_disconnected_restrictions(self):
        t = AffineTorus(M([Q(1,2),0]),M([2,3]))
        canonical = canonical_torus(t)
        self.assertEqual(canonical.offset,M([0,Q(1,4)]))
        other = AffineTorus(t.offset+t.basis*Q(1,7),-t.basis)
        self.assertEqual(canonical_torus(other),canonical)

    def test_screw_cover_and_exact_recovery(self):
        name = parse_label('N: ^{(0,2*u0,0)}P 2_1 | u0 in R/Z; 2*C^T*k notin Z^3')
        for u in (Q(1,6),Q(2,3)):
            screw = name.evaluate(point=1,parameters=[u])
            self.assertEqual(screw,embed_o2(rotation_2d(u)))
            self.assertEqual(screw**2,name.evaluate((0,1,0),parameters=[u]))
        self.assertNotEqual(name.evaluate(point=1,parameters=[Q(1,6)]),name.evaluate(point=1,parameters=[Q(2,3)]))
        for u in (0,Q(1,4),Q(1,2)):
            with self.assertRaises(ValueError): name.evaluate(parameters=[u])

    def test_reciprocal_shift_requires_spin_change(self):
        a = parse_label('N: ^{(0,4/3,0)}P 2_1')
        b = parse_label('N: ^{(0,1/3,0)}P ^{2_z}2_1')
        for p in range(2): self.assertEqual(a.evaluate(point=p),b.evaluate(point=p))
        c = parse_label('N: ^{(0,1/3,0)}P 2_1')
        self.assertNotEqual(a.evaluate(point=1),c.evaluate(point=1))

    def test_composite_hm_keeps_both_operations(self):
        name = parse_label('L: P 2/^{-1}m')
        self.assertEqual(len(name.spins),2)
        self.assertEqual(name.spins,(M.eye(3),-M.eye(3)))
        self.assertEqual(name.to_record().category,'L.0.1')

    def test_coplanar_proper_lift_and_native_plane(self):
        name = parse_label('P: ^{<2_x,1,1>}P 1')
        self.assertEqual(name.evaluate((1,0,0)),M.diag(1,-1,-1))
        self.assertEqual(name.evaluate((1,0,0),embedded=False),M.diag(1,-1))
        self.assertEqual(name.to_record().category,'P.2.1')
        with self.assertRaises(ValueError): parse_label('P: P ^{m_z}1')

    def test_centered_grading_not_reduced_componentwise(self):
        name = parse_label('L: I_{(0,0,1)} 2 2 2')
        self.assertEqual(name.grading_q,M([0,0,Q(1,2)]))
        self.assertEqual(name.evaluate((0,0,1)),-M.eye(3))
        screw = parse_label('L: I_{(0,0,1)} ^{-1}2_1 ^{-1}2_1 2_1')
        self.assertEqual(name_for_chart(24,screw.to_record()).text,screw.text)
        self.assertEqual(screw.evaluate((0,0,-1)), -M.eye(3))

    def test_all_hm_generators_include_complete_lifts(self):
        for number in range(1,231):
            setting = naming_setting(number)
            self.assertEqual(setting['number'],number)
            self.assertTrue(all('shift' in a and 'translation' in a for a in setting['atoms']))
        self.assertEqual(naming_setting(4)['hall_number'],6)
        self.assertEqual(naming_setting(75)['hall_number'],349)

    def test_bad_group_relations_and_unsafe_expressions_rejected(self):
        with self.assertRaises(ValueError):
            parse_label('N: ^{(0,0,4*u0)}P ^{3_z}4_1 | u0 in R/Z; 2*C^T*k notin Z^3')
        with self.assertRaises(ValueError): parse_label("N: ^{(__import__('os'),0,0)}P 1")
        with self.assertRaises(ValueError): parse_label('L: P_{(0,0,1/3)} 1')


class NamingCatalogueTests(unittest.TestCase):
    def test_space_inversion_uses_overbar_not_minus(self):
        from ssg_enumeration import name_for_label
        name=name_for_label('N2.9.7')
        self.assertIn(r'\bar{1}',name.liu_latex)
        self.assertNotIn('-1',name.liu_latex)

    def test_xiao_and_old_identifier_remain_available(self):
        name = name_for_label('N143.5.2')
        self.assertEqual(to_xiao_label(name.text),'N143.5.2')
        self.assertEqual(from_xiao_label('N143.5.2',formal=True),name.text)
        self.assertEqual(from_xiao_label('N143.5.2'),'SG143/N.1.2/0002')
        self.assertFalse(name.liu_latex.startswith(r'\mathrm{N}:'))
        self.assertIn(r'{}^{\infty m}\!1',name_for_label('L1.1.1').liu_latex)
        self.assertIn(r'{}^{m}\!1',name_for_label('P1.1.1').liu_latex)

    def test_name_to_record_to_name(self):
        for identifier in ('N143.5.2','SG001/P.2.1/0001','SG004/N.1.2/0001','SG047/N.0.1/0001','SG143/P.0/0002'):
            name=name_for_label(identifier)
            record=parse_label(name.text).to_record()
            self.assertEqual(label_for_record(name.space_group,record),name.text)
            self.assertEqual(record.name(name.space_group).text,name.text)
            self.assertEqual(xiao_label_for_record(name.space_group,record),to_xiao_label(name.text))

    def test_named_catalogue_export(self):
        from ssg_enumeration import load_standard_space_group, enumerate_ssg, catalog_dict
        group,_=load_standard_space_group(1)
        result=enumerate_ssg(group,automorphisms='full')
        data=catalog_dict(result,space_group=1)
        self.assertTrue(all(row['formal_label'].startswith(('L: ','P: ','N: ')) for row in data['charts']))
        self.assertTrue(all(row['category']==row['label'] for row in data['charts']))
        self.assertEqual({row['xiao_label'] for row in data['charts']},
                         {to_xiao_label(record.name(1).text) for record in result})


if __name__ == '__main__': unittest.main()
