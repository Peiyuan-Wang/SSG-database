import shutil
import tempfile
import unittest
from pathlib import Path
from ssg_database.label_svg import compile_formulas


@unittest.skipUnless(shutil.which('latex') and shutil.which('dvisvgm'),'TeX build tools are optional')
class FormulaTests(unittest.TestCase):
    def test_compiled_formula_is_vector_and_preserves_fraction_and_subscripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            formulas=[r'{}^{(0,\frac{1}{2},u_0)}P_{(0,0,\frac{1}{2})}\,{}^{2_x}2_1',
                      r'P\,1\,{}^{\infty m}\!1']
            vectors=compile_formulas(formulas+[r'P\,1']*15,Path(tmp))
            self.assertEqual(len(vectors),17)
            for svg in vectors:
                self.assertIn(b'<path',svg)
                self.assertIn(b'viewBox=',svg)
                self.assertNotIn(b'<image',svg)
                self.assertNotIn(b'data:image',svg)


if __name__=='__main__':unittest.main()
