"""Native, offline Qt Widgets application for the five-level SSG catalogue."""
import argparse
from functools import lru_cache
from html import escape
import json
from math import ceil
import os
from pathlib import Path
import platform
import re
import sys

try:
    from PySide6.QtCore import Qt, QTimer, QRectF, QSize, QLocale, QPoint, QPointF, QUrl, QSettings
    from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF, QPainter, QAction, QColor, QTextDocument, QIcon, QPainterPath, QPen, QImage
    from PySide6.QtSvg import QSvgRenderer
    from PySide6 import QtWidgets
except ImportError:
    from PyQt5.QtCore import Qt, QTimer, QRectF, QSize, QLocale, QPoint, QPointF, QUrl, QSettings
    from PyQt5.QtGui import QFont, QFontDatabase, QFontMetricsF, QPainter, QColor, QTextDocument, QIcon, QPainterPath, QPen, QImage
    from PyQt5.QtSvg import QSvgRenderer
    from PyQt5.QtWidgets import QAction
    from PyQt5 import QtWidgets
for _name in ('QApplication QMainWindow QWidget QVBoxLayout QHBoxLayout QGridLayout QLabel QPushButton '
              'QComboBox QLineEdit QTabWidget QTreeWidget QTreeWidgetItem QSplitter QTextBrowser '
              'QTableWidget QTableWidgetItem QHeaderView QScrollArea QFormLayout QSpinBox '
              'QFileDialog QMessageBox QFrame QListView QAbstractItemView QStyledItemDelegate QStyle QStyleOptionViewItem QStyleOptionHeader QStyleOptionComboBox QStyleOptionButton QSizePolicy QDialog QTabBar').split():
    globals()[_name]=getattr(QtWidgets,_name)

from .retrieval import SearchDatabase, DIMENSIONS, LEVELS, LEVEL_NAMES, hm_display

STYLE='''
QMainWindow, QWidget#canvas, QWidget#workspace { background: #f4f2ec; color: #202020; }
QWidget { font-family: Arial, "Helvetica Neue", sans-serif; font-size: 14px; color: #202020; }
QFrame#appHeader { background: #173f45; border: none; }
QLabel#appTitle { color: #f7f7f4; font-size: 15px; }
QFrame#appHeader { border-bottom: 1px solid #829895; }
QFrame#navigationRail { background: #242424; border: none; }
QPushButton#railButton { background: transparent; color: #f7f7f4; border: none; border-radius: 0; text-align: left; padding: 15px 19px; font-size: 16px; min-height: 25px; }
QPushButton#railButton:hover { background: #343c34; }
QPushButton#railButton:checked { background: #476b4a; }
QFrame#searchCard { background: #f8f7f2; border: 1px solid #cccac1; border-radius: 9px; }
QFrame#groupHeader { background: #32656a; border-radius: 5px; }
QLabel#groupHeaderTitle { color: #ffffff; font-size: 17px; }
QLabel#fieldLabel { font-size: 16px; color: #252525; }
QLabel#conditionsSummary, QLabel#conditionsCount { font-size: 14px; color: #292929; }
QLabel#brand { font-size: 17px; font-weight: 600; color: #252a25; }
QLabel#subtitle, QLabel#muted { color: #686f68; font-size: 12px; }
QWidget#searchForm { background: #f8f7f2; }
QWidget#chipBody { background: #f8f7f2; }
QTabWidget#contentStack::pane { border: none; background: transparent; }
QTabWidget::pane { background: #f8f7f2; border: 1px solid #d0cec6; border-radius: 5px; }
QTabBar::tab { min-width: 140px; padding: 10px 16px; color: #555c54; }
QTabWidget#sideNavigation QTabBar::tab { min-width: 102px; padding: 10px 12px; }
QTabBar::tab:selected { color: #335638; font-weight: 600; border-bottom: 2px solid #456b49; }
QTreeWidget, QTableWidget, QTextBrowser { background: #f9f8f3; border: 1px solid #d2d0c8; border-radius: 0; selection-background-color: #d8e4d4; selection-color: #182a19; }
QTreeWidget, QTableWidget { font-family: "Latin Modern Roman", "Latin Modern Math", "Times New Roman"; font-size: 16px; }
QComboBox#mathGroupSelector, QComboBox#mathGroupSelector QLineEdit { font-family: "Latin Modern Math"; font-size: 16px; }
QTreeWidget::item { min-height: 30px; padding: 3px; }
QHeaderView::section { background: #e8e8e3; border: none; border-bottom: 1px solid #cecec7; padding: 9px; color: #282b28; font-weight: 500; }
QLineEdit, QComboBox, QSpinBox { background: #f9f8f4; border: 1px solid #a7a79d; border-radius: 4px; min-height: 31px; padding: 2px 8px; }
QComboBox { combobox-popup: 0; }
QComboBox#panelSelector::drop-down { width: 0px; border: none; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #476b4a; }
QLineEdit[active="true"], QComboBox[active="true"] { border-left: 3px solid #456b49; background: #eef3e9; }
QLineEdit[invalid="true"] { border: 1px solid #a8443e; background: #fbefec; }
QLineEdit:disabled, QComboBox:disabled { background: #eeede7; color: #92988e; }
QPushButton { border: 1px solid #c7c9bf; border-radius: 5px; background: #f9f8f4; padding: 7px 13px; }
QPushButton:hover { background: #e7eee3; border-color: #7f9a7e; }
QPushButton#operationFilter:checked { background: #32656a; border-color: #32656a; color: white; }
QPushButton#primary { background: #32656a; border-color: #32656a; color: white; padding: 8px 25px; }
QPushButton#detailButton { background: #f9f8f3; border: 1px solid #6d9e9a; border-radius: 4px; color: #245f5d; padding: 3px 12px; }
QPushButton#detailButton:hover { background: #e1efed; border-color: #326b68; }
QPushButton#subtleButton { background: transparent; border: none; color: #47634a; padding: 3px 8px; }
QPushButton#advancedButton { background: transparent; border: none; color: #47634a; padding: 5px 8px; font-weight: 600; }
QPushButton#conditionChip { background: #f8f7f2; border: 1px solid #89a088; border-radius: 6px; padding: 6px 10px; color: #293b2b; }
QPushButton:disabled { color: #969b92; background: #eeede7; }
QSplitter::handle { background: #d3d2c8; width: 5px; height: 5px; }
QScrollArea { background: transparent; border: none; }
QToolTip { color: #252525; background: #fffef9; border: 1px solid #c7c9bf; padding: 6px; }
QDialog { background: #f4f2ec; }
QMenuBar { background: #173f45; color: #f5f5f2; }
QMenuBar::item:selected { background: #456448; }
'''


@lru_cache(maxsize=256)
def formula_renderer(svg):
    # Keep the stored vector formula untouched while matching the ink color of
    # the search-first theme. The geometry and common TeX scale are unchanged.
    renderer=QSvgRenderer(svg.replace(b'#183c55',b'#202020'))
    if not renderer.isValid():raise ValueError('Invalid compiled SVG formula')
    return renderer


# All stored formulas were compiled at the same TeX font size. Preserve that
# common coordinate scale; fitting each bounding box to a fixed height changes
# the font size whenever an accent, subscript or fraction makes a formula taller.
FORMULA_SCALE=2.2
# The kχ=0 zero-grading label sits in the classification tree beside 14 pt text.
# The stored formula's ink is ~9.8 pt tall per unit scale, so this factor brings
# it to the cap height of the surrounding text instead of the previous 1.3,
# which was visibly smaller than the lines above and below it.
HEADER_FORMULAS={3:Path(__file__).parent/'data/h_image.svg',4:Path(__file__).parent/'data/k_image.svg',
                 5:Path(__file__).parent/'data/q_image.svg',6:Path(__file__).parent/'data/kernel_image.svg'}
MATH_FORMULAS={'H':Path(__file__).parent/'data/h_image.svg','K':HEADER_FORMULAS[4],
               'Q':HEADER_FORMULAS[5],'kernel':HEADER_FORMULAS[6]}


def formula_size(vector):
    return vector.viewBoxF().size()*FORMULA_SCALE


def math_formula_image(path,scale=1.9):
    vector=formula_renderer(path.read_bytes());box=vector.viewBoxF()
    width=max(1,ceil(box.width()*scale));height=max(1,ceil(box.height()*scale))
    resolution=4
    image=QImage(width*resolution,height*resolution,QImage.Format_ARGB32);image.fill(Qt.transparent)
    painter=QPainter(image);painter.setRenderHint(QPainter.Antialiasing)
    vector.render(painter,QRectF(0,0,width*resolution,height*resolution));painter.end()
    return image,width,height


def overbar_markup(text):
    """Place overlines on their own glyphs instead of using combining marks."""
    return re.sub(r'([A-Za-z0-9])\u0305',r'<span style="text-decoration:overline">\1</span>',escape(str(text)))


_SUBSCRIPT_DIGITS=str.maketrans('₀₁₂₃₄₅₆₇₈₉','0123456789')
_TO_SUBSCRIPT=str.maketrans('0123456789','₀₁₂₃₄₅₆₇₈₉')

# The text face carries no Greek, so χ (in kχ) and ϱ would otherwise fall back to
# an unrelated system font and change shape and weight mid-label. Latin Modern
# Math supplies them from the same family. Used by the stylesheet and the rich
# text labels so the two never disagree.
MATH_FONT_STACK="'Latin Modern Roman','Latin Modern Math','Times New Roman',serif"
MATH_FONT_POINT_SIZE=12


def math_font(point_size=None):
    """Display font for mathematical labels, with a Greek-capable fallback."""
    font=QFont()
    font.setStyleHint(QFont.Serif)
    font.setFamilies(['Latin Modern Roman','Latin Modern Math','Times New Roman'])
    font.setPointSize(point_size or MATH_FONT_POINT_SIZE)
    return font


def rich_text(text):
    """True when a label needs HTML markup to display correctly."""
    return bool(re.search(r'[̅₀-₉ₕᵥᵢₛχρ]|\bk[123](?![0-9])|\bu\d',str(text)))


def tree_label(node):
    """Tree text for one hierarchy node.

    Level 1 carries a space-group number and its HM symbol in separate columns;
    level 5 carries the Q and K group names. The rendering path
    for level 1 is explicitly Hermann–Mauguin, so a bare ``C2`` remains distinct
    from an abstract cyclic group ``C_2``.
    """
    label=str(node['label'])
    if node['level']==1:return label.split('  ',1)[1]
    if label.startswith('Q = '):
        return 'Q = '+group_display_text(label[4:])
    return label


def math_paint_font(font):
    """Give a painter font the Greek-capable family stack of the math labels."""
    result=QFont(font) if font is not None else math_font()
    families=list(result.families())
    if 'Latin Modern Math' not in families:families.append('Latin Modern Math')
    result.setFamilies(families)
    return result


def group_display_text(text):
    """Abstract group name with its order as a subscript: ``C2 × C2`` → ``C₂ × C₂``.

    Use this only for abstract groups. A space-group symbol such as ``C2`` or
    ``P2_1/c`` keeps its digits on the baseline, because there the number is
    part of the symbol rather than the order of a cyclic group.
    """
    def factor(match):
        if match.group(6) is not None:return 'C'+{'i':'ᵢ','s':'ₛ','ᵢ':'ᵢ','ₛ':'ₛ'}[match.group(6)[1]]
        if match.group(4) is not None:
            return match.group(4)+(match.group(5) or '')
        return (match.group(1)+match.group(2).translate(_TO_SUBSCRIPT)+
                (match.group(3) or '').translate(_QUALIFIER_SUBSCRIPT))
    return _GROUP_FACTOR.sub(factor,str(text))


# Unicode has subscripts for h and v but none for d, so D2d keeps its qualifier
# on the baseline in plain text; rich text sets it properly as a subscript.
_QUALIFIER_SUBSCRIPT=str.maketrans('hvd','ₕᵥd')


# One factor of an abstract group product, e.g. the "C2" in "C2 × C2", or a
# single-letter group such as O or T which carries no order. The trailing letter
# is the Schoenflies qualifier — h and v (vertical/horizontal) for the C and D
# families, d for the diagonal one (D2d, Td), which is why d must be allowed.
_GROUP_FACTOR=re.compile(r'(?<![A-Za-z0-9₀-₉])([CDSTO])([0-9₀-₉]+)([hvdₕᵥ]?)(?![A-Za-z0-9])'
                         r'|(?<![A-Za-z0-9₀-₉])([OT])([hvd]?)(?![A-Za-z0-9])'
                         r'|(?<![A-Za-z0-9₀-₉])(C[isᵢₛ])(?![A-Za-z0-9])')

