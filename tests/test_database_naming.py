"""Formula repair when importing earlier catalogues."""
import unittest

from ssg_enumeration import name_for_label


class DatabaseNamingTests(unittest.TestCase):
    def test_database_migration_does_not_rewrite_negative_wavevectors(self):
        from scripts.rebuild_spin_overbars import correct
        before=r'{}^{(-3/2,0,0)}P\,{}^{-4_{x}}m'
        self.assertEqual(correct(before),r'{}^{(-3/2,0,0)}P\,{}^{\overline{4}_{x}}m')

    def test_database_migration_corrects_space_symbols_only(self):
        from scripts.rebuild_spin_overbars import correct
        before=r'{}^{(-1/2,0,0)}P\,{}^{2_{[-1,0,0]}}-1\,-4'
        self.assertEqual(correct(before),r'{}^{(-1/2,0,0)}P\,{}^{2_{[-1,0,0]}}\overline{1}\,\overline{4}')

    def test_database_builder_corrects_old_catalogue_inversion(self):
        from ssg_database.retrieval import _liu_latex
        name=name_for_label('N2.9.7')
        old_latex=name.latex.replace(r'\bar{1}','-1')
        displayed=_liu_latex({'name':name.to_dict(),'latex':old_latex})
        self.assertIn(r'\bar{1}',displayed)
        self.assertNotIn('-1',displayed)

    def test_database_builder_corrects_improper_spin_superscript(self):
        from ssg_database.retrieval import _liu_latex
        name=name_for_label('N9.13.2')
        old_latex=name.latex.replace(r'\bar{4}_{x}',r'-4_{x}')
        displayed=_liu_latex({'name':name.to_dict(),'latex':old_latex})
        self.assertIn(r'\overline{4}_{x}',displayed)
        self.assertNotIn(r'^{-4_',displayed)

