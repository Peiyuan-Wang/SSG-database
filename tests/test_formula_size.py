"""Equal TeX glyphs must retain their size when a formula's bounding box changes."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest

try:
    from ssg_database.desktop import (QApplication, FormulaView, FormulaDelegate,
        QTableWidget, QTableWidgetItem, QStyleOptionViewItem, Qt, QPainter)
    try:
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QImage
    except ImportError:
        from PyQt5.QtCore import QRect
        from PyQt5.QtGui import QImage
except ImportError as exc:
    raise unittest.SkipTest('Optional Qt dependencies are not installed') from exc


def formula(width,height):
    # The same 6x8 glyph in short and tall formula canvases, with a distant accent.
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
            '<path fill="#183c55" d="M0 0h6v8H0z"/>'
            f'<path fill="#183c55" d="M{width-2} {height-2}h2v2h-2z"/></svg>').encode()


def first_glyph_size(image):
    points=[]
    for y in range(image.height()):
        for x in range(40):
            c=image.pixelColor(x,y)
            if c.alpha()>200 and c.red()<60 and c.green()<60 and c.blue()<60:
                points.append((x,y))
    if not points:return (0,0)
    return (max(x for x,y in points)-min(x for x,y in points)+1,
            max(y for x,y in points)-min(y for x,y in points)+1)


class FormulaSizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_table_preserves_glyph_size_for_different_formula_heights(self):
        table=QTableWidget(2,1);delegate=FormulaDelegate(table);sizes=[];hints=[]
        for row,(width,height) in enumerate([(40,12),(80,30)]):
            item=QTableWidgetItem('');item.setData(Qt.UserRole+1,formula(width,height))
            table.setItem(row,0,item);index=table.model().index(row,0)
            option=QStyleOptionViewItem();option.rect=QRect(0,0,300,120)
            image=QImage(300,120,QImage.Format_ARGB32);image.fill(Qt.white)
            painter=QPainter(image);delegate.paint(painter,option,index);painter.end()
            sizes.append(first_glyph_size(image));hints.append(delegate.sizeHint(option,index))
        table.close()
        self.assertGreater(sizes[0][0],0)
        # Centering at fractional device pixels can change antialias coverage by
        # one pixel at 150% scaling; it must not change the actual glyph scale.
        for a,b in zip(sizes[0],sizes[1]):self.assertAlmostEqual(a,b,delta=1)
        self.assertGreater(hints[1].width(),hints[0].width())
        self.assertGreater(hints[1].height(),hints[0].height())

    def test_detail_preserves_glyph_size_and_intrinsic_width(self):
        view=FormulaView();view.resize(300,160);sizes=[];widths=[]
        for width,height in [(40,12),(80,30)]:
            view.set_svg(formula(width,height));view.show();self.app.processEvents()
            sizes.append(first_glyph_size(view.grab().toImage()))
            widths.append(view.minimumWidth())
        view.close()
        self.assertGreater(sizes[0][0],0)
        for a,b in zip(sizes[0],sizes[1]):self.assertAlmostEqual(a,b,delta=1)
        self.assertGreater(widths[1],widths[0])


if __name__=='__main__':unittest.main()