# A whole label that is nothing but a product of abstract groups.
_GROUP_PRODUCT=re.compile(r'(?:C[isᵢₛ]|[CDSTO][0-9₀-₉]*[hvdₕᵥ]?)(?: × (?:C[isᵢₛ]|[CDSTO][0-9₀-₉]*[hvdₕᵥ]?))*')

def group_sort_key(value):
    """Order abstract groups by family, numeric order, then qualifier."""
    families={'C':0,'D':1,'S':2,'T':3,'O':4}
    def factor(part):
        if part=='1':return (-1,0,0,part)
        if part in ('Ci','Cs'):return (0,0,{'Ci':0,'Cs':1}[part],part)
        match=re.fullmatch(r'([CDSTO])(\d*)([hvd]?)',part)
        if not match:return (9,0,0,part)
        family,order,suffix=match.groups()
        return (families[family],int(order or 0),{'':0,'h':1,'v':2,'d':3}[suffix],part)
    return tuple(factor(part.strip()) for part in value.split('×'))


def math_text_markup(text):
    """HTML markup for the unambiguous parts of a mixed text label.

    Only markup that cannot be confused with a space-group symbol is applied:
    overbars, the k/kχ/u subscripts, and abstract group names in a ``Q =`` or
    ``K =`` phrase. Elsewhere the digits are left alone, so ``C2`` and
    ``P2₁/c`` keep their crystallographic form.
    """
    markup=overbar_markup(text)
    markup=re.sub(r'(?<=\d)\*(?=u\d)', '', markup)
    def group(match):
        """Typeset one abstract-group factor: letter upright, order subscript."""
        if match.group(6) is not None:return '<i>C</i><sub>'+{'ᵢ':'i','ₛ':'s'}.get(match.group(6)[1],match.group(6)[1])+'</sub>'
        if match.group(4) is not None:return '<i>'+match.group(4)+'</i>'+('<sub>'+match.group(5)+'</sub>' if match.group(5) else '')
        letter,digits,suffix=match.group(1),match.group(2),match.group(3)
        digits=digits.translate(_SUBSCRIPT_DIGITS)
        suffix=(suffix or '').translate(str.maketrans('ₕᵥ','hv'))
        return '<i>'+letter+'</i><sub>'+digits+suffix+'</sub>'
    # An abstract-group value is a product such as "C2 × C2". The key is matched
    # together with its value, because Python look-behind cannot be variable
    # width; converting the whole run also catches every factor, not just the
    # first.
    markup=re.sub(r'((?:[QK]|ker ?[ϱρ]P) ?= ?)([^\s;]+(?: × [^\s;]+)*)',
                  lambda m:m.group(1)+_GROUP_FACTOR.sub(group,m.group(2)),markup)
    # The Q and K columns of the result table hold the value alone, with no key.
    # A bare product of abstract groups is then the whole label, and nothing in
    # it can be a space-group symbol, so every factor typesets.
    if _GROUP_PRODUCT.fullmatch(markup.strip()):
        markup=_GROUP_FACTOR.sub(group,markup)
    # Italic k before whatever subscript it carries. The hierarchy labels emit
    # the Unicode form (k₁, k₂, k₃) while the raw text uses k1..k3 and kχ; marking
    # the k first makes every variant italic, and the subscript digits are then
    # converted uniformly below. Without this a Unicode subscript left the k
    # upright, so it disagreed with the vector kχ of the row beneath it.
    markup=re.sub(r'\bk(?=χ|[₀-₉]|[123](?![0-9]))',r'<i>k</i>',markup)
    markup=re.sub(r'\bk(?==)',r'<i>k</i>',markup)
    # Subscript digits may also arrive as Unicode, already converted by
    # group_display_text; turn them into real subscripts so only one mechanism
    # is in play and the font renders them at the right size.
    markup=re.sub(r'([₀-₉]+)',lambda m:'<sub>'+m.group(1).translate(_SUBSCRIPT_DIGITS)+'</sub>',markup)
    markup=re.sub(r'(<i>k</i>)χ',r'\1<sub>χ</sub>',markup)
    markup=re.sub(r'(<i>k</i>)([123])(?![0-9])',r'\1<sub>\2</sub>',markup)
    return re.sub(r'(?<![A-Za-z_])u(\d+)',r'<i>u</i><sub>\1</sub>',markup)


def plain_math_document(text,font=None,markup=None):
    """Rich-text document for a label, with the same font stack everywhere."""
    doc=QTextDocument();doc.setDocumentMargin(0)
    doc.setDefaultFont(math_paint_font(font))
    doc.setHtml('<span style="font-family:'+MATH_FONT_STACK+'">'+(markup if markup is not None else math_text_markup(text))+'</span>')
    doc.adjustSize();return doc


class OverbarDelegate(QStyledItemDelegate):
    def markup_for(self,text,index):
        return math_text_markup(text)

    def document_for(self,text,font,index):
        return plain_math_document(text,font,self.markup_for(text,index))

    def sizeHint(self,option,index):
        size=super().sizeHint(option,index);text=str(index.data() or '')
        if self.markup_for(text,index)!=escape(text):
            doc=self.document_for(text,option.font,index)
            size.setHeight(max(size.height(),ceil(doc.size().height())+4))
            size.setWidth(max(size.width(),ceil(doc.idealWidth())+10))
        return size

    def paint(self,painter,option,index):
        text=str(index.data() or '')
        if self.markup_for(text,index)==escape(text):return super().paint(painter,option,index)
        opt=QStyleOptionViewItem(option);self.initStyleOption(opt,index);opt.text=''
        painter.save();style=option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem,opt,painter,option.widget);painter.restore()
        doc=self.document_for(text,option.font,index)
        painter.save();painter.setClipRect(option.rect)
        painter.translate(option.rect.left()+5,option.rect.center().y()-doc.size().height()/2)
        doc.drawContents(painter);painter.restore()


class OverbarComboBox(QComboBox):
    def wheelEvent(self,event):
        event.ignore()

    def paintEvent(self,event):
        text=self.currentText()
        if self.isEditable() or '\u0305' not in text:return super().paintEvent(event)
        option=QStyleOptionComboBox();self.initStyleOption(option);option.currentText=''
        painter=QPainter(self);style=self.style();style.drawComplexControl(QStyle.CC_ComboBox,option,painter,self)
        rect=style.subControlRect(QStyle.CC_ComboBox,option,QStyle.SC_ComboBoxEditField,self)
        doc=plain_math_document(text,self.font())
        painter.save();painter.setClipRect(rect);painter.translate(rect.left()+3,rect.center().y()-doc.size().height()/2)
        doc.drawContents(painter);painter.restore();painter.end()


class SelectionPanelCombo(OverbarComboBox):
    """Choose a single value in a grid instead of a long dropdown list."""
    PADDING=18

    def __init__(self,parent=None):
        super().__init__(parent);self.panel=None

    def _label_width(self,text,font):
        """Width a button needs for ``text``, including style margins.

        The style's own sizeHint accounts for the button frame and padding, so
        the fixed cell must not be narrower than either that or the typeset
        document; taking only the document width clipped wide labels such as
        ``4/mmm``.
        """
        probe=OverbarButton(text);probe.setFont(font)
        doc_width=ceil(max(plain_math_document(text,font).idealWidth(),0))
        return max(probe.sizeHint().width(),doc_width+self.PADDING)

    def showPopup(self):
        panel=QDialog(self,Qt.Popup);panel.setWindowTitle('Select '+self.accessibleName())
        outer=QVBoxLayout(panel);outer.setContentsMargins(6,6,6,6)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body=QWidget();grid=QGridLayout(body);grid.setSpacing(3);grid.setContentsMargins(3,3,3,3)
        font=self.font()
        labels=[self.itemText(i) for i in range(self.count())]
        # Size every cell to the widest label so that nothing is clipped and the
        # grid stays aligned; the previous fixed sizes cut text like "4/mmm".
        cell_width=(max(48,ceil(max(QFontMetricsF(font).horizontalAdvance(t) for t in labels))+24)
                    if self.accessibleName()=='Space group' else max(44,max(self._label_width(t,font) for t in labels)))
        metrics=QFontMetricsF(font)
        cell_height=max(28,ceil(metrics.height())+12)
        # Fill the available width rather than a fixed four columns: the 230
        # space groups became a very long scroll at four per row.
        screen=self.screen().availableGeometry()
        available=min(int(screen.width()*0.8),int(self.window().width()))-36
        columns=max(1,min(6,len(labels),available//(cell_width+3)))
        for i,text in enumerate(labels):
            button=OverbarButton(text);button.setCheckable(True);button.setChecked(i==self.currentIndex())
            if self.accessibleName()=='Space group':button.setStyleSheet('min-width: 0px; padding: 2px 4px;')
            button.setFixedSize(cell_width,cell_height)
            button.clicked.connect(lambda checked=False,n=i:(self.setCurrentIndex(n),panel.accept()))
            grid.addWidget(button,i//columns,i%columns)
        scroll.setWidget(body);outer.addWidget(scroll);self.panel=panel
        rows=ceil(len(labels)/columns) if labels else 1
        width=max(320,(cell_width+3)*columns+30)
        height=min(int(screen.height()*0.7),(cell_height+3)*rows+42)
        panel.resize(width,height)
        origin=self.mapToGlobal(QPoint(0,self.height()))
        x=max(screen.left(),min(origin.x(),screen.right()-panel.width()+1))
        y=origin.y() if origin.y()+panel.height()<=screen.bottom()+1 else max(screen.top(),origin.y()-self.height()-panel.height())
        panel.move(x,y);panel.show()


class OverbarButton(QPushButton):
    """Button that typesets overbars and subscripts instead of raw markup."""
    def paintEvent(self,event):
        text=self.text()
        if not rich_text(text):return super().paintEvent(event)
        option=QStyleOptionButton();self.initStyleOption(option);option.text=''
        painter=QPainter(self);self.style().drawControl(QStyle.CE_PushButton,option,painter,self)
        doc=plain_math_document(text,self.font());painter.save();painter.setClipRect(self.rect())
        painter.translate((self.width()-doc.idealWidth())/2,(self.height()-doc.size().height())/2)
        doc.drawContents(painter);painter.restore();painter.end()


class FormulaView(QLabel):
    """Scaled vector formula, sized so nothing is clipped.

    The fixed 75–115 px band around this widget cut tall formulae (a 3×3 matrix
    name needs about 148 px), so the view now reports the height it needs and
    the surrounding scroll area follows it; the area itself takes its size from
    the view instead of stretching to fill the dialog.
    """
    SCALE=2.8

    def __init__(self,text=''):
        super().__init__(text);self.vector=None
        self.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Fixed)

    def set_svg(self,svg):
        self.vector=formula_renderer(svg);super().clear()
        size=self.vector.viewBoxF().size()*self.SCALE
        self.setFixedHeight(ceil(size.height())+20)
        self.setMinimumWidth(ceil(size.width())+32);self.setMaximumWidth(16777215)
        self.updateGeometry();self.update()

    def clear(self):
        self.vector=None;self.setMinimumSize(0,0);self.setMaximumSize(16777215,16777215)
        super().clear();self.updateGeometry();self.update()

    def setText(self,text):
        self.vector=None;self.setMinimumSize(0,0);self.setMaximumHeight(16777215)
        super().setText(text);self.updateGeometry()

    def paintEvent(self,event):
        if self.vector is None:return super().paintEvent(event)
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);painter.setRenderHint(QPainter.TextAntialiasing)
        size=self.vector.viewBoxF().size()*self.SCALE
        self.vector.render(painter,QRectF(16,(self.height()-size.height())/2,size.width(),size.height()))
        painter.end()


class InlineFormula(QLabel):
    def __init__(self,path):
        super().__init__();self.vector=formula_renderer(path.read_bytes())
        box=self.vector.viewBoxF();self.width_hint=ceil(box.width()*1.5);self.height_hint=ceil(box.height()*1.5)
        self.setFixedSize(self.width_hint+4,max(24,self.height_hint+2))

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);painter.setRenderHint(QPainter.TextAntialiasing)
        self.vector.render(painter,QRectF(0,(self.height()-self.height_hint)/2,self.width_hint,self.height_hint));painter.end()


