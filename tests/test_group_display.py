import os
import unittest
from sympy import eye, Matrix
from ssg_database import SearchDatabase
from ssg_database.group_display import point_operation_rows, finite_quotient_rows, translation_generator_rows, matched_quotient_rows
from pathlib import Path

DB=Path(os.environ.get('SSG_TEST_DATABASE',Path(__file__).resolve().parents[1]/'output/retrieval/SSGclassify.sqlite')).resolve()

@unittest.skipUnless(DB.exists(),'Full database is a separate release asset')
class GroupDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.db=SearchDatabase(DB)
    @classmethod
    def tearDownClass(cls):cls.db.close()

    def test_section_operations_are_real_representatives(self):
        d=self.db.detail('N6.9.1');rows=point_operation_rows(d)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['spin'],eye(3))
        self.assertEqual(rows[0]['rotation'],eye(3))
        self.assertEqual(rows[0]['translation'],Matrix([0,0,0]))
        self.assertEqual(rows[1]['spin'],-eye(3))

    def test_continuous_family_retains_symbolic_parameters(self):
        d=self.db.detail('N143.5.2');rows=point_operation_rows(d)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['spin'],eye(3))

    def test_symbolic_sections_remain_equal_to_original_matrices(self):
        from sympy import Rational
        from ssg_enumeration.naming import SSGName
        for label in ('N182.14.2','N143.5.2','N3.11.17'):
            detail=self.db.detail(label);name=SSGName.from_dict(detail['name_data'],validate=False)
            rows=point_operation_rows(detail)
            for value in (Rational(1,7),Rational(2,9)):
                values=(value,)*name.parameter_count
                original=name._sections(values);substitutions=dict(zip(name.parameters,values))
                for row,expected in zip(rows,original):
                    difference=(row['spin'].subs(substitutions)-expected).evalf(30)
                    self.assertTrue(all(abs(complex(x))<1e-20 for x in difference),label)
            self.assertLess(max(len(str(x)) for row in rows for x in row['spin']),120)

    def test_translation_generated_cosets_are_not_lost(self):
        d=self.db.detail('N1.9.4');rows=finite_quotient_rows(d)
        self.assertEqual(len(rows),4)
        self.assertEqual(len({tuple(row['spin']) for row in rows}),4)
        self.assertTrue(any(row['translation']!=Matrix([0,0,0]) for row in rows))

    def test_continuous_quotient_is_not_silently_sampled(self):
        with self.assertRaises(ValueError):finite_quotient_rows(self.db.detail('N143.5.2'))

    def test_continuous_translation_generator_retains_parameter(self):
        rows=translation_generator_rows(self.db.detail('N143.5.2'))
        self.assertEqual(len(rows),3)
        self.assertIn('u0',str(rows[2]['spin']))
        self.assertEqual(rows[2]['translation'],Matrix([0,0,1]))

    def test_all_spatial_sections_remain_when_spin_images_coincide(self):
        d=self.db.detail('L5.1.1');rows=point_operation_rows(d)
        self.assertEqual(len(rows),d['parent_info']['setting']['point_order'])
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['spin'],rows[1]['spin'])
        self.assertNotEqual(rows[0]['rotation'],rows[1]['rotation'])

    def test_specialized_sections_accept_irrational_and_large_denominator(self):
        from sympy import Rational,sqrt
        d=self.db.detail('N143.5.2')
        for value in (Rational(81,100),sqrt(2)/10,Rational(1,997)):
            rows=point_operation_rows(d,parameters=[value],approximate=True)
            translations=translation_generator_rows(d,parameters=[value],approximate=True)
            self.assertEqual(len(rows),3);self.assertEqual(len(translations),3)
            self.assertFalse(any(x.free_symbols for x in translations[2]['spin']))
            self.assertAlmostEqual(float(translations[2]['spin'][0,0]),float(__import__('math').cos(2*__import__('math').pi*float(value))),places=6)

    def test_matched_chart_shows_each_point_section_once(self):
        from ssg_database.group_display import matched_section_rows
        result=self.db.search({'parent':1,'bravais':'aP','category':'P.1.2','k1':'1/7,0,0','k_name':'C7'})
        row=next(r for r in result['rows'] if r['xiao']=='P1.5.1')
        d=self.db.detail(row['id']);sections,translations=matched_section_rows(d,row['matched_specialization'])
        self.assertEqual(len(sections),1);self.assertEqual(len(translations),3)
        self.assertEqual(sections[0]['spin'],eye(3))

    def test_matched_coplanar_chart_sections_match_its_recorded_phases(self):
        from ssg_database.group_display import matched_section_rows
        from ssg_enumeration.naming import _matrix
        from ssg_enumeration.representations import rotation_2d,embed_o2
        from sympy import Rational,zeros,simplify
        result=self.db.search({'parent':27,'bravais':'oP','category':'P.1.2','k1':'0,0,1/3','q_name':'C2'})
        row=next(r for r in result['rows'] if r['xiao']=='P27.5.2')
        detail=self.db.detail(row['id']);match=row['matched_specialization']
        sections,translations=matched_section_rows(detail,match)
        chart=match['chart'];rep=chart['representation'];pars=Matrix([Rational(x) for x in match['parameters']])
        values=_matrix(rep['offset'])+_matrix(rep['basis'])*pars
        grading=chart.get('grading') or {};chi=_matrix(grading['k']) if grading else zeros(3,1)
        bits=grading.get('section_bits',[0]*len(rep['eta']))
        self.assertEqual(len(sections),detail['parent_info']['setting']['point_order'])
        self.assertEqual(len(translations),3)
        for p,row in enumerate(sections):
            expected=(-1)**int(bits[p])*embed_o2(rotation_2d(values[3+p])*Matrix.diag(1,int(rep['eta'][p])))
            self.assertEqual((row['spin']-expected).applyfunc(simplify),Matrix.zeros(3))
        for j,row in enumerate(translations):
            expected=(-1)**int(2*chi[j])*embed_o2(rotation_2d(values[j]))
            self.assertEqual((row['spin']-expected).applyfunc(simplify),Matrix.zeros(3))

    def test_rational_continuous_family_has_exact_finite_cosets(self):
        d=self.db.detail('N143.5.2')
        rows=finite_quotient_rows(d,parameters=['1/7'])
        self.assertEqual(len(rows),21)
        self.assertEqual(rows[0]['spin'],eye(3))
        from ssg_enumeration.naming import SSGName
        from sympy import simplify
        name=SSGName.from_dict(d['name_data'],validate=False)
        row=rows[1]
        self.assertEqual((row['spin']-name.evaluate(tuple(row['primitive_translation']),row['point'],['1/7'])).applyfunc(simplify),Matrix.zeros(3))

    def test_matched_chart_yields_actual_specialized_group(self):
        result=self.db.search({'parent':1,'bravais':'aP','category':'P.1.2','k1':'1/7,0,0','k_name':'C7'})
        row=next(r for r in result['rows'] if r['xiao']=='P1.5.1')
        detail=self.db.detail(row['id']);match=row['matched_specialization']
        operations,translations=matched_quotient_rows(detail,match)
        self.assertEqual(len(operations),7)
        self.assertEqual(len(operations),match['crystal']['k_order'])
        self.assertEqual(len(translations),3)
        # Search parameters belong to the matched orbit chart, which need not
        # share the displayed name's spin frame or its parameterization.
        from sympy import Rational, zeros, simplify
        from sympy.polys.numberfields import to_number_field
        from ssg_enumeration.naming import _matrix
        from ssg_enumeration.representations import rotation_2d, embed_o2
        chart=match['chart']; rep=chart['representation']
        values=_matrix(rep['offset'])+_matrix(rep['basis'])*Matrix([Rational(x) for x in match['parameters']])
        grading=chart.get('grading') or {}
        chi=_matrix(grading['k']) if grading else zeros(3,1)
        bits=grading.get('section_bits',[0]*len(rep['eta']))
        for operation in operations:
            p=operation['point']; t=operation['primitive_translation']
            phase=(sum(values[j]*t[j] for j in range(3))+values[3+p])%1
            bit=(int(2*chi.dot(t))+int(bits[p]))%2
            expected=(-1)**bit*embed_o2(rotation_2d(phase)*Matrix.diag(1,int(rep['eta'][p])))
            for difference in operation['spin']-expected:
                difference=simplify(difference)
                self.assertTrue(difference==0 or to_number_field(difference).is_zero)

if __name__=='__main__':unittest.main()