class FormulaDelegate(OverbarDelegate):
    def sizeHint(self,option,index):
        svg=index.data(Qt.UserRole+1)
        if svg and index.data(Qt.UserRole+5):return QSize(120,38)
        if svg:
            vector=formula_renderer(svg)
            scale=index.data(Qt.UserRole+4)
            size=vector.viewBoxF().size()*float(scale) if scale else formula_size(vector)
            return QSize(ceil(size.width())+18,max(38,ceil(size.height())+12))
        return super().sizeHint(option,index)

    def paint(self,painter,option,index):
        svg=index.data(Qt.UserRole+1)
        if not svg:return super().paint(painter,option,index)
        if index.data(Qt.UserRole+5):
            opt=QStyleOptionViewItem(option);self.initStyleOption(opt,index);opt.text=''
            style=option.widget.style() if option.widget else QApplication.style()
            style.drawControl(QStyle.CE_ItemViewItem,opt,painter,option.widget)
            painter.save();painter.setPen(QColor('#526556'))
            painter.drawText(option.rect.adjusted(10,0,-6,0),Qt.AlignVCenter|Qt.AlignLeft,'[matrix]')
            painter.restore();return
        try:
            vector=formula_renderer(svg)
        except Exception:return super().paint(painter,option,index)
        opt=QStyleOptionViewItem(option);self.initStyleOption(opt,index);opt.text=''
        style=option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem,opt,painter,option.widget)
        scale=index.data(Qt.UserRole+4)
        size=vector.viewBoxF().size()*float(scale) if scale else formula_size(vector)
        painter.save();painter.setClipRect(option.rect)
        painter.setRenderHint(QPainter.Antialiasing);painter.setRenderHint(QPainter.TextAntialiasing)
        vector.render(painter,QRectF(option.rect.left()+9,option.rect.top()+(option.rect.height()-size.height())/2,
                                    size.width(),size.height()))
        painter.restore()


class TreeFormulaDelegate(FormulaDelegate):
    """Render level-one Hermann–Mauguin labels without abstract-group rules."""
    def markup_for(self,text,index):
        if index.data(Qt.UserRole+2)=='space-group-symbol':
            return overbar_markup(text)
        return super().markup_for(text,index)


class ClassificationTree(QTreeWidget):
    def resizeEvent(self,event):
        super().resizeEvent(event)
        callback=getattr(self,'fill_callback',None)
        if callback:QTimer.singleShot(0,callback)


class MatrixDelegate(QStyledItemDelegate):
    """Draw exact matrix entries with TeX-style delimiters and stacked fractions."""
    @staticmethod
    def tooltip(entries):
        """Show exact entries as individually bracketed, aligned rows."""
        widths=[max(len(str(row[j])) for row in entries) for j in range(len(entries[0]))]
        lines=['[ '+',  '.join(str(value).rjust(widths[j]) for j,value in enumerate(row))+' ]' for row in entries]
        return '<pre>'+escape('\n'.join(lines))+'</pre>'

    @staticmethod
    def fraction_parts(value):
        match=re.fullmatch(r'([−-]?)((?:sqrt\([^()]*\))|\d+)/(\d+)',str(value))
        if not match:return None
        sign,numerator,denominator=match.groups()
        numerator=re.sub(r'^sqrt\(([^()]*)\)$',r'√\1',numerator)
        return sign.replace('-','−')+numerator,denominator

    @staticmethod
    def math_text(value):
        value=re.sub(r'sqrt\(([^()]*)\)',r'√\1',str(value))
        value=re.sub(r'(?<![A-Za-z_])pi(?=u\d|\b)','π',value)
        value=re.sub(r'(?<![A-Za-z_])u(\d+)',lambda m:'u'+m.group(1).translate(_TO_SUBSCRIPT),value)
        value=re.sub(r'\*\*(-?\d+)',lambda m:m.group(1).translate(str.maketrans('-0123456789','⁻⁰¹²³⁴⁵⁶⁷⁸⁹')),value)
        value=value.replace('**','^')
        value=re.sub(r'(?<=\d)\*(?=(?:u[₀-₉]+|π))','',value)
        value=re.sub(r'(?<=π)\*(?=u[₀-₉]+)','',value)
        return value.replace('-','−').replace('*','\u2009')

    @classmethod
    def expression_parts(cls,value):
        parts=[];offset=0;text=str(value)
        while True:
            start=text.find('sqrt(',offset)
            if start<0:break
            depth=1;end=start+5
            while end<len(text) and depth:
                if text[end]=='(':depth+=1
                elif text[end]==')':depth-=1
                end+=1
            if depth:break
            if start>offset:parts.append(('text',cls.math_text(text[offset:start])))
            parts.append(('root',text[start+5:end-1]));offset=end
        if offset<len(text):parts.append(('text',cls.math_text(text[offset:])))
        return parts

    @classmethod
    def expression_width(cls,value,metrics):
        return sum((cls.expression_width(text,metrics)+9 if kind=='root' else cls.text_width(text,metrics))
                   for kind,text in cls.expression_parts(value))

    @staticmethod
    def text_document(text,font):
        doc=QTextDocument();doc.setDocumentMargin(0);doc.setDefaultFont(font)
        markup=escape(text)
        markup=re.sub(r'([₀-₉]+)',lambda m:'<sub>'+m.group(1).translate(_SUBSCRIPT_DIGITS)+'</sub>',markup)
        doc.setHtml(markup)
        return doc

    @classmethod
    def text_width(cls,text,metrics):
        if re.search(r'[₀-₉]',text):return cls.text_document(text,QFont('Latin Modern Math',13)).idealWidth()
        return metrics.horizontalAdvance(text)

    @classmethod
    def radical_depth(cls,value):
        return max((1+cls.radical_depth(text) for kind,text in cls.expression_parts(value) if kind=='root'),default=0)

    @classmethod
    def matrix_cell_height(cls,entries,metrics):
        depth=max((cls.radical_depth(value) for row in entries for value in row),default=0)
        return max(36,ceil(metrics.height())+12+8*max(0,depth-1))

    @classmethod
    def draw_expression(cls,painter,rect,value):
        metrics=QFontMetricsF(painter.font());parts=cls.expression_parts(value)
        x=rect.center().x()-cls.expression_width(value,metrics)/2
        baseline=rect.center().y()+(metrics.ascent()-metrics.descent())/2
        def draw(parts,x):
            for kind,text in parts:
                if kind=='root':
                    width=cls.expression_width(text,metrics)
                    top=baseline-metrics.ascent()+2-4*cls.radical_depth(text);bottom=baseline+metrics.descent()-2
                    mid=(top+bottom)/2;pen=QPen(QColor('#202020'));pen.setWidthF(.85);painter.setPen(pen)
                    path=QPainterPath(QPointF(x,mid+2));path.lineTo(x+2,mid);path.lineTo(x+4,bottom)
                    path.lineTo(x+7,top);path.lineTo(x+9+width,top);painter.drawPath(path)
                    x=draw(cls.expression_parts(text),x+9)
                else:
                    if re.search(r'[₀-₉]',text):
                        doc=cls.text_document(text,painter.font())
                        painter.save();painter.translate(x,rect.center().y()-doc.size().height()/2)
                        doc.drawContents(painter);painter.restore();x+=doc.idealWidth()
                    else:
                        painter.drawText(QPointF(x,baseline),text);x+=metrics.horizontalAdvance(text)
            return x
        draw(parts,x)

    def sizeHint(self,option,index):
        entries=index.data(Qt.UserRole+3)
        if not entries:return super().sizeHint(option,index)
        font=QFont('Latin Modern Math',13);metrics=QFontMetricsF(font)
        widths=[]
        for j in range(len(entries[0])):
            rendered=[]
            for row in entries:
                fraction=self.fraction_parts(row[j])
                if fraction:rendered.extend(metrics.horizontalAdvance(text) for text in fraction)
                else:rendered.append(self.expression_width(row[j],metrics))
            widths.append(max(26,max(rendered)+18))
        width=max(150,ceil(sum(widths)+38))
        cell_h=self.matrix_cell_height(entries,metrics)
        return QSize(width,max(76,len(entries)*cell_h+30))

    def paint(self,painter,option,index):
        entries=index.data(Qt.UserRole+3)
        if not entries:return super().paint(painter,option,index)
        opt=QStyleOptionViewItem(option);self.initStyleOption(opt,index);opt.text=''
        style=option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem,opt,painter,option.widget)
        painter.save();painter.setClipRect(option.rect);painter.setPen(QColor('#202020'))
        painter.setRenderHint(QPainter.Antialiasing);painter.setRenderHint(QPainter.TextAntialiasing)
        count=len(entries);cols=len(entries[0])
        font=QFont('Latin Modern Math',13);metrics=QFontMetricsF(font)
        cell_h=self.matrix_cell_height(entries,metrics)
        widths=[]
        for j in range(cols):
            rendered=[]
            for row in entries:
                fraction=self.fraction_parts(row[j])
                if fraction:rendered.extend(metrics.horizontalAdvance(text) for text in fraction)
                else:rendered.append(self.expression_width(row[j],metrics))
            widths.append(max(26,max(rendered)+18))
        total=sum(widths);left=option.rect.center().x()-total/2
        top=option.rect.center().y()-count*cell_h/2
        painter.setFont(font)
        for i,row in enumerate(entries):
            x=left
            for j,value in enumerate(row):
                rect=QRectF(x,top+i*cell_h,widths[j],cell_h)
                fraction=self.fraction_parts(value)
                if fraction:
                    small=QFont(font);small.setPointSize(10);painter.setFont(small)
                    numerator,denominator=fraction
                    fraction_top=rect.top()+(cell_h-36)/2
                    self._draw_numerator(painter,QRectF(x,fraction_top,widths[j],17),numerator)
                    painter.drawText(QRectF(x,fraction_top+19,widths[j],17),Qt.AlignCenter,denominator)
                    mid=rect.center().y();pen=QPen(QColor('#202020'));pen.setWidthF(.75);painter.setPen(pen)
                    line_width=min(widths[j]*.68,max(8,metrics.horizontalAdvance(numerator)+4))
                    painter.drawLine(QPoint(int(rect.center().x()-line_width/2),int(mid)),
                                     QPoint(int(rect.center().x()+line_width/2),int(mid)))
                    painter.setFont(font)
                else:self.draw_expression(painter,rect,value)
                x+=widths[j]
        # Use the actual Latin Modern Math delimiter glyphs used by TeX, scaled
        # to the matrix height instead of hand-drawn parenthesis strokes.
        self._draw_delimiter(painter,'(',left-21,top-4,15,count*cell_h+8)
        self._draw_delimiter(painter,')',left+total+6,top-4,15,count*cell_h+8)
        painter.restore()

    @staticmethod
    def _draw_numerator(painter,rect,text):
        match=re.fullmatch(r'(−?)√(.+)',text)
        if not match:
            painter.drawText(rect,Qt.AlignCenter,text);return
        sign,radicand=match.groups();metrics=QFontMetricsF(painter.font())
        sign_width=metrics.horizontalAdvance(sign) if sign else 0
        rad_width=metrics.horizontalAdvance(radicand);total=sign_width+8+rad_width+2
        left=rect.center().x()-total/2;top=rect.top()
        if sign:painter.drawText(QRectF(left,top,sign_width,17),Qt.AlignCenter,sign)
        start=left+sign_width;rad_start=start+8
        pen=QPen(QColor('#202020'));pen.setWidthF(.8);painter.setPen(pen)
        path=QPainterPath(QPointF(start,top+9));path.lineTo(start+2,top+7);path.lineTo(start+4,top+13)
        path.lineTo(start+7,top+2);path.lineTo(rad_start+rad_width+1,top+2);painter.drawPath(path)
        painter.drawText(QRectF(rad_start,top+2,rad_width+1,15),Qt.AlignCenter,radicand)

    @staticmethod
    def _draw_delimiter(painter,glyph,x,y,width,height):
        font=QFont('Latin Modern Math');font.setPointSize(100)
        path=QPainterPath();path.addText(0,0,font,glyph);bounds=path.boundingRect()
        if bounds.width()<=0 or bounds.height()<=0:return
        painter.save();painter.translate(x,y);painter.scale(width/bounds.width(),height/bounds.height())
        painter.translate(-bounds.left(),-bounds.top());painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#202020'));painter.drawPath(path);painter.restore()


class OperationDelegate(QStyledItemDelegate):
    """Render axes and powers as mathematical subscripts and superscripts."""
    @staticmethod
    def document(value):
        markup=math_text_markup(value)
        markup=re.sub(r'sqrt\(([^()]*)\)',r'√<span style="text-decoration:overline">\1</span>',markup)
        # Space-operation symbols from space_symbols.py use sympy-style
        # sub/superscripts; typeset them rather than showing ``_x``/``^2``.
        markup=re.sub(r'_(\[[^\]]*\]|[xyz])',r'<sub>\1</sub>',markup)
        markup=re.sub(r'\^(-?\d+)',r'<sup>\1</sup>',markup)
        markup=markup.replace('Rz(', 'R<sub>z</sub>(').replace(' 2x',' 2<sub>x</sub>')
        doc=QTextDocument();doc.setDocumentMargin(0)
        doc.setHtml('<span style="font-family:'+MATH_FONT_STACK+';font-size:16px;color:#202020">'+markup+'</span>')
        doc.adjustSize();return doc

    def sizeHint(self,option,index):
        doc=self.document(str(index.data() or ''))
        return QSize(ceil(doc.idealWidth())+20,max(48,ceil(doc.size().height())+12))

    def paint(self,painter,option,index):
        opt=QStyleOptionViewItem(option);self.initStyleOption(opt,index);opt.text=''
        painter.save()
        style=option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem,opt,painter,option.widget)
        painter.restore();painter.save();painter.setClipRect(option.rect)
        doc=self.document(str(index.data() or ''))
        painter.translate(option.rect.center().x()-doc.idealWidth()/2,option.rect.center().y()-doc.size().height()/2)
        doc.drawContents(painter);painter.restore()


class ResultHeader(QHeaderView):
    def paintSection(self,painter,rect,index):
        if index not in (4,5):
            super().paintSection(painter,rect,index);return
        option=QStyleOptionHeader();self.initStyleOption(option);option.rect=rect;option.section=index
        painter.save();self.style().drawControl(QStyle.CE_Header,option,painter,self);painter.restore()
        vector=formula_renderer(HEADER_FORMULAS[index].read_bytes());box=vector.viewBoxF()
        scale=min(1.5,(rect.width()-10)/box.width(),(rect.height()-8)/box.height())
        width=box.width()*scale;height=box.height()*scale
        painter.save();vector.render(painter,QRectF(rect.center().x()-width/2,rect.center().y()-height/2,width,height));painter.restore()


def _label(text,object_name=None):
    w=QLabel(text)
    if object_name: w.setObjectName(object_name)
    return w


def _button(text,callback,primary=False):
    w=QPushButton(text);w.clicked.connect(callback)
    if primary: w.setObjectName('primary')
    return w


class MainWindow(QMainWindow):
    def __init__(self,path):
        super().__init__()
        for font in ('LatinModernRoman-Regular.otf','latinmodern-math.otf'):
            QFontDatabase.addApplicationFont(str(Path(__file__).parent/'data'/font))
        self.db=SearchDatabase(path);self.options=self.db.options()
        self.setWindowTitle('Spin Space Group Database')
        available=self.screen().availableGeometry()
        width=max(1,available.width()-40);height=max(1,available.height()-60)
        self.setMinimumSize(min(1120,width),min(760,height))
        self.resize(min(1500,width),min(980,height))
        self.current_detail=None;self.current_filters=None;self.current_total=0;self.offset=0
        self.page_size=60;self.inputs={};self.expansion_queue=[];self._closing=False
        self.settings_store=QSettings('SSGclassify','SpinSpaceGroupDatabase')
        canvas=QWidget();canvas.setObjectName('canvas');canvas.setMinimumSize(980,620)
        viewport=QScrollArea();viewport.setWidgetResizable(True);viewport.setWidget(canvas)
        self.setCentralWidget(viewport)
        outer=QVBoxLayout(canvas);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        title=QFrame();title.setObjectName('appHeader');title.setFixedHeight(50)
        th=QHBoxLayout(title);th.setContentsMargins(20,0,20,0)
        th.addWidget(_label('Spin Space Group Database','appTitle'));th.addStretch();outer.addWidget(title)
        split=QSplitter(Qt.Horizontal);self.workbench_split=split;outer.addWidget(split,1)
        split.splitterMoved.connect(lambda *_:self.apply_fit_columns() if getattr(self,'fit_columns',False) else None)
        self.navigation=QTabWidget();self.navigation.setObjectName('sideNavigation');self.navigation.setMinimumWidth(260)
        self.tree,self.tree_page=self._browser_page();self.navigation.addTab(self.tree_page,'Browse')
        self.search_page=self._search_page();self.navigation.addTab(self.search_page,'Search')
        split.addWidget(self.navigation)
        result_box=QWidget();result_box.setMinimumWidth(450)
        rl=QVBoxLayout(result_box);rl.setContentsMargins(14,12,14,12);rl.setSpacing(8)
        summary=QHBoxLayout();summary.addWidget(_label('Conditions:','conditionsSummary'))
        self.conditions_summary=_label('Conditions:  None');self.conditions_summary.hide()
        self.chip_scroll=QScrollArea();self.chip_scroll.setWidgetResizable(True);self.chip_scroll.setFixedHeight(40)
        self.chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        chip_body=QWidget();chip_body.setObjectName('chipBody');self.chip_layout=QHBoxLayout(chip_body)
        self.chip_layout.setContentsMargins(0,0,0,0);self.chip_layout.setSpacing(8);self.chip_layout.addStretch()
        self.chip_scroll.setWidget(chip_body);summary.addWidget(self.chip_scroll,1)
        self.condition_chips={};self.conditions_count=_label('0 results','conditionsCount');summary.addWidget(self.conditions_count)
        self.conditions_count.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        rl.addLayout(summary)
        self.results_title=_label('Search results','brand')
        toolbar=QHBoxLayout()
        self.sidebar_toggle=_button('‹',self.toggle_sidebar);self.sidebar_toggle.setFixedWidth(36)
        self.sidebar_toggle.setToolTip('Collapse search sidebar');toolbar.addWidget(self.sidebar_toggle)
        self.fit_columns_button=_button('Fit columns',self.toggle_fit_columns);toolbar.addWidget(self.fit_columns_button)
        self.compact_names_button=_button('Compact matrix names',self.toggle_compact_names);toolbar.addWidget(self.compact_names_button)
        self.fit_columns_button.setToolTip('Fit table columns to the available width. Full formulas remain available in Details and in each cell tooltip.')
        self.compact_names_button.setToolTip('Use a compact marker for tall or wide formulas. Hover for the full name; click again to expand.')
        toolbar.addStretch();rl.addLayout(toolbar)
        self.results=QTableWidget(0,10)
        self.results.setHorizontalHeader(ResultHeader(Qt.Horizontal,self.results))
        self.results.setItemDelegateForColumn(2,FormulaDelegate(self.results))
        for col in (3,4,5,6):self.results.setItemDelegateForColumn(col,OperationDelegate(self.results))
        # Keep the table header short enough to remain readable at laptop
        # widths.  The full representation maps are available as header
        # tooltips and in the selected-class details.
        headers=['Configuration','Spin-lattice type','SSG name','H','K','Q','ker ϱP','Xiao ID','Parameters','Details']
        self.results.setHorizontalHeaderLabels(headers)
        self.results.setColumnHidden(3,True);self.results.setColumnHidden(6,True)
        header=self.results.horizontalHeader();header.moveSection(header.visualIndex(5),header.visualIndex(4))
        for column,description in {
            3:'H = ϱ_T(T)',4:'K = ϱ(G)',5:'Q = ϱ_P(P)',
            6:'Kernel of ϱ_P',
        }.items():
            self.results.horizontalHeaderItem(column).setToolTip(description)
        self.results.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results.verticalHeader().hide();self.results.verticalHeader().setDefaultSectionSize(38)
        # The typeset Q and K values are not fixed-width: a continuous family can
        # read "(u0), r(u1), r(u2)", which overran the old 110 px columns and
        # spilled into the Xiao ID cell. Let those columns take the width their
        # delegate asks for and give the remaining space to the SSG name.
        # The typeset name, Q and K values are not fixed-width: a continuous
        # family can read "⟨r(u0), r(u1), r(u2)⟩", which overran the old 110 px
        # columns and spilled into the Xiao ID cell. Each of these columns takes
        # the width its own delegate asks for, and the table scrolls sideways
        # when the total exceeds the window rather than shrinking the formulae.
        for col in range(10):self.results.horizontalHeader().setSectionResizeMode(col,QHeaderView.Interactive)
        self.results.horizontalHeader().setStretchLastSection(True)
        self.results.horizontalHeader().setSectionsMovable(False)
        self.results.setColumnWidth(0,105);self.results.setColumnWidth(1,128)
        self.results.setColumnWidth(2,245)
        for col,width in {3:62,4:150,5:160,6:82,7:88,8:105}.items():self.results.setColumnWidth(col,width)
        self.results.setFont(QFont('Latin Modern Roman',13))
        self.results.setColumnWidth(9,82)
        self.results.setContextMenuPolicy(Qt.CustomContextMenu);self.results.customContextMenuRequested.connect(self.result_context_menu)
        self.results.itemSelectionChanged.connect(self._select_result);rl.addWidget(self.results,1)
        self.results.itemDoubleClicked.connect(lambda item:self._show_result_details(item.row()))
        pager=QHBoxLayout();self.page_label=_label('','muted');pager.addWidget(self.page_label)
        pager.addWidget(_button('Export results',self.export_results));pager.addStretch()
        pager.addWidget(_label('Rows per page:','muted'))
        self.page_size_combo=OverbarComboBox()
        for size in (60,120,240):self.page_size_combo.addItem(str(size),size)
        self.page_size_combo.currentIndexChanged.connect(self.change_page_size);pager.addWidget(self.page_size_combo)
        pager.addWidget(_label('Page:','muted'))
        self.page_jump=QSpinBox();self.page_jump.setRange(1,1);self.page_jump.setFixedWidth(76)
        self.page_jump.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.page_jump.editingFinished.connect(self.go_to_page);pager.addWidget(self.page_jump)
        self.prev=_button('Previous',lambda:self.turn_page(-1));self.next=_button('Next',lambda:self.turn_page(1))
        self.prev.setEnabled(False);self.next.setEnabled(False);pager.addWidget(self.prev);pager.addWidget(self.next)
        self.pager_widget=QWidget();self.pager_widget.setLayout(pager);rl.addWidget(self.pager_widget)
        split.addWidget(result_box);split.setStretchFactor(0,0);split.setStretchFactor(1,1);split.setSizes([330,1070])
        self._create_detail_widgets()
        self.detail_sessions=[]
        for node in self.db.children([]): self._add_node(self.tree,node)
        self.setStyleSheet(STYLE)
        self._configure_primary_dropdowns()
        help_action=QAction('User guide',self);help_action.triggered.connect(self.show_help)
        self.menuBar().addMenu('Help').addAction(help_action)
        settings=self.menuBar().addMenu('Settings')
        count_action=QAction('Show counts',self);count_action.setCheckable(True);count_action.setChecked(True)
        count_action.toggled.connect(self._show_tree_counts);settings.addAction(count_action)
        threshold_menu=settings.addMenu('Automatic expansion level')
        self.expansion_actions=[]
        for i,label in enumerate(LEVEL_NAMES,1):
            action=QAction(label,self);action.setCheckable(True);action.setChecked(i==5)
            action.triggered.connect(lambda checked=False,n=i:self.set_expansion_level(n-1))
            self.expansion_actions.append(action);threshold_menu.addAction(action)
        self.show_browse()

    def _create_detail_widgets(self):
        self.detail_window=QDialog(getattr(self,'detail_parent',self));self.detail_window.setWindowTitle('SSG Details');self.detail_window.resize(1100,1000)
        self.detail_window.setWindowFlags(self.detail_window.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        saved_geometry=self.settings_store.value('detail_geometry')
        if saved_geometry:self.detail_window.restoreGeometry(saved_geometry)
        self.detail_window.finished.connect(lambda *_:self.settings_store.setValue('detail_geometry',self.detail_window.saveGeometry()))
        detail_box=QWidget();window_layout=QVBoxLayout(self.detail_window);window_layout.addWidget(detail_box)
        dl=QVBoxLayout(detail_box);dl.setContentsMargins(0,0,0,0)
        group_header=QFrame();group_header.setObjectName('groupHeader');group_header.setFixedHeight(42)
        group_header_layout=QHBoxLayout(group_header);group_header_layout.setContentsMargins(15,0,15,0)
        group_header_layout.addWidget(_label('Group details','groupHeaderTitle'));dl.addWidget(group_header)
        dh=QHBoxLayout();self.detail_title=_label('Classification details','brand');self.detail_title.setStyleSheet('font-size: 17px;')
        dh.addWidget(self.detail_title);dh.addStretch();dh.addWidget(_button('Copy LaTeX',self.copy_name));dh.addWidget(_button('Export JSON',self.export_detail));dl.addLayout(dh)
        formula_area=QScrollArea();formula_area.setWidgetResizable(True)
        # The height follows the formula: a tall matrix name must not be cut, and
        # a one-line name must not leave an empty band above the tabs.
        formula_area.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Fixed)
        formula_area.setMinimumHeight(90)
        self.formula=FormulaView('Select an SSG to view its name and representation.');self.formula.setContentsMargins(16,10,16,10)
        self.formula.setTextInteractionFlags(Qt.TextSelectableByMouse);formula_area.setWidget(self.formula);dl.addWidget(formula_area)
        self.detail_tabs=QTabWidget();dl.addWidget(self.detail_tabs)
        self.detail_text=QTextBrowser()
        self.operation_table=QTableWidget(0,6)
        self.operation_table.setHorizontalHeaderLabels(['No.','Spin matrix','Spatial rotation','Spatial translation','Spin operation','Space operation'])
        self.operation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.operation_table.horizontalHeader().setSectionsMovable(False)
        self.operation_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.operation_table.setMinimumHeight(225)
        self.operation_table.verticalHeader().hide();self.operation_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for col in (1,2,3):self.operation_table.setItemDelegateForColumn(col,MatrixDelegate(self.operation_table))
        for col in (4,5):self.operation_table.setItemDelegateForColumn(col,OperationDelegate(self.operation_table))
        operation_page=QWidget();ol=QVBoxLayout(operation_page)
        self.parameter_note=_label('');self.parameter_note.setWordWrap(True);ol.addWidget(self.parameter_note)
        parameter_row=QHBoxLayout();self.parameter_input=QLineEdit();self.parameter_input.setPlaceholderText('e.g. 1/7 or 1/7,2/11');parameter_row.addWidget(self.parameter_input)
        self.evaluate_button=_button('Calculate',self.evaluate_parameters,True);parameter_row.addWidget(self.evaluate_button)
        self.reset_parameters_button=_button('Reset',self.reset_parameters);parameter_row.addWidget(self.reset_parameters_button)
        self.parameter_controls=QWidget();self.parameter_controls.setLayout(parameter_row);ol.addWidget(self.parameter_controls)
        self.parameter_result=QLabel();self.parameter_result.setWordWrap(True);ol.addWidget(self.parameter_result)
        self.operation_title=_label('Group operations','brand');ol.addWidget(self.operation_title)
        filter_row=QHBoxLayout();filter_row.addWidget(_label('Show:','muted'))
        self.operation_filter='all';self.operation_filter_buttons={}
        for key,label in (('nontrivial','Nontrivial spin'),('trivial','Trivial spin'),('all','All elements')):
            button=_button(label,lambda checked=False,value=key:self.set_operation_filter(value))
            button.setObjectName('operationFilter')
            button.setCheckable(True);button.setChecked(key=='all')
            self.operation_filter_buttons[key]=button;filter_row.addWidget(button)
        filter_row.addStretch();ol.addLayout(filter_row)
        self.operation_filter_status=_label('','muted');ol.addWidget(self.operation_filter_status)
        ol.addWidget(self.operation_table,1)
        self.translation_table=QTableWidget(0,6)
        self.translation_table.setHorizontalHeaderLabels(['No.','Spin matrix','Spatial rotation','Spatial translation','Spin operation','Space operation'])
        self.translation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.translation_table.verticalHeader().hide();self.translation_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for col in (1,2,3):self.translation_table.setItemDelegateForColumn(col,MatrixDelegate(self.translation_table))
        for col in (4,5):self.translation_table.setItemDelegateForColumn(col,OperationDelegate(self.translation_table))
        self.translation_table.hide()
        operation_scroll=QScrollArea();operation_scroll.setWidgetResizable(True);operation_scroll.setWidget(operation_page)
        self.detail_tabs.addTab(self.detail_text,'Classification');self.detail_tabs.addTab(operation_scroll,'Group operations')

    def set_expansion_level(self,index):
        self.tree_threshold.setCurrentIndex(index)
        for i,action in enumerate(self.expansion_actions):action.setChecked(i==index)

    def _browser_page(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(12,12,12,12)
        threshold=QComboBox()
        for i,label in enumerate(LEVEL_NAMES,1): threshold.addItem(f'{i} · {label}',i)
        threshold.setCurrentIndex(4)
        self.tree_threshold=threshold
        tree=ClassificationTree();tree.fill_callback=self._fill_tree_column
        tree.setHeaderLabels(['No.','Classification','Count'])
        tree.setTreePosition(1);tree.setIndentation(22)
        tree.setFont(QFont('Latin Modern Roman',14))
        tree.header().setStretchLastSection(False)
        tree.header().setMinimumSectionSize(30)
        tree.header().setSectionResizeMode(0,QHeaderView.Fixed);tree.setColumnWidth(0,42)
        tree.header().setSectionResizeMode(1,QHeaderView.Interactive)
        tree.header().setSectionResizeMode(2,QHeaderView.Fixed);tree.setColumnWidth(2,55)
        tree.setItemDelegateForColumn(1,TreeFormulaDelegate(tree))
        tree.itemExpanded.connect(lambda item:self._expanded(tree,item))
        tree.itemClicked.connect(lambda item,col:self._node_click(tree,item))
        v.addWidget(tree,1)
        return tree,page

    def _add_node(self,tree,node,parent=None):
        label=tree_label(node)
        number=str(node['value']) if node['level']==1 else ''
        item=QTreeWidgetItem([number,label,str(node['count'])]);item.setData(0,Qt.UserRole,{'path':node['path'],'loaded':False})
        if node['level']==1:item.setData(1,Qt.UserRole+2,'space-group-symbol')
        if node['label']=='kχ=0':item.setFont(1,math_font(16))
        item.setToolTip(1,node['label']);item.addChild(QTreeWidgetItem(['','','Loading…']))
        (parent.addChild(item) if parent else tree.addTopLevelItem(item));return item

    def _load_children(self,tree,item):
        data=item.data(0,Qt.UserRole)
        if not data or 'id' in data or data.get('loaded'): return
        item.takeChildren();path=data['path']
        if len(path)<5:
            for node in self.db.children(path): self._add_node(tree,node,item)
        else:
            offset=0
            while True:
                result=self.db.search(dict(zip(LEVELS,path)),offset=offset,limit=1000)
                for row in result['rows']:
                    child=QTreeWidgetItem(['',row['xiao'],'']);child.setToolTip(1,row['liu_latex'])
                    child.setData(0,Qt.UserRole,{'id':row['id']});item.addChild(child)
                offset+=len(result['rows'])
                if offset>=result['total']: break
        data['loaded']=True;item.setData(0,Qt.UserRole,data)
        if item.childCount()==1:
            child=item.child(0)
            if 'path' in (child.data(0,Qt.UserRole) or {}): child.setExpanded(True)

    def _expanded(self,tree,item):
        self._load_children(tree,item)
        QTimer.singleShot(0,self._fit_expanded_tree)

    def _fit_expanded_tree(self):
        if self._closing or not self.navigation.isVisible():return
        tree=self.tree
        tree.resizeColumnToContents(1)
        columns=sum(tree.columnWidth(i) for i in range(tree.columnCount()) if not tree.isColumnHidden(i))
        target=columns+self.navigation.width()-tree.viewport().width()+24
        sizes=self.workbench_split.sizes()
        available=sum(sizes)
        target=min(target,max(0,available-450))
        if len(sizes)==2 and target>sizes[0]:
            self.workbench_split.setSizes([target,available-target])
        self._fill_tree_column()

    def _fill_tree_column(self):
        if self._closing or not hasattr(self,'tree'):return
        tree=self.tree
        other=sum(tree.columnWidth(i) for i in (0,2) if not tree.isColumnHidden(i))
        tree.setColumnWidth(1,max(tree.sizeHintForColumn(1),tree.viewport().width()-other))

    def _show_tree_counts(self,checked):
        self.tree.setColumnHidden(2,not checked)
        self._fill_tree_column()

    def _expand_all_below(self,tree,item):
        self.expansion_queue.append((tree,item))
        if len(self.expansion_queue)==1: QTimer.singleShot(0,self._expansion_tick)

    def _expansion_tick(self):
        if self._closing:return  # The database is gone; queued expansions are moot.
        for _ in range(min(25,len(self.expansion_queue))):
            tree,item=self.expansion_queue.pop(0)
            try:
                self._load_children(tree,item);item.setExpanded(True)
                for i in range(item.childCount()):
                    child=item.child(i)
                    if 'path' in (child.data(0,Qt.UserRole) or {}): self.expansion_queue.append((tree,child))
            except RuntimeError: pass  # Navigation may have replaced this tree.
        if self.expansion_queue: QTimer.singleShot(0,self._expansion_tick)

    def _node_click(self,tree,item):
        data=item.data(0,Qt.UserRole) or {}
        if 'id' in data:
            parent=item.parent();path=(parent.data(0,Qt.UserRole) or {}).get('path') if parent else None
            if path and len(path)==5:
                self._sync_tree_filters(path)
                index=parent.indexOfChild(item);offset=(index//self.page_size)*self.page_size
                self.set_results(dict(zip(LEVELS,path)),offset)
                self.results.selectRow(index-offset)
            else:self.open_detail(data['id'])
            self._open_detail_session(data['id'])
            return
        if 'path' not in data:return
        path=data['path'];self._sync_tree_filters(path);self.set_results(dict(zip(LEVELS,path)))
        threshold=self.tree_threshold.currentData()
        if len(path)>=threshold: self._expand_all_below(tree,item)
        else: item.setExpanded(True)

    def _sync_tree_filters(self,path):
        self.clear_filters()
        for index,key in enumerate(('parent','dimension','category')):
            if index>=len(path):break
            value=int(path[index]) if key=='parent' else path[index]
            field=self.inputs[key];position=field.findData(value)
            if position>=0:field.setCurrentIndex(position)

    def _combo(self,items,panel_name=None):
        w=SelectionPanelCombo() if panel_name else OverbarComboBox();w.addItem('All',None)
        if panel_name:w.setAccessibleName(panel_name);w.setObjectName('panelSelector')
        for label,value in items: w.addItem(group_display_text(label),value)
        w.setView(QListView(w));w.view().setItemDelegate(OverbarDelegate(w.view()))
        w.setMinimumContentsLength(8)
        w.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        w.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        w.currentTextChanged.connect(w.setToolTip)
        return w

    def _configure_primary_dropdowns(self):
        """Size the three related controls and their lists to the screen."""
        parent=self.inputs['parent'];metrics=parent.fontMetrics()
        widest=max(metrics.horizontalAdvance(parent.itemText(i)) for i in range(parent.count()))
        minimum_width=widest+32  # room for the drop-down indicator and padding
        available=self.screen().availableGeometry().height()
        visible_rows=min(24,max(1,(available-80)//(metrics.height()+10)))
        for key in ('parent','dimension','category'):
            combo=self.inputs[key]
            combo.setMinimumWidth(minimum_width)
            combo.setView(QListView(combo))
            combo.view().setItemDelegate(OverbarDelegate(combo.view()))
            combo.setMaxVisibleItems(visible_rows)
            combo.view().setMinimumWidth(minimum_width)

    def _search_page(self):
        page=QWidget();self.search_card=page
        layout=QVBoxLayout(page);layout.setContentsMargins(12,12,12,12);layout.setSpacing(10)
        self.tag_section=QFrame();tag_layout=QVBoxLayout(self.tag_section);tag_layout.setContentsMargins(0,0,0,0)
        tag_layout.addWidget(_label('Label search','fieldLabel'))
        tagrow=QHBoxLayout();self.tag_input=QLineEdit();self.tag_input.setPlaceholderText('Xiao ID')
        self.tag_input.returnPressed.connect(self.search_tag);tagrow.addWidget(self.tag_input)
        tagrow.addWidget(_button('Search',self.search_tag));tag_layout.addLayout(tagrow);layout.addWidget(self.tag_section)
        separator=QFrame();separator.setFrameShape(QFrame.HLine);layout.addWidget(separator)
        self.condition_section=QFrame();condition_layout=QVBoxLayout(self.condition_section);condition_layout.setContentsMargins(0,0,0,0)
        condition_layout.addWidget(_label('Condition search','fieldLabel'))
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();body.setObjectName('searchForm')
        form=QFormLayout(body);self.search_form=form;form.setRowWrapPolicy(QFormLayout.WrapAllRows);form.setVerticalSpacing(8)
        self.inputs['parent']=self._combo([(str(p['number']),p['number']) for p in self.options['parents']],'Space group')
        self.inputs['parent'].setEditable(True)
        self.inputs['parent'].lineEdit().setPlaceholderText('1–230')
        self.inputs['parent'].lineEdit().editingFinished.connect(self._parent_text_finished)
        for key in ('bravais','point_group','category','q_name','k_name','kernel_name'):
            items=self.options[key]
            if key=='k_name':items=[r[0] for r in self.db.connection.execute('SELECT DISTINCT k_name FROM classes WHERE family=0 ORDER BY k_name')]
            if key in ('q_name','k_name','kernel_name'):items=sorted(items,key=group_sort_key)
            self.inputs[key]=self._combo([(hm_display(v) if key=='point_group' else v,v) for v in items],key if key in ('bravais','point_group') else None)
        self.inputs['k_name'].setEditable(True)
        self.inputs['k_name'].setObjectName('mathGroupSelector')
        no_insert=getattr(QComboBox,'NoInsert',None)
        if no_insert is None:no_insert=QComboBox.InsertPolicy.NoInsert
        self.inputs['k_name'].setInsertPolicy(no_insert)
        self.inputs['k_name'].setDuplicatesEnabled(False)
        self.inputs['dimension']=self._combo([(label,key) for key,label in DIMENSIONS.items()])
        self.inputs['family']=self._combo([('Continuous families',1),('Discrete entries',0)])
        self.wave_status={}
        wave_placeholders={'kchi':'character wavevector, e.g. 0,0,1/2',
                           'k1':'first wavevector, e.g. 0,0,1/2',
                           'k2':'second wavevector (optional)',
                           'k3':'third wavevector (optional)'}
        for key in ('kchi','k1','k2','k3'):self.inputs[key]=QLineEdit()
        for key in ('kchi','k1','k2','k3'):
            w=self.inputs[key];w.setPlaceholderText(wave_placeholders[key]);w.setEnabled(False)
            w.setToolTip('Conventional reciprocal coordinates. Select a Bravais lattice first. The search checks equivalent representatives and parameter domains.')
        labels=[('parent','Space group'),('bravais','Bravais lattice'),('point_group','Crystallographic point group'),
                ('dimension','Configuration'),('category','Spin-lattice type'),('family','Parameter type'),
                ('kchi','kχ'),('k1','k₁'),('k2','k₂'),('k3','k₃'),('q_name','Q = ϱ<sub>P</sub>(P)'),
                ('k_name','K = ϱ(G) (only for discrete SSGs)'),('kernel_name','ker ϱ<sub>P</sub>')]
        for key,label in labels:
            if key in ('q_name','k_name','kernel_name'):
                math_key={'q_name':'Q','k_name':'K','kernel_name':'kernel'}[key]
                label_widget=QWidget();line=QHBoxLayout(label_widget);line.setContentsMargins(0,0,0,0);line.setSpacing(5)
                line.addWidget(InlineFormula(MATH_FORMULAS[math_key]))
                if key=='k_name':line.addWidget(_label('only for discrete SSGs'))
                line.addStretch();label_widget.setAccessibleName(label);label=label_widget
            if key in ('parent','bravais','point_group'):
                wrapper=QWidget();selector=QHBoxLayout(wrapper);selector.setContentsMargins(0,0,0,0)
                selector.addWidget(self.inputs[key],1);selector.addWidget(_button('Select',self.inputs[key].showPopup))
                form.addRow(label,wrapper)
            elif key in ('kchi','k1','k2','k3'):
                holder=QWidget();line=QHBoxLayout(holder);line.setContentsMargins(0,0,0,0);line.setSpacing(6)
                line.addWidget(self.inputs[key],1);indicator=_label('');indicator.setFixedWidth(18)
                indicator.setAlignment(Qt.AlignCenter);self.wave_status[key]=indicator;line.addWidget(indicator)
                form.addRow(label,holder)
            else:form.addRow(label,self.inputs[key])
        scroll.setWidget(body);condition_layout.addWidget(scroll,1);layout.addWidget(self.condition_section,1)
        self.inputs['parent'].currentIndexChanged.connect(self._parent_changed)
        self.inputs['bravais'].currentIndexChanged.connect(self._waves_enabled)
        self.inputs['dimension'].currentIndexChanged.connect(self._dimension_changed)
        self.inputs['category'].currentIndexChanged.connect(self._category_changed)
        for w in self.inputs.values():
            if isinstance(w,QLineEdit):
                w.returnPressed.connect(self.run_search);w.textChanged.connect(self._refresh_filter_styles)
        for key in ('kchi','k1','k2','k3'):
            self.inputs[key].editingFinished.connect(lambda k=key:self._validate_wavevector(k))
            self.inputs[key].textChanged.connect(self._validate_all_wavevectors)
        for key,w in self.inputs.items():
            if isinstance(w,QComboBox):w.currentIndexChanged.connect(self._refresh_filter_styles)
        self.tag_input.textChanged.connect(self._refresh_filter_styles)
        self.error_label=QLabel();self.error_label.setWordWrap(True);self.error_label.setStyleSheet('color:#9b3c36;');layout.addWidget(self.error_label)
        buttons=QHBoxLayout();buttons.addWidget(_button('Reset',self.clear_filters));buttons.addWidget(_button('Search',self.run_search,True));layout.addLayout(buttons)
        return page

    @staticmethod
    def _wavevector_error(text):
        if not text.strip():return ''
        fields=[part.strip() for part in text.split(',')]
        if len(fields)!=3:return 'Enter three reciprocal coordinates, separated by commas.'
        number=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:/[+-]?\d+)?'
        if not all(re.fullmatch(number,value) for value in fields):
            return 'Use numbers, decimals, or fractions such as 1/2.'
        if any('/' in value and int(value.rsplit('/',1)[1])==0 for value in fields):return 'A fraction denominator cannot be zero.'
        return ''

    def _validate_wavevector(self,key):
        field=self.inputs[key];text=field.text().strip();error=self._wavevector_error(text)
        if key=='k2' and text and not self.inputs['k1'].text().strip():
            error='Wavevectors must be entered in order: fill k₁ before k₂.'
        if key=='k3' and text and not self.inputs['k2'].text().strip():
            error='Wavevectors must be entered in order: fill k₂ before k₃.'
        field.setProperty('invalid',bool(error));field.style().unpolish(field);field.style().polish(field)
        indicator=self.wave_status.get(key)
        if indicator:
            indicator.setText('!' if error else '✓' if text else '')
            indicator.setStyleSheet('color:#a8443e;font-weight:600;' if error else 'color:#456b49;font-weight:600;')
        field.setToolTip(error or 'Conventional reciprocal coordinates. Search includes equivalent representatives and parameter domains.')
        return error

    def _validate_all_wavevectors(self,*_):
        for key in ('kchi','k1','k2','k3'):self._validate_wavevector(key)

    def _refresh_filter_styles(self,*_):
        for key,field in self.inputs.items():
            if isinstance(field,QComboBox):
                active=field.currentData() is not None or (field.isEditable() and field.currentText().strip() not in ('','All'))
            else:active=bool(field.text().strip())
            field.setProperty('active',active);field.style().unpolish(field);field.style().polish(field)
        active=bool(self.tag_input.text().strip())
        self.tag_input.setProperty('active',active);self.tag_input.style().unpolish(self.tag_input);self.tag_input.style().polish(self.tag_input)

    def toggle_sidebar(self):
        collapsed=self.navigation.isVisible()
        self.navigation.setVisible(not collapsed)
        self.sidebar_toggle.setText('›' if collapsed else '‹')
        self.sidebar_toggle.setToolTip('Show search sidebar' if collapsed else 'Collapse search sidebar')

    def toggle_fit_columns(self):
        self.fit_columns=not getattr(self,'fit_columns',False)
        if not self.fit_columns:
            header=self.results.horizontalHeader()
            for col in range(10):header.setSectionResizeMode(col,QHeaderView.Interactive)
            for col,width in getattr(self,'natural_column_widths',{}).items():
                if not self.results.isColumnHidden(col):self.results.setColumnWidth(col,width)
            self.fit_columns_button.setText('Fit columns')
            return
        self.natural_column_widths={col:self.results.columnWidth(col) for col in range(10) if not self.results.isColumnHidden(col)}
        self.apply_fit_columns()
        self.fit_columns_button.setText('Natural widths')

    def apply_fit_columns(self):
        header=self.results.horizontalHeader()
        for col in range(10):header.setSectionResizeMode(col,QHeaderView.Fixed)
        available=max(450,self.results.viewport().width()-4)
        base={0:100,1:140,4:150,5:160,7:78,8:104,9:100}
        for col in (4,5):base[col]=max(base[col],self.results.sizeHintForColumn(col)+8)
        for col,width in base.items():self.results.setColumnWidth(col,width)
        used=sum(base.values())
        self.results.setColumnWidth(2,max(140,available-used,self.results.sizeHintForColumn(2)+8))

    def toggle_compact_names(self):
        compact=not getattr(self,'compact_names',False);self.compact_names=compact
        for row in range(self.results.rowCount()):
            item=self.results.item(row,2)
            if not item:continue
            svg=item.data(Qt.UserRole+1)
            complex_formula=False
            if svg:
                try:
                    box=formula_renderer(svg).viewBoxF()
                    complex_formula=box.height()>24 or box.width()>250
                except Exception:pass
            item.setData(Qt.UserRole+5,bool(compact and complex_formula))
        if compact:
            for row in range(self.results.rowCount()):self.results.setRowHeight(row,38)
        else:self.results.resizeRowsToContents()
        self.results.viewport().update()
        self.compact_names_button.setText('Expand matrix names' if compact else 'Compact matrix names')

    def change_page_size(self,index):
        if index<0:return
        old=self.page_size;page=self.offset//old+1
        self.page_size=int(self.page_size_combo.currentData())
        if self.current_filters:self.set_results(self.current_filters,(page-1)*self.page_size)

    def go_to_page(self):
        if self.current_filters:self.set_results(self.current_filters,(self.page_jump.value()-1)*self.page_size)

    def set_operation_filter(self,mode):
        if mode not in ('all','trivial','nontrivial'):return
        self.operation_filter=mode
        for key,button in self.operation_filter_buttons.items():button.setChecked(key==mode)
        rows=getattr(self,'_all_operation_rows',[])
        if mode!='all':
            from sympy import ImmutableMatrix
            identity=ImmutableMatrix.eye(3)
            def nontrivial(row):
                matrix=ImmutableMatrix(row['spin'])
                return matrix.equals(identity) is not True
            rows=[row for row in rows if nontrivial(row)==(mode=='nontrivial')]
        populate=getattr(self,'_populate_operation_table',None)
        if populate:populate(self.operation_table,rows)
        total=len(getattr(self,'_all_operation_rows',[]))
        self.operation_filter_status.setText(f'Showing {len(rows)} of {total} elements')

    def result_context_menu(self,position):
        row=self.results.rowAt(position.y())
        if row<0:return
        self.results.selectRow(row)
        menu=QtWidgets.QMenu(self)
        menu.addAction('Copy SSG name',self.copy_plain_name)
        menu.addAction('Copy LaTeX',self.copy_name)
        menu.addAction('Copy Xiao ID',self.copy_xiao_id)
        menu.addSeparator();menu.addAction('Locate in Browse tree',self.locate_current_in_tree)
        menu.exec(self.results.viewport().mapToGlobal(position))

    def copy_plain_name(self):
        if self.current_detail:QApplication.clipboard().setText(self.current_detail['display_name'])

    def copy_xiao_id(self):
        if self.current_detail:QApplication.clipboard().setText(self.current_detail['xiao'])

    def locate_current_in_tree(self):
        if not self.current_detail:return
        path=[];current_items=[self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        found=None
        for value in self.current_detail['hierarchy']:
            path.append(str(value));match=None
            for item in current_items:
                data=item.data(0,Qt.UserRole) or {}
                if data.get('path')==path:match=item;break
            if match is None:return
            self.tree.expandItem(match);self._load_children(self.tree,match)
            current_items=[match.child(i) for i in range(match.childCount())]
        for item in current_items:
            data=item.data(0,Qt.UserRole) or {}
            if data.get('id')==self.current_detail['id']:found=item;break
        if found:
            self.show_browse();self.tree.setCurrentItem(found);self.tree.scrollToItem(found)

    def _condition_value(self,key,value,filters):
        if key in ('spin_bravais','crystal_id'):
            return self.db.hierarchy_label(key,value,filters=filters)
        return DIMENSIONS.get(value,value) if key=='dimension' else hm_display(value) if key=='point_group' else value

    def _set_condition_chips(self,filters):
        while self.chip_layout.count():
            item=self.chip_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        self.condition_chips={}
        names={**dict(zip(LEVELS,LEVEL_NAMES)),'parent':'Space group','k1':'Wavevector','text':'Label'}
        for key,value in filters.items():
            if key in ('bravais','point_group') and 'parent' in filters:continue
            displayed=self._condition_value(key,value,filters)
            chip=OverbarButton(f'{names.get(key,key)}: {displayed}  ×');chip.setObjectName('conditionChip')
            chip.clicked.connect(lambda checked=False,k=key:self._remove_condition(k))
            self.condition_chips[key]=chip;self.chip_layout.addWidget(chip)
        self.chip_layout.addStretch()

    def _remove_condition(self,key):
        if not self.current_filters or key not in self.current_filters:return
        remaining=dict(self.current_filters);remaining.pop(key)
        if remaining:
            try:self.set_results(remaining);self.error_label.clear()
            except (ValueError,KeyError) as exc:self.error_label.setText(str(exc));return
        else:
            self.current_filters=None;self.current_total=0;self.offset=0
            self.results.setRowCount(0);self.current_detail=None;self.detail_window.close()
            self.operation_table.setRowCount(0);self.translation_table.setRowCount(0)
            self.formula.clear();self.detail_text.clear();self.parameter_result.clear()
            self.page_label.clear();self.prev.setEnabled(False);self.next.setEnabled(False)
            self.page_jump.setRange(1,1);self.page_jump.setValue(1)
            self.conditions_summary.setText('Conditions:  None');self.conditions_count.setText('0 results')
            self._set_condition_chips({})
        if key=='text':self.tag_input.clear()
        elif key in self.inputs:
            field=self.inputs[key]
            if isinstance(field,QComboBox):field.setCurrentIndex(0)
            else:field.clear()

    def _parent_changed(self):
        value=self.inputs['parent'].currentData()
        if value is not None:
            p=self.db.parent(value)
            for key in ('bravais','point_group'):
                w=self.inputs[key];w.setCurrentIndex(w.findData(p[key]));w.setEnabled(False)
        else:
            for key in ('bravais','point_group'): self.inputs[key].setEnabled(True)
        self._waves_enabled()

    def _parent_text_finished(self):
        field=self.inputs['parent'];text=field.currentText().strip()
        if not text or text.lower()=='all':field.setCurrentIndex(0);return
        if text.isdigit() and 1<=int(text)<=230:
            field.setCurrentIndex(field.findData(int(text)));self._parent_changed()
        else:self.error_label.setText('Enter a space-group number from 1 to 230.')

    def _waves_enabled(self):
        enabled=self.inputs['bravais'].currentData() is not None
        for key in ('kchi','k1','k2','k3'):
            self.inputs[key].setEnabled(enabled)
            if not enabled:self.inputs[key].clear()

    def _dimension_changed(self):
        dim=self.inputs['dimension'].currentData();w=self.inputs['category'];old=w.currentData()
        w.blockSignals(True);w.clear();w.addItem('All',None)
        for category in self.options['category']:
            if dim is None or category.startswith(dim+'.'):w.addItem(category,category)
        if old is not None and w.findData(old)>=0:w.setCurrentIndex(w.findData(old))
        w.blockSignals(False)

    def _category_changed(self):
        value=self.inputs['category'].currentData()
        if value:self.inputs['dimension'].setCurrentIndex(self.inputs['dimension'].findData(value[0]))

    def clear_filters(self):
        self.tag_input.clear()
        for w in self.inputs.values():
            if isinstance(w,QComboBox):w.setCurrentIndex(0)
            else:w.clear()
        self._parent_changed();self._waves_enabled();self.error_label.clear()

    def run_search(self):
        for key in ('kchi','k1','k2','k3'):
            error=self._validate_wavevector(key)
            if error:self.error_label.setText(error);return
        filters={}
        for key,w in self.inputs.items():
            value=w.currentData() if isinstance(w,QComboBox) else w.text().strip()
            if isinstance(w,QComboBox) and w.isEditable() and value is None and w.currentText()!='All':value=w.currentText().strip()
            if value is not None and value!='':filters[key]=value
        if 'k_name' in filters:
            if filters.get('family')==1:
                self.error_label.setText('K search is available for discrete entries only.');return
            filters['family']=0
        try:self.set_results(filters);self.error_label.clear()
        except (ValueError,KeyError) as exc:self.error_label.setText(str(exc))

    def search_tag(self):
        value=self.tag_input.text().strip()
        if not value:return
        try:self.set_results({'text':value});self.error_label.clear()
        except (ValueError,KeyError) as exc:self.error_label.setText(str(exc))

    def set_results(self,filters,offset=0):
        result=self.db.search(filters,limit=self.page_size,offset=offset)
        self.current_filters=filters;self.current_total=result['total'];self.offset=offset
        names={**dict(zip(LEVELS,LEVEL_NAMES)),'k1':'Wavevector','text':'Label'}
        summary=['%s: %s' % (names.get(k,k),self._condition_value(k,v,filters)) for k,v in filters.items()]
        self.conditions_summary.setText('Conditions:  '+('  |  '.join(summary) if summary else 'None'))
        self._set_condition_chips(filters)
        self.conditions_count.setText(f"{result['total']:,} results")
        self.results.blockSignals(True);self.results.setRowCount(len(result['rows']))
        for i,row in enumerate(result['rows']):
            values=[DIMENSIONS[row['dimension']],row['category'],row['display_name'],row['h_name'],row['k_name'],row['q_name'],row['kernel_name'],row['xiao'],
                    'Matched value' if row.get('matched_specialization') else 'Continuous family' if row['family'] else 'Discrete']
            for j,value in enumerate(values):
                full_value=str(value);display_value=full_value
                item=QTableWidgetItem(display_value);item.setToolTip(full_value);item.setData(Qt.UserRole,row['id'])
                if j==2:
                    item.setData(Qt.UserRole+1,self.db.formula_svg(row['id']));item.setToolTip(row['liu_latex'])
                item.setData(Qt.UserRole+2,row.get('matched_specialization'))
                if j==7:item.setFont(QFont('Latin Modern Roman',12))
                self.results.setItem(i,j,item)
            button=QPushButton('Details');button.setObjectName('detailButton')
            button.clicked.connect(lambda checked=False,index=i:self._show_result_details(index))
            holder=QWidget();button_row=QHBoxLayout(holder);button_row.setContentsMargins(4,3,4,3)
            button.setFixedSize(74,29);button_row.addWidget(button,0,Qt.AlignCenter)
            self.results.setCellWidget(i,9,holder)
            if getattr(self,'compact_names',False):
                name_item=self.results.item(i,2);svg=name_item.data(Qt.UserRole+1)
                if svg and formula_renderer(svg).viewBoxF().height()>24:name_item.setData(Qt.UserRole+5,True)
        self.results.blockSignals(False)
        if getattr(self,'fit_columns',False):self.apply_fit_columns()
        else:
            for col in (2,4,5):
                self.results.setColumnWidth(col,max(self.results.columnWidth(col),self.results.sizeHintForColumn(col)+8))
        if getattr(self,'compact_names',False):
            for r in range(self.results.rowCount()):self.results.setRowHeight(r,38)
        else:self.results.resizeRowsToContents()
        self.results_title.setText(f"Search results  |  {result['total']:,} classifications")
        pages=max(1,ceil(result['total']/self.page_size));page=offset//self.page_size+1
        self.page_jump.blockSignals(True);self.page_jump.setMaximum(pages);self.page_jump.setValue(min(page,pages));self.page_jump.blockSignals(False)
        self.page_label.setText(f"{offset+1 if result['total'] else 0}–{offset+len(result['rows'])} / {result['total']:,} items")
        self.prev.setEnabled(offset>0);self.next.setEnabled(offset+len(result['rows'])<result['total'])
        if result['rows']:
            # Selecting row zero again need not emit a selection-change signal.
            self.results.blockSignals(True);self.results.selectRow(0);self.results.blockSignals(False)
            self._select_result()
            self.results.scrollToTop()
        else:
            self.current_detail=None;self.detail_title.setText('No selection')
            self.detail_window.close();self.operation_table.setRowCount(0);self.translation_table.setRowCount(0)
            self.formula.clear();self.formula.setText('No matching entries. Adjust the search conditions.')
            self.detail_text.clear();self.parameter_result.clear()
            self.evaluate_button.setEnabled(False)

    def turn_page(self,direction):
        if self.current_filters:self.set_results(self.current_filters,max(0,self.offset+direction*self.page_size))

    def _select_result(self):
        row=self.results.currentRow()
        if row>=0 and self.results.item(row,0):
            self.open_detail(self.results.item(row,0).data(Qt.UserRole),self.results.item(row,0).data(Qt.UserRole+2))

    def _show_result_details(self,row):
        if row<0 or row>=self.results.rowCount():return
        self.results.selectRow(row);self._select_result()
        item=self.results.item(row,0)
        if item:self._open_detail_session(item.data(Qt.UserRole),item.data(Qt.UserRole+2))

    def _open_detail_session(self,identifier,query_match=None):
        session=DetailSession(self,identifier,query_match)
        self.detail_sessions.append(session)
        session.detail_window.show();session.detail_window.raise_()
        return session

    def show_search(self):
        self.navigation.setCurrentIndex(1)

    def show_browse(self):
        self.navigation.setCurrentIndex(0)

    def show_group_detail(self,parameters=None,*,report_errors=True,use_match=True,approximate=False):
        if not self.current_detail:return
        if not self.detail_window.isVisible():self.detail_tabs.setCurrentIndex(0)
        from .group_display import point_operation_rows,translation_generator_rows,matched_section_rows
        from ssg_enumeration.naming import _spin_symbol
        from sympy import ImmutableMatrix
        try:
            match=self.current_detail.get('query_match')
            if parameters is None and match and use_match:
                rows,translation_rows=matched_section_rows(self.current_detail,match)
                self.operation_title.setText('Translation generators and point operations of the matched representative')
            else:
                rows=point_operation_rows(self.current_detail,parameters,approximate)
                translation_rows=translation_generator_rows(self.current_detail,parameters,approximate)
                if approximate and parameters is not None:
                    symbolic_rows=point_operation_rows(self.current_detail)
                    symbolic_translations=translation_generator_rows(self.current_detail)
                    for actual,original in zip(rows+translation_rows,symbolic_rows+symbolic_translations):
                        actual['symbolic_spin']=original['spin']
                self.operation_title.setText('Translation generators and point operations')
        except (ValueError,ArithmeticError) as exc:
            if not report_errors:raise
            self.operation_table.setRowCount(0)
            self.operation_title.setText('Group operations unavailable')
            QMessageBox.warning(self.detail_window,'Cannot display group operations',str(exc))
            return
        def matrix_text(m):
            lines=['  '.join(matrix_value(m[i,j]) for j in range(m.cols)) for i in range(m.rows)]
            if len(lines)==3:
                return '\n'.join(left+' '+line+' '+right for left,line,right in zip('⎛⎜⎝',lines,'⎞⎟⎠'))
            return '\n'.join(lines)
        def matrix_value(value):
            if approximate and getattr(value,'is_Float',False):
                return format(float(value),'.7g').replace('-', '−')
            return str(value).replace('-', '−')
        def populate(table,entries):
            from .space_symbols import symbol_for_rotation
            number=self.current_detail['parent']
            def space_rotation(row):
                # Every operation needs its own symbol; the stored setting names
                # only the HM generators, so a lookup by point index would print
                # an identical fallback in every row.
                try:symbol=symbol_for_rotation(row['rotation'],number)
                except (ValueError,KeyError):symbol='matrix'
                return re.sub(r'-(\d+|m)(_|$)',lambda m:m.group(1)+'̅'+m.group(2),symbol)
            table.setRowCount(len(entries))
            for i,row in enumerate(entries):
                symbol=row.get('spin_label')
                if symbol is None:
                    try:
                        original=row.get('symbolic_spin',row['spin'])
                        symbol='Numerical matrix' if approximate and original.free_symbols else _spin_symbol(ImmutableMatrix(original))
                        if symbol.startswith('M['):symbol='= matrix'
                        symbol=re.sub(r'-(\d+)',lambda m:m.group(1)+'̅',symbol)
                    except Exception:symbol='= matrix'
                translation=','.join(str(x).replace('-','−') for x in row['translation'])
                spatial='{'+space_rotation(row)+' | '+translation+'}'
                for j,value in enumerate((str(row['index']),matrix_text(row['spin']),matrix_text(row['rotation']),matrix_text(row['translation']),symbol,spatial)):
                    item=QTableWidgetItem(value);item.setTextAlignment(Qt.AlignCenter)
                    if j==0:item.setFont(QFont('Latin Modern Roman',12))
                    if 1<=j<=3:
                        matrix=(row['spin'],row['rotation'],row['translation'])[j-1]
                        entries=[[matrix_value(matrix[a,b]) for b in range(matrix.cols)] for a in range(matrix.rows)]
                        item.setData(Qt.UserRole+3,entries)
                        item.setToolTip(MatrixDelegate.tooltip(entries))
                    elif j==4 and symbol in ('= matrix','See spin matrix'):
                        item.setToolTip('No short symbol; the exact matrix is shown in this row.')
                    table.setItem(i,j,item)
            table.resizeRowsToContents()
            table.resizeColumnsToContents()
            extra=max(0,self.detail_window.width()-70-sum(table.columnWidth(j) for j in range(6)))
            for j in (1,2,3):table.setColumnWidth(j,table.columnWidth(j)+extra//3)
        combined=[dict(row,index='T'+str(row['index'])) for row in translation_rows]+rows
        self._all_operation_rows=combined
        self._populate_operation_table=populate
        self.set_operation_filter(self.operation_filter)
        populate(self.translation_table,translation_rows)
        self.detail_window.show();self.detail_window.raise_()

    def open_detail(self,identifier,query_match=None):
        if self.current_detail is None or self.current_detail.get('id')!=identifier:
            self.operation_filter='all'
            for key,button in self.operation_filter_buttons.items():button.setChecked(key=='all')
        d=self.db.detail(identifier);self.current_detail=d;c=d['crystal'];parent=d['parent_info']
        self.detail_window.setWindowTitle(d['xiao']+' | Spin Space Group')
        self.detail_title.setText(d['xiao']+'  |  '+DIMENSIONS[d['dimension']])
        svg=self.db.formula_svg(d['id'])
        if svg:self.formula.set_svg(svg)
        else:self.formula.setText(d['display_name'])
        rows=[('Parent space group',f"{d['parent']}  {hm_display(parent['hm'])}"),
              ('Spin-lattice type',d['category']),('Spin Bravais lattice',d['wave_description']),
              ('H = ϱT(T)',group_display_text(c['h_name'])),('K = ϱ(G)',group_display_text(c['k_name'])),
              ('Q = ϱP(P)',group_display_text(c['q_name'])+f"  (order {c['q_order']})"),
              ('ker ϱP',group_display_text(d['kernel_name'])+f"  (order {d['kernel_order']})")]
        html='<style>td{padding:7px 10px;font-family:'+MATH_FONT_STACK+';font-size:17px;} th{text-align:left;padding:7px;color:#58675c;} p{line-height:1.6;} .math{font-family:'+MATH_FONT_STACK+';font-size:17px;font-weight:normal;}</style>'
        if query_match:
            d['query_match']=query_match;m=query_match['crystal']
            html+='<p style="background:#e3f1eb;padding:10px;"><b>Compatible value for this search</b><br>'+escape(
                'Wavevector '+str(query_match['wavevectors'])+'; matched representative parameters '+str(query_match['parameters'])+
                '; Q = '+m['q_name']+', K = '+m['k_name']+', kernel = '+str(m['kernel']))+'</p>'
            html+='<p>Group operations use the matched representative and its spin frame. Its parameters may differ from those of the displayed name.</p>'
        image_resources={}
        math_labels={}
        for key,name in (('H = ϱT(T)','H'),('K = ϱ(G)','K'),('Q = ϱP(P)','Q'),('ker ϱP','kernel')):
            image,width,height=math_formula_image(MATH_FORMULAS[name]);url=QUrl('math://'+name)
            image_resources[url]=image
            math_labels[key]=f'<img src="{url.toString()}" width="{width}" height="{height}" />'
        def table_row(key,value):
            value_markup=math_text_markup(value)
            return '<tr><th width="25%">'+math_labels.get(key,escape(key))+'</th><td colspan="3">'+value_markup+'</td></tr>'
        html+='<table width="100%">'+table_row(*rows[0])
        html+=table_row('Bravais lattice',parent['bravais'])+table_row('Point group',hm_display(parent['point_group']))
        html+=''.join(table_row(k,v) for k,v in rows[1:])+'</table>'
        if d['family']:
            html+='<p style="color:#526556;background:#edf2ec;padding:10px;"><b>Continuous family</b><br>Evaluate the matrices in Group operations. Special points may have a different classification.</p>'
        self.detail_text.setHtml(html)
        for url,image in image_resources.items():self.detail_text.document().addResource(QTextDocument.ImageResource,url,image)
        self.detail_text.document().markContentsDirty(0,self.detail_text.document().characterCount())
        self.parameter_input.clear();self.parameter_result.clear()
        self.parameter_input.setEnabled(bool(d['family']));self.evaluate_button.setEnabled(bool(d['family']))
        self.parameter_controls.setVisible(bool(d['family']));self.parameter_note.setVisible(bool(d['family']))
        self.parameter_note.setText(('Enter '+str(d['parameter_count'])+' parameter value(s) in order, e.g. 1/7, 0.81 or sqrt(2)/10. Special points may belong to a separate classification.' if d['family'] else 'This entry has no continuous parameters.'))
        if self.detail_window.isVisible():self.show_group_detail()

    def evaluate_parameters(self):
        if not self.current_detail:return
        busy=False
        try:
            from .parameter_input import parse_parameters
            values,approximate=parse_parameters(self.parameter_input.text(),self.current_detail['parameter_count'])
            QApplication.setOverrideCursor(Qt.WaitCursor);busy=True
            self.show_group_detail(values,report_errors=False,approximate=approximate);self.detail_tabs.setCurrentIndex(1)
            self.parameter_result.setText('Approximate numerical matrices.' if approximate else 'Exact matrices.')
        except Exception as exc:self.parameter_result.setText('Cannot calculate these parameters: '+str(exc))
        finally:
            if busy:QApplication.restoreOverrideCursor()

    def reset_parameters(self):
        self.parameter_input.clear();self.parameter_result.clear()
        self.show_group_detail(use_match=False)

    def copy_name(self):
        if self.current_detail:QApplication.clipboard().setText(self.current_detail['liu_latex'])

    def export_detail(self):
        if not self.current_detail:return
        path,_=QFileDialog.getSaveFileName(self.detail_window,'Export exact data',self.current_detail['xiao']+'.json','JSON (*.json)',options=QFileDialog.DontUseNativeDialog)
        if path:
            try:Path(path).write_text(json.dumps(self.current_detail,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            except (OSError,TypeError,ValueError) as exc:QMessageBox.warning(self.detail_window,'Cannot export JSON',str(exc))

    def export_results(self):
        if not self.current_filters:return
        path,_=QFileDialog.getSaveFileName(self,'Export all matching results','SSG_results.csv','CSV (*.csv)',options=QFileDialog.DontUseNativeDialog)
        if not path:return
        import csv
        with open(path,'w',encoding='utf-8-sig',newline='') as f:
            writer=None;offset=0
            while True:
                data=self.db.search(self.current_filters,limit=1000,offset=offset)
                if writer is None and data['rows']:
                    writer=csv.DictWriter(f,fieldnames=data['rows'][0]);writer.writeheader()
                if data['rows']:writer.writerows(data['rows'])
                offset+=len(data['rows'])
                if offset>=data['total']:break
        self.statusBar().showMessage('Exported all '+str(offset)+' matching results.')

    def show_help(self):
        if not hasattr(self,'guide_dialog'):
            self.guide_dialog=QDialog(self);self.guide_dialog.setWindowTitle('User Guide');self.guide_dialog.resize(850,750)
            layout=QVBoxLayout(self.guide_dialog);self.guide_browser=QTextBrowser();layout.addWidget(self.guide_browser)
        path=Path(__file__).resolve().parent/'data/USER_GUIDE.md'
        if path.is_file():self.guide_browser.setMarkdown(path.read_text(encoding='utf-8'))
        else:self.guide_browser.setPlainText('The user guide is unavailable. Search by Xiao ID or browse the classification tree.')
        self.guide_dialog.show();self.guide_dialog.raise_()

    def closeEvent(self,event):
        # Expansion ticks are queued with singleShot, so a tick can still be
        # pending when the window closes and would then query a closed database.
        self._closing=True;self.expansion_queue.clear()
        for session in list(self.detail_sessions):session.detail_window.close()
        self.db.close();super().closeEvent(event)


class DetailSession:
    """Independent detail-window state sharing only the read-only catalogue."""
    _create_detail_widgets=MainWindow._create_detail_widgets
    set_operation_filter=MainWindow.set_operation_filter
    show_group_detail=MainWindow.show_group_detail
    open_detail=MainWindow.open_detail
    evaluate_parameters=MainWindow.evaluate_parameters
    reset_parameters=MainWindow.reset_parameters
    copy_name=MainWindow.copy_name
    export_detail=MainWindow.export_detail

    def __init__(self,owner,identifier,query_match=None):
        self.owner=owner;self.detail_parent=owner;self.db=owner.db
        self.settings_store=owner.settings_store;self.current_detail=None
        self._create_detail_widgets()
        self.detail_window.finished.connect(self._closed)
        self.open_detail(identifier,query_match)
        self.show_group_detail(report_errors=False)

    def _closed(self,*_):
        if self in self.owner.detail_sessions:self.owner.detail_sessions.remove(self)
        self.detail_window.deleteLater()


def database_path():
    if getattr(sys,'frozen',False):return Path(sys._MEIPASS)/'SSGclassify.sqlite'
    return Path(__file__).resolve().parents[1]/'output/retrieval/SSGclassify.sqlite'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--database',type=Path,default=database_path())
    parser.add_argument('--smoke-test',action='store_true')
    parser.add_argument('--smoke-report',type=Path)
    parser.add_argument('--smoke-screenshot',type=Path)
    args=parser.parse_args()
    if (args.smoke_report or args.smoke_screenshot) and not args.smoke_test:
        parser.error('Diagnostic output requires --smoke-test')
    for attribute in ('AA_EnableHighDpiScaling','AA_UseHighDpiPixmaps'):
        value=getattr(Qt,attribute,None)
        if value is not None:QApplication.setAttribute(value,True)
    QLocale.setDefault(QLocale(QLocale.English))
    app=QApplication(sys.argv[:1]);app.setApplicationName('Spin Space Group Database');app.setOrganizationName('SSGclassify')

    def save_report(data):
        if args.smoke_report:
            args.smoke_report.parent.mkdir(parents=True,exist_ok=True)
            args.smoke_report.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    try:window=MainWindow(args.database)
    except Exception as exc:
        if args.smoke_test:
            save_report({'ok':False,'error':str(exc)});return 1
        QMessageBox.critical(None,'Cannot open database',str(exc));return 1
    window.show()
    if args.smoke_test:
        def verify():
            try:
                c=window.db.connection
                counts={name:c.execute('SELECT count(*) FROM '+table).fetchone()[0]
                        for name,table in [('classes','classes'),('parents','parents'),('formulas','label_formulas')]}
                if counts!={'classes':67475,'parents':230,'formulas':67475}:
                    raise ValueError('Incomplete catalogue: '+str(counts))
                window.tag_input.setText('N143.5.2');window.search_tag()
                if window.current_total!=1 or window.current_detail['xiao']!='N143.5.2':
                    raise ValueError('Xiao detail query failed')
                if window.formula.vector is None or not window.formula.vector.isValid():
                    raise ValueError('Compiled vector formula could not be rendered')
                specialized=window.db.search({'parent':1,'category':'P.1.2','bravais':'aP',
                                             'k1':'1/7,0,0','k_name':'C7'})
                matched=[row['xiao'] for row in specialized['rows']]
                if specialized['total']!=1 or matched!=['P1.5.1']:
                    raise ValueError('Specialized rational-wavevector query failed')
                window.show_group_detail(report_errors=False)
                if window.operation_table.rowCount()!=6 or window.translation_table.rowCount()!=3:
                    raise ValueError('Group operation display failed')
                window.detail_window.close()
                first=window._open_detail_session('N143.5.2');first.set_operation_filter('trivial')
                second=window._open_detail_session('N6.9.1')
                if (not first.detail_window.isVisible() or not second.detail_window.isVisible()
                        or first.current_detail['xiao']!='N143.5.2' or second.current_detail['xiao']!='N6.9.1'
                        or first.operation_filter!='trivial' or second.operation_filter!='all'):
                    raise ValueError('Independent detail windows failed')
                tooltip=first.operation_table.item(0,1).toolTip()
                if not tooltip.startswith('<pre>') or any(ch in tooltip for ch in '⎛⎜⎝'):
                    raise ValueError('Matrix tooltip is malformed')
                if MatrixDelegate.radical_depth('sqrt(2+sqrt(3))')!=2:
                    raise ValueError('Nested radical parsing failed')
                if MatrixDelegate.math_text('cos(2*pi*u0)')!='cos(2πu₀)':
                    raise ValueError('Matrix pi or parameter subscript formatting failed')
                first.detail_window.close();second.detail_window.close()
                window.show_help()
                if 'Five-level classification' not in window.guide_browser.toPlainText():
                    raise ValueError('Bundled English user guide could not be loaded')
                window.guide_dialog.close()
                if args.smoke_screenshot:
                    args.smoke_screenshot.parent.mkdir(parents=True,exist_ok=True)
                    if not window.grab().save(str(args.smoke_screenshot),'PNG'):
                        raise OSError('Could not save rendered window')
                save_report(dict(ok=True,**counts,detail='N143.5.2',vector_valid=True,independent_windows=True,
                                 matrix_tooltip_valid=True,nested_radical_valid=True,matrix_pi_subscript_valid=True,
                                 specialized_c7=matched,guide_valid=True,platform=platform.platform(),
                                 python=platform.python_version(),qt_binding=QtWidgets.__name__,
                                 frozen=bool(getattr(sys,'frozen',False)),
                                 database=str(window.db.path)))
                window.close();app.exit(0)
            except Exception as exc:
                try:save_report({'ok':False,'error':str(exc)})
                finally:window.close();app.exit(1)
        QTimer.singleShot(500,verify)
    return app.exec()


if __name__=='__main__':sys.exit(main())
