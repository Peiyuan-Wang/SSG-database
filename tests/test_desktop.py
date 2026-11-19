import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from pathlib import Path
try:
    from ssg_database.desktop import MainWindow, QApplication, Qt
    try:
        from PySide6.QtTest import QTest
    except ImportError:
        from PyQt5.QtTest import QTest
except ImportError as exc:
    raise unittest.SkipTest('Optional Qt desktop dependencies are not installed') from exc

ROOT=Path(__file__).resolve().parents[1]
DATABASE=Path(os.environ.get('SSG_TEST_DATABASE',ROOT/'output/retrieval/SSGclassify.sqlite')).resolve()


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATABASE.is_file():
            raise unittest.SkipTest('Full desktop integration requires the separately supplied SQLite database')
        cls.app=QApplication.instance() or QApplication([])
        cls.window=MainWindow(DATABASE)
        cls.window.show();cls.app.processEvents()

    @classmethod
    def tearDownClass(cls): cls.window.close()

    def test_navigation_and_search_live_in_sidebar(self):
        w=self.window;w.show_search();self.app.processEvents()
        self.assertLess(w.navigation.mapTo(w,w.navigation.rect().topRight()).x(),
                        w.results.mapTo(w,w.results.rect().topLeft()).x())
        self.assertFalse(hasattr(w,'settings_button'))
        self.assertTrue(w.tag_section.isAncestorOf(w.tag_input))

    def test_fresh_window_opens_on_browse_and_tree_arrows_follow_labels(self):
        fresh=MainWindow(DATABASE)
        try:
            self.assertEqual(fresh.navigation.currentIndex(),0)
            self.assertEqual(fresh.tree.treePosition(),1)
        finally:fresh.close()

    def test_expanding_classification_grows_sidebar_to_fit_visible_rows(self):
        from ssg_database.desktop import QHeaderView
        fresh=MainWindow(DATABASE);fresh.show();self.app.processEvents()
        try:
            fresh.workbench_split.setSizes([290,1000]);self.app.processEvents()
            initial=fresh.workbench_split.sizes()[0]
            item=fresh.tree.topLevelItem(172)
            for index in (1,0,0):
                item.setExpanded(True);self.app.processEvents()
                item=item.child(index)
            item.setExpanded(True);self.app.processEvents()
            self.assertEqual(fresh.tree.header().sectionResizeMode(1),QHeaderView.Interactive)
            self.assertGreater(fresh.workbench_split.sizes()[0],initial)
            self.assertGreaterEqual(fresh.tree.columnWidth(1),fresh.tree.sizeHintForColumn(1))
            columns=sum(fresh.tree.columnWidth(i) for i in range(3))
            self.assertGreaterEqual(fresh.tree.viewport().width(),columns)
        finally:fresh.close()

    def test_classification_columns_fill_sidebar_on_resize_and_count_toggle(self):
        from ssg_database.desktop import QAction
        fresh=MainWindow(DATABASE);fresh.show();self.app.processEvents()
        try:
            for width in (380,520):
                fresh.workbench_split.setSizes([width,900]);self.app.processEvents()
                columns=sum(fresh.tree.columnWidth(i) for i in range(3))
                self.assertLessEqual(abs(fresh.tree.viewport().width()-columns),2)
            action=next(a for a in fresh.findChildren(QAction) if a.text()=='Show counts')
            action.setChecked(False);self.app.processEvents()
            columns=sum(fresh.tree.columnWidth(i) for i in (0,1))
            self.assertLessEqual(abs(fresh.tree.viewport().width()-columns),2)
            action.setChecked(True);self.app.processEvents()
            columns=sum(fresh.tree.columnWidth(i) for i in range(3))
            self.assertLessEqual(abs(fresh.tree.viewport().width()-columns),2)
        finally:fresh.close()

    def test_k_selector_does_not_insert_duplicate_typed_values(self):
        combo=self.window.inputs['k_name'];before=combo.count()
        labels=[combo.itemText(i) for i in range(before)]
        self.assertEqual(labels.count('O'),1)
        self.assertEqual(labels.count('T'),1)
        combo.setEditText('O');combo.lineEdit().returnPressed.emit();self.app.processEvents()
        self.assertEqual(combo.count(),before)

    def test_matrix_entries_use_radicals_and_consistent_negative_fractions(self):
        from ssg_database.desktop import MatrixDelegate
        self.assertEqual(MatrixDelegate.fraction_parts('−1/2'),('−1','2'))
        self.assertEqual(MatrixDelegate.fraction_parts('-sqrt(3)/2'),('−√3','2'))
        self.assertIsNone(MatrixDelegate.fraction_parts('sqrt(3)'))
        self.assertEqual(MatrixDelegate.math_text('sqrt(3)'), '√3')

    def test_matrix_pi_and_parameter_subscripts(self):
        from ssg_database.desktop import MatrixDelegate
        self.assertEqual(MatrixDelegate.math_text('cos(2*pi*u0)'),'cos(2πu₀)')
        self.assertEqual(MatrixDelegate.math_text('-sin(2*pi*u12)'),'−sin(2πu₁₂)')
        self.assertEqual(MatrixDelegate.math_text('spin + pilot + u0'),'spin + pilot + u₀')
        self.assertEqual(MatrixDelegate.math_text('cos(4piu0) + u12'),'cos(4πu₀) + u₁₂')
        from ssg_database.desktop import QFont
        doc=MatrixDelegate.text_document('cos(4πu₀)+u₁₂',QFont('Latin Modern Math',13))
        self.assertEqual(doc.toPlainText(),'cos(4πu0)+u12')
        self.assertIn('vertical-align:sub',doc.toHtml())
        w=self.window;w.open_detail('N143.5.2');w.show_group_detail()
        entries=w.operation_table.item(2,1).data(Qt.UserRole+3)
        values=[MatrixDelegate.math_text(v) for row in entries for v in row]
        self.assertTrue(any('π' in v and 'u₀' in v for v in values),values)
        self.assertFalse(any('pi' in v or 'u0' in v for v in values),values)
        w.detail_window.close()

    def test_browse_numbers_inherit_the_classification_font(self):
        from ssg_database.desktop import Qt
        item=self.window.tree.topLevelItem(0)
        self.assertIsNone(item.data(0,Qt.FontRole))
        self.assertIsNone(item.data(1,Qt.FontRole))
        self.assertIsNone(item.data(2,Qt.FontRole))

    def test_matrix_size_hint_keeps_vertical_delimiter_clearance(self):
        from ssg_database.desktop import QTableWidget,QTableWidgetItem,QStyleOptionViewItem,MatrixDelegate,Qt
        table=QTableWidget(1,1);item=QTableWidgetItem()
        item.setData(Qt.UserRole+3,[['1','0','0'],['0','1','0'],['0','0','1']]);table.setItem(0,0,item)
        self.assertGreaterEqual(MatrixDelegate(table).sizeHint(QStyleOptionViewItem(),table.model().index(0,0)).height(),138)

    def test_group_labels_sort_and_format_special_point_groups(self):
        from ssg_database.desktop import group_display_text,math_text_markup
        combo=self.window.inputs['k_name']
        names=[combo.itemData(i) for i in range(1,combo.count())]
        self.assertLess(names.index('C2'),names.index('C12'))
        self.assertLess(names.index('C12'),names.index('D1'))
        self.assertEqual(group_display_text('Ci'),'Cᵢ')
        self.assertEqual(group_display_text('Cs'),'Cₛ')
        self.assertIn('<sub>i</sub>',math_text_markup('Cᵢ'))
        self.assertIn('<sub>s</sub>',math_text_markup('Cₛ'))
        self.assertIn('<sub>2h</sub>',math_text_markup(group_display_text('C2h')))
        self.assertNotIn('*',math_text_markup('k=(0,2*u0,0)'))
        self.assertIn('*',math_text_markup('a*b'))

    def test_operation_filter_partitions_all_group_elements(self):
        result=self.window.db.search({'text':'P1.2.1'},limit=1)
        self.assertEqual(result['total'],1)
        w=self.window;w.open_detail(result['rows'][0]['id']);w.show_group_detail(report_errors=False)
        total=w.operation_table.rowCount()
        w.set_operation_filter('trivial');trivial=w.operation_table.rowCount()
        w.set_operation_filter('nontrivial');nontrivial=w.operation_table.rowCount()
        self.assertEqual(trivial+nontrivial,total)
        w.set_operation_filter('all');self.assertEqual(w.operation_table.rowCount(),total)
        self.assertFalse(w.condition_section.isAncestorOf(w.tag_input))
        self.assertTrue(w.condition_section.isAncestorOf(w.inputs['parent']))

    def test_space_group_number_can_be_entered_or_selected(self):
        from ssg_database.desktop import SelectionPanelCombo
        w=self.window;w.clear_filters();parent=w.inputs['parent']
        self.assertIsInstance(parent,SelectionPanelCombo)
        self.assertEqual(parent.itemText(parent.findData(20)),'20')
        parent.setEditText('20');w._parent_text_finished()
        self.assertEqual(parent.currentData(),20)
        self.assertEqual(w.inputs['bravais'].currentData(),w.db.parent(20)['bravais'])
        self.assertIsInstance(w.inputs['bravais'],SelectionPanelCombo)
        self.assertIsInstance(w.inputs['point_group'],SelectionPanelCombo)
        w.run_search();self.assertEqual(w.current_filters['parent'],20)
        w.clear_filters()

    def test_selection_panel_changes_real_search_field(self):
        from ssg_database.desktop import QPushButton
        w=self.window;w.clear_filters();parent=w.inputs['parent'];parent.showPopup()
        self.app.processEvents()
        button=next(b for b in parent.panel.findChildren(QPushButton) if b.text()=='20')
        button.click();self.app.processEvents()
        self.assertEqual(parent.currentData(),20)
        self.assertEqual(w.inputs['bravais'].currentData(),w.db.parent(20)['bravais'])
        w.clear_filters()

    def test_space_group_selector_is_compact(self):
        from ssg_database.desktop import QGridLayout,QPushButton
        combo=self.window.inputs['parent'];combo.showPopup();self.app.processEvents()
        grid=combo.panel.findChild(QGridLayout)
        self.assertIsNotNone(grid)
        self.assertLessEqual(grid.columnCount(),6)
        button=next(b for b in combo.panel.findChildren(QPushButton) if b.text()=='230')
        self.assertLessEqual(button.width(),70)
        self.assertGreater(button.width(),button.fontMetrics().horizontalAdvance('230')+8)
        combo.panel.close()

    def test_tree_crystal_nodes_show_q_and_k_and_preserve_keys(self):
        from ssg_database.desktop import tree_label,math_text_markup
        w=self.window
        for xiao in ('L20.1.1','N213.12.1','N143.5.2'):
            detail=w.db.detail(xiao);path=detail['hierarchy'];crystal=detail['crystal']
            node=next(n for n in w.db.children(path[:4]) if n['value']==path[4])
            self.assertEqual(node['label'],f"Q = {crystal['q_name']}, K = {crystal['k_name']}")
            self.assertEqual(node['path'],path)
            self.assertIn(', K = ',tree_label(node))
            self.assertIn('K = ',math_text_markup(tree_label(node)))

    def test_parameter_errors_preserve_matrices_and_reset(self):
        w=self.window;w.open_detail('N143.5.2');w.show_group_detail()
        before=w.operation_table.item(2,1).text()
        w.parameter_input.setText('bad');w.evaluate_parameters()
        self.assertIn('Cannot calculate',w.parameter_result.text())
        self.assertEqual(w.operation_table.item(2,1).text(),before)
        w.reset_parameters();self.assertEqual(w.operation_table.item(2,1).text(),before)
        self.assertEqual(w.parameter_result.text(),'');w.detail_window.close()

    def test_each_row_details_opens_its_own_record(self):
        w=self.window;w.set_results({'parent':5})
        expected=w.results.item(1,7).text()
        from ssg_database.desktop import QPushButton
        button=w.results.cellWidget(1,9).findChild(QPushButton)
        self.assertEqual(button.text(),'Details');button.click();self.app.processEvents()
        session=w.detail_sessions[-1]
        self.assertTrue(session.detail_window.isVisible())
        self.assertEqual(session.current_detail['xiao'],expected)
        session.detail_window.close()

    def test_detail_session_exports_json(self):
        import json,tempfile
        from unittest.mock import patch
        w=self.window;session=w._open_detail_session('N143.5.2')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'group.json'
            with patch('ssg_database.desktop.QFileDialog.getSaveFileName',return_value=(str(path),'JSON (*.json)')) as dialog:
                session.export_detail()
            self.assertIs(dialog.call_args.args[0],session.detail_window)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['xiao'],'N143.5.2')
        session.detail_window.close()

    def test_approximate_spin_labels_follow_each_symbolic_matrix(self):
        w=self.window;w.open_detail('P40.5.4');w.show_group_detail()
        originals=[w.operation_table.item(i,4).text() for i in range(w.operation_table.rowCount())]
        w.parameter_input.setText('0.81');w.evaluate_parameters()
        labels=[w.operation_table.item(i,4).text() for i in range(w.operation_table.rowCount())]
        rows=w._all_operation_rows
        self.assertTrue(any(row['symbolic_spin'].free_symbols for row in rows))
        self.assertTrue(any(not row['symbolic_spin'].free_symbols for row in rows))
        for before,after,row in zip(originals,labels,rows):
            if row['symbolic_spin'].free_symbols:self.assertEqual(after,'Numerical matrix')
            else:self.assertEqual(after,before)
        w.detail_window.close()

    def test_detail_windows_keep_independent_filter_and_parameters(self):
        from ssg_database.desktop import Qt
        w=self.window;a=w._open_detail_session('N143.5.2')
        a.set_operation_filter('trivial')
        b=w._open_detail_session('N6.9.1');self.app.processEvents()
        self.assertTrue(a.detail_window.isVisible());self.assertTrue(b.detail_window.isVisible())
        self.assertEqual(a.current_detail['xiao'],'N143.5.2')
        self.assertEqual(b.current_detail['xiao'],'N6.9.1')
        self.assertEqual(a.operation_filter,'trivial');self.assertEqual(b.operation_filter,'all')
        self.assertTrue(a.operation_filter_buttons['trivial'].isChecked())
        self.assertTrue(b.operation_filter_buttons['all'].isChecked())
        self.assertTrue(b.detail_window.windowFlags() & Qt.WindowMaximizeButtonHint)
        self.assertTrue(b.detail_window.windowFlags() & Qt.WindowMinimizeButtonHint)
        a.detail_window.close();self.assertTrue(b.detail_window.isVisible())
        b.detail_window.close()

    def test_continuous_results_show_full_k_and_expand_columns(self):
        w=self.window;w.set_results({'text':'N3.11.17'})
        item=w.results.item(0,4)
        self.assertEqual(item.text(),w.current_detail['crystal']['k_name'])
        self.assertNotIn('…',item.text())
        self.assertGreaterEqual(w.results.columnWidth(4),w.results.sizeHintForColumn(4))
        self.assertGreaterEqual(w.results.columnWidth(2),w.results.sizeHintForColumn(2))

    def test_parameter_subscript_and_compound_radical_parts(self):
        from ssg_database.desktop import math_text_markup,MatrixDelegate
        self.assertIn('<i>u</i><sub>0</sub>',math_text_markup('k=(0,0,-2*u0)'))
        parts=MatrixDelegate.expression_parts('-sqrt(2)/4 + sqrt(6)/4')
        self.assertEqual([text for kind,text in parts if kind=='root'],['2','6'])
        self.assertEqual(MatrixDelegate.math_text('cos(u0)**2 + sin(u0)**2'),'cos(u₀)² + sin(u₀)²')
        self.assertEqual(MatrixDelegate.expression_parts('sqrt(2+sqrt(3))'),[('root','2+sqrt(3)')])

    def test_radicals_from_exact_rotations_keep_every_root(self):
        from math import lcm
        from sympy import Rational,pi,sin,cos
        from ssg_database.desktop import MatrixDelegate
        def count_roots(value):
            return sum(1+count_roots(text) for kind,text in MatrixDelegate.expression_parts(value) if kind=='root')
        phases={Rational(p,lcm(q,12)) for q in range(1,49) for p in range(lcm(q,12))}
        values={str(fn(2*pi*phase)) for phase in phases for fn in (sin,cos)}
        roots=[value for value in values if 'sqrt(' in value]
        self.assertGreater(len(roots),60)
        for value in roots:self.assertEqual(count_roots(value),value.count('sqrt('),value)
        self.assertEqual(MatrixDelegate.radical_depth('sqrt(2+sqrt(3))'),2)
        self.assertEqual(MatrixDelegate.radical_depth('sqrt(2+sqrt(2+sqrt(3)))'),3)
        from ssg_database.desktop import QFont,QFontMetricsF
        metrics=QFontMetricsF(QFont('Latin Modern Math',13))
        self.assertGreater(MatrixDelegate.matrix_cell_height([['sqrt(2+sqrt(2+sqrt(3)))']],metrics),
                           MatrixDelegate.matrix_cell_height([['sqrt(3)']],metrics))

    def test_radicals_in_catalogue_axis_labels_are_rich_text(self):
        from ssg_database.desktop import OperationDelegate
        for kind in ('2','m'):
            for sign in ('','-'):
                for divisor in ('','/3'):
                    doc=OperationDelegate.document(f'{kind}_[1,{sign}sqrt(3){divisor},0]')
                    self.assertIn('√3',doc.toPlainText())
                    self.assertIn('overline',doc.toHtml())

    def test_matrix_tooltip_has_intact_row_brackets(self):
        from ssg_database.desktop import MatrixDelegate
        entries=[['−1','0','0'],['0','−1','0'],['0','0','1']]
        text=MatrixDelegate.tooltip(entries)
        self.assertEqual(text.count('['),3);self.assertEqual(text.count(']'),3)
        self.assertNotIn('⎛',text);self.assertNotIn('⎜',text);self.assertNotIn('⎝',text)
        w=self.window;w.open_detail('P40.5.4');w.show_group_detail()
        self.assertEqual(w.operation_table.item(0,1).toolTip(),
                         MatrixDelegate.tooltip(w.operation_table.item(0,1).data(Qt.UserRole+3)))
        w.detail_window.close()

    def test_page_change_resets_vertical_scroll(self):
        w=self.window;w.set_results({'parent':3});self.app.processEvents()
        bar=w.results.verticalScrollBar();bar.setValue(bar.maximum());self.assertGreater(bar.value(),0)
        w.turn_page(1);self.app.processEvents();self.assertEqual(bar.value(),0)

    def test_detail_fields_and_reminder_layout(self):
        w=self.window;w.open_detail('N143.5.2');w.show_group_detail();w.detail_tabs.setCurrentIndex(0)
        html=w.detail_text.toHtml();text=w.detail_text.toPlainText()
        self.assertNotIn('Hall ',text)
        self.assertIn('Bravais lattice',text);self.assertIn('Point group',text)
        self.assertNotIn('Bravais lattice / point group',text)
        self.assertGreater(text.index('Continuous family'),text.index('Spin Bravais lattice'))
        self.assertIn('math://kernel',html)
        self.assertNotIn('#fff5dc',html.lower())
        self.app.processEvents()
        bravais=w.detail_text.document().find('hP')
        self.assertFalse(bravais.isNull())
        self.assertEqual(bravais.block().layout().lineCount(),1)
        w.detail_window.close()

    def test_formula_headers_and_result_name_scale_are_consistent(self):
        from ssg_database.desktop import FORMULA_SCALE, HEADER_FORMULAS, MATH_FORMULAS
        self.assertLess(FORMULA_SCALE,3.0)
        self.assertEqual(set(HEADER_FORMULAS),{3,4,5,6})
        for path in HEADER_FORMULAS.values():self.assertTrue(path.is_file())
        self.assertEqual(MATH_FORMULAS['Q'],HEADER_FORMULAS[5])
        self.assertEqual(MATH_FORMULAS['kernel'],HEADER_FORMULAS[6])

    def test_group_subscripts_are_displayed_without_changing_search_values(self):
        from ssg_database.desktop import OperationDelegate,math_text_markup
        combo=self.window.inputs['q_name'];index=combo.findData('C2')
        self.assertEqual(combo.itemText(index),'C₂')
        self.assertEqual(combo.itemData(index),'C2')
        self.assertIn('vertical-align:sub',OperationDelegate.document('C2').toHtml())
        self.assertIn('<sub>2h</sub>',math_text_markup('C2h'))
        self.assertIn('<sub>2d</sub>',math_text_markup('D2d'))
        self.assertIn('<sub>χ</sub>',math_text_markup('kχ=(0,0,1/2)'))

    def test_space_group_c2_keeps_baseline_digit_but_abstract_c2_is_subscripted(self):
        from html import escape
        from ssg_database.desktop import QTreeWidget,TreeFormulaDelegate,math_text_markup
        node=next(n for n in self.window.db.children([]) if str(n['value'])=='5')
        tree=QTreeWidget();tree.setColumnCount(3)
        item=self.window._add_node(tree,node)
        index=tree.indexFromItem(item,1)
        delegate=TreeFormulaDelegate(tree)
        self.assertEqual(item.text(1),'C2')
        self.assertEqual(delegate.markup_for('C2',index),escape('C2'))
        self.assertIn('<sub>2</sub>',math_text_markup('C2'))
        tree.close()

    def test_overbars_use_placed_lines_in_rich_text(self):
        from ssg_database.desktop import OperationDelegate,overbar_markup
        self.assertIn('text-decoration:overline',overbar_markup('P 1̅ 4̅'))
        doc=OperationDelegate.document('1̅');html=doc.toHtml()
        self.assertIn('overline',html);self.assertNotIn('̅',doc.toPlainText())

    def test_point_group_choices_keep_ids_but_typeset_overbars(self):
        w=self.window;combo=w.inputs['point_group'];position=combo.findData('-1')
        self.assertGreaterEqual(position,0)
        self.assertEqual(combo.itemText(position),'1̅')

    def test_overbar_popup_row_is_tall_enough_for_the_mark(self):
        from math import ceil
        from ssg_database.desktop import QStyleOptionViewItem,plain_math_document,OverbarDelegate
        w=self.window;combo=w.inputs['point_group'];index=combo.model().index(combo.findData('-1'),0)
        option=QStyleOptionViewItem();option.font=combo.view().font()
        doc=plain_math_document(index.data(),option.font)
        hint=OverbarDelegate(combo.view()).sizeHint(option,index)
        self.assertGreaterEqual(hint.height(),ceil(doc.size().height())+4)

    def test_q_and_k_header_formulas_both_render(self):
        try:
            from PySide6.QtCore import QRect
            from PySide6.QtGui import QImage,QPainter
        except ImportError:
            from PyQt5.QtCore import QRect
            from PyQt5.QtGui import QImage,QPainter
        for column in (4,5):
            image=QImage(150,50,QImage.Format_ARGB32);image.fill(Qt.white)
            painter=QPainter(image);self.window.results.horizontalHeader().paintSection(painter,QRect(0,0,150,50),column);painter.end()
            dark=sum(image.pixelColor(x,y).red()<100 for y in range(50) for x in range(150))
            self.assertGreater(dark,20,column)

    def test_search_sidebar_places_fields_beside_results(self):
        w=self.window;w.show_search()
        self.app.processEvents()
        self.assertEqual(w.navigation.currentIndex(),1)
        self.assertTrue(w.search_card.isVisible())
        self.assertLess(w.search_card.mapTo(w,w.search_card.rect().topRight()).x(),
                        w.results.mapTo(w,w.results.rect().topLeft()).x())

    def test_short_dropdowns_share_parent_width_and_fit_without_scrolling(self):
        w=self.window;w.show_search();w.clear_filters();self.app.processEvents()
        parent=w.inputs['parent']
        parent_text=max(parent.fontMetrics().horizontalAdvance(parent.itemText(i)) for i in range(parent.count()))
        self.assertGreaterEqual(parent.minimumWidth(),parent_text+25)
        screen_rows=max(1,(w.screen().availableGeometry().height()-80)//(parent.fontMetrics().height()+10))
        self.assertGreaterEqual(parent.maxVisibleItems(),min(18,screen_rows))
        for key in ('dimension','category'):
            combo=w.inputs[key]
            self.assertEqual(combo.minimumWidth(),parent.minimumWidth())
            self.assertEqual(combo.maxVisibleItems(),parent.maxVisibleItems())
            longest=max(combo.fontMetrics().horizontalAdvance(combo.itemText(i)) for i in range(combo.count()))
            self.assertGreaterEqual(combo.width(),longest+25)
            if combo.count()<=combo.maxVisibleItems():
                combo.showPopup();self.app.processEvents()
                self.assertEqual(combo.view().verticalScrollBar().maximum(),0,key)
                combo.hidePopup()

    def test_search_summary_describes_the_applied_query(self):
        w=self.window;w.show_search();w.clear_filters()
        w.inputs['parent'].setCurrentIndex(w.inputs['parent'].findData(5));w.run_search()
        self.assertIn('Parent space group',w.conditions_summary.text())
        self.assertIn('5',w.conditions_summary.text())
        self.assertEqual(w.conditions_count.text(),'105 results')

    def test_condition_chips_remove_applied_filters(self):
        w=self.window;w.show_search();w.clear_filters()
        w.inputs['parent'].setCurrentIndex(w.inputs['parent'].findData(5))
        w.inputs['category'].setCurrentIndex(w.inputs['category'].findData('L.0.2'))
        w.run_search();self.assertEqual(w.current_total,3)
        self.assertIn('category',w.condition_chips)
        w.condition_chips['category'].click()
        self.assertNotIn('category',w.current_filters)
        self.assertEqual(w.current_total,5)
        self.assertEqual(w.inputs['category'].currentData(),None)

    def test_tree_navigation_synchronizes_search_fields(self):
        w=self.window;w.show_browse();w.clear_filters()
        w._node_click(w.tree,w.tree.topLevelItem(4))
        self.assertEqual(w.inputs['parent'].currentData(),5)
        w.show_search();self.assertEqual(w.current_filters['parent'],'5')
        self.assertIn('parent',w.condition_chips)

    def test_tree_condition_chips_show_readable_hierarchy_labels(self):
        from ssg_database.retrieval import LEVELS
        w=self.window;path=w.db.detail('L20.1.1')['hierarchy']
        filters=dict(zip(LEVELS,path))
        spin_label=next(n['label'] for n in w.db.children(path[:3]) if n['value']==path[3])
        crystal_label=next(n['label'] for n in w.db.children(path[:4]) if n['value']==path[4])
        item=w.tree.topLevelItem(int(path[0])-1)
        for value in path[1:]:
            w._load_children(w.tree,item)
            item=next(item.child(i) for i in range(item.childCount())
                      if str((item.child(i).data(0,Qt.UserRole) or {}).get('path',[''])[-1])==str(value))
        w._node_click(w.tree,item)
        self.assertEqual(w.current_filters,filters)
        self.assertIn(spin_label,w.condition_chips['spin_bravais'].text())
        self.assertIn(crystal_label,w.condition_chips['crystal_id'].text())
        self.assertNotIn(path[3],w.condition_chips['spin_bravais'].text())
        self.assertNotIn(path[4],w.condition_chips['crystal_id'].text())
        w.condition_chips['parent'].click()
        self.assertIn(spin_label,w.condition_chips['spin_bravais'].text())
        self.assertIn(crystal_label,w.condition_chips['crystal_id'].text())
        w.condition_chips['crystal_id'].click()
        self.assertNotIn('crystal_id',w.current_filters)
        self.assertIn('spin_bravais',w.current_filters)
        self.assertGreater(w.current_total,0)

    def test_removing_last_condition_clears_results_and_selection(self):
        w=self.window;w.set_results({'parent':5})
        w.condition_chips['parent'].click()
        self.assertIsNone(w.current_filters)
        self.assertEqual(w.current_total,0)
        self.assertEqual(w.results.rowCount(),0)
        self.assertIsNone(w.current_detail)
        self.assertEqual(w.conditions_count.text(),'0 results')

    def test_sidebar_search_and_settings_are_accessible(self):
        w=self.window;w.show_search()
        self.assertIn('q_name',w.inputs);self.assertIn('kernel_name',w.inputs)
        self.assertNotIn('kernel_indices',w.inputs);self.assertNotIn('kernel_order',w.inputs)
        self.assertTrue(w.condition_section.isVisible())

    def test_detail_tracks_selection_and_empty_results(self):
        w=self.window;w.set_results({'text':'N143.5.2'})
        self.assertEqual(w.current_detail['xiao'],'N143.5.2')
        self.assertIn('N143.5.2',w.detail_title.text())
        self.assertIn(w.current_detail['category'],w.detail_text.toPlainText())
        self.assertIn(w.current_detail['crystal']['k_name'],w.detail_text.toPlainText())
        w.set_results({'text':'this-ssg-does-not-exist'})
        self.assertNotIn('N143.5.2',w.detail_title.text())
        self.assertEqual(w.detail_text.toPlainText().strip(),'')

    def test_navigation_switches_between_browse_and_search(self):
        w=self.window;w.show_browse();self.assertEqual(w.navigation.currentIndex(),0)
        w.show_search();self.assertEqual(w.navigation.currentIndex(),1)

    def test_user_guide_opens_in_english(self):
        w=self.window;w.show_help()
        self.assertTrue(w.guide_dialog.isVisible())
        self.assertIn('Five-level classification',w.guide_browser.toPlainText())
        self.assertNotRegex(w.guide_browser.toPlainText(),r'[\u4e00-\u9fff]')
        self.assertEqual((ROOT/'docs/USER_GUIDE.md').read_bytes(),(ROOT/'ssg_database/data/USER_GUIDE.md').read_bytes())
        w.guide_dialog.close()

    def test_user_facing_workbench_labels_are_english(self):
        w=self.window
        self.assertEqual([w.navigation.tabText(i) for i in range(w.navigation.count())],['Browse','Search'])
        self.assertEqual(w.tree.headerItem().text(1),'Classification')
        self.assertEqual(w.results.horizontalHeaderItem(0).text(),'Configuration')
        self.assertEqual(w.detail_tabs.tabText(1),'Group operations')

    def test_search_fields_fit_sidebar_without_horizontal_scrolling(self):
        from ssg_database.desktop import QFormLayout
        self.assertEqual(self.window.search_form.rowWrapPolicy(),QFormLayout.WrapAllRows)
        self.assertGreaterEqual(self.window.results.columnWidth(0),105)

    def test_invalid_search_message_is_english(self):
        w=self.window;w.clear_filters()
        w.inputs['parent'].setCurrentIndex(w.inputs['parent'].findData(1))
        w.inputs['k1'].setText('not-a-wavevector');w.run_search()
        self.assertTrue(w.error_label.text())
        self.assertNotRegex(w.error_label.text(),r'[\u4e00-\u9fff]')
        w.clear_filters()

    def test_parent_locks_derived_fields_and_enables_waves(self):
        w=self.window
        w.inputs['parent'].setCurrentIndex(w.inputs['parent'].findData(4))
        self.assertEqual(w.inputs['bravais'].currentData(),'mP')
        self.assertFalse(w.inputs['bravais'].isEnabled())
        self.assertEqual(w.inputs['point_group'].currentData(),'2')
        self.assertTrue(w.inputs['k1'].isEnabled())
        w.clear_filters()
        self.assertFalse(w.inputs['k1'].isEnabled())

    def test_search_opens_real_class_detail(self):
        w=self.window
        w.tag_input.setText('L1.1.1')
        w.search_tag()
        self.assertEqual(w.current_total,1)
        w.open_detail('L1.1.1')
        self.assertEqual(w.current_detail['xiao'],'L1.1.1')
        self.assertIn('1',w.detail_text.toPlainText())

    def test_tree_has_all_parents_without_directory_tab(self):
        w=self.window
        self.assertEqual(w.tree.topLevelItemCount(),230)
        self.assertEqual(w.navigation.count(),2)
        self.assertEqual([w.navigation.tabText(i) for i in range(2)],['Browse','Search'])

    def test_results_place_coplanar_before_noncoplanar(self):
        w=self.window;w.set_results({'parent':5})
        values=[w.results.item(i,0).text() for i in range(w.results.rowCount())]
        self.assertIn('Coplanar',values);self.assertIn('Noncoplanar',values)
        self.assertLess(values.index('Coplanar'),values.index('Noncoplanar'))

    def test_k_search_excludes_continuous_families(self):
        w=self.window;w.clear_filters()
        w.inputs['parent'].setCurrentIndex(w.inputs['parent'].findData(1))
        w.inputs['category'].setCurrentIndex(w.inputs['category'].findData('P.1.2'))
        w.inputs['k1'].setText('1/7,0,0')
        w.inputs['k_name'].setEditText('C7')
        w.run_search()
        self.assertEqual(w.current_total,0)
        self.assertEqual(w.current_filters['family'],0)

    def test_actual_tree_click_loads_parent_results(self):
        w=self.window;w.navigation.setCurrentIndex(0)
        item=w.tree.topLevelItem(3);w.tree.scrollToItem(item);self.app.processEvents()
        QTest.mouseClick(w.tree.viewport(),Qt.LeftButton,pos=w.tree.visualItemRect(item).center())
        self.app.processEvents()
        self.assertEqual(w.current_total,52)
        self.assertEqual(item.childCount(),3)
        self.assertTrue(item.isExpanded())

    def test_tree_leaf_and_result_selection_stay_in_sync(self):
        w=self.window;detail=w.db.detail('L3.2.5');path=detail['hierarchy']
        item=w.tree.topLevelItem(2)
        for value in path[1:]:
            w._load_children(w.tree,item)
            item=next(item.child(i) for i in range(item.childCount())
                      if str((item.child(i).data(0,Qt.UserRole) or {}).get('path',[''])[-1])==str(value))
        w._load_children(w.tree,item)
        leaf=next(item.child(i) for i in range(item.childCount()) if item.child(i).text(1)=='L3.2.5')
        w._node_click(w.tree,leaf)
        self.assertEqual(w.current_detail['xiao'],'L3.2.5')
        self.assertEqual(w.results.item(w.results.currentRow(),7).text(),'L3.2.5')
        w.detail_window.close()

    def test_formal_name_uses_precompiled_vector_glyphs(self):
        w=self.window;w.open_detail('N143.5.2')
        svg=w.db.formula_svg(w.current_detail['id'])
        self.assertIn(b'<path',svg)
        self.assertNotIn(b'<image',svg)
        self.assertTrue(w.formula.vector.isValid())

    def test_window_minimum_allows_fitting_available_desktop(self):
        available=self.window.screen().availableGeometry()
        self.assertLessEqual(self.window.minimumWidth(),available.width()-40)
        self.assertLessEqual(self.window.minimumHeight(),available.height()-60)

    def test_results_columns_follow_requested_order(self):
        w=self.window;w.set_results({'parent':5})
        self.assertEqual([w.results.horizontalHeaderItem(i).text() for i in range(10)],
                         ['Configuration','Spin-lattice type','SSG name','H','K','Q','ker ϱP','Xiao ID','Parameters','Details'])
        self.assertEqual(w.results.item(0,0).text(),'Collinear')
        self.assertTrue(w.results.item(0,7).text().startswith('L5.'))
        self.assertTrue(w.results.isColumnHidden(3))
        self.assertTrue(w.results.isColumnHidden(6))
        header=w.results.horizontalHeader()
        self.assertLess(header.visualIndex(5),header.visualIndex(4))

    def test_result_pagination_controls_page_size_and_jump(self):
        w=self.window;w.set_results({'family':1})
        self.assertEqual(w.page_size,60);self.assertGreater(w.page_jump.maximum(),1)
        w.page_size_combo.setCurrentIndex(1)
        self.assertEqual(w.page_size,120)
        w.page_jump.setValue(2);w.go_to_page()
        self.assertEqual(w.offset,120);self.assertEqual(w.page_jump.value(),2)

    def test_wavevector_validation_and_order_feedback(self):
        from ssg_database.desktop import MainWindow
        self.assertEqual(MainWindow._wavevector_error('0, 0, 1/2'),'')
        self.assertIn('three reciprocal',MainWindow._wavevector_error('0,1/2'))
        w=self.window;w.clear_filters()
        w.inputs['k2'].setText('0,0,1/2')
        self.assertIn('in order',w._validate_wavevector('k2'))
        w.inputs['k1'].setText('0,0,1/3');self.assertEqual(w._validate_wavevector('k2'),'')
        w.clear_filters()

    def test_sidebar_fit_and_compact_controls(self):
        from ssg_database.desktop import QHeaderView
        w=self.window
        self.assertTrue(w.navigation.isVisible());w.toggle_sidebar();self.assertFalse(w.navigation.isVisible())
        w.toggle_sidebar();self.assertTrue(w.navigation.isVisible())
        w.set_results({'parent':5});w.results.setColumnWidth(2,317)
        original={i:w.results.columnWidth(i) for i in range(10) if not w.results.isColumnHidden(i)}
        w.toggle_fit_columns();self.assertTrue(w.fit_columns)
        self.assertGreaterEqual(w.results.columnWidth(9),94)
        self.assertEqual(w.results.horizontalHeader().sectionResizeMode(2),QHeaderView.Fixed)
        w.toggle_fit_columns();self.assertFalse(w.fit_columns)
        self.assertEqual(original,{i:w.results.columnWidth(i) for i in original})
        w.toggle_compact_names();self.assertTrue(w.compact_names)
        self.assertTrue(all(w.results.rowHeight(r)==38 for r in range(w.results.rowCount())))
        w.toggle_compact_names()

    def test_parameter_calculation_has_no_history(self):
        w=self.window;w.open_detail('N143.5.2');w.parameter_input.setText('1/7');w.evaluate_parameters()
        self.assertIn('Exact',w.parameter_result.text())
        self.assertFalse(hasattr(w,'parameter_history_table'))
        w.detail_window.close()

    def test_result_context_menu_can_locate_classification(self):
        w=self.window;w.set_results({'text':'L5.1.1'});w.locate_current_in_tree()
        self.assertEqual(w.navigation.currentIndex(),0)
        self.assertEqual(w.tree.currentItem().text(1),'L5.1.1')

    def test_q_header_renders_compiled_formula(self):
        try:
            from PySide6.QtCore import QRect
            from PySide6.QtGui import QImage,QPainter
        except ImportError:
            from PyQt5.QtCore import QRect
            from PyQt5.QtGui import QImage,QPainter
        image=QImage(150,50,QImage.Format_ARGB32);image.fill(Qt.white)
        painter=QPainter(image)
        self.window.results.horizontalHeader().paintSection(painter,QRect(0,0,150,50),5)
        painter.end()
        dark=sum(1 for y in range(50) for x in range(150)
                 if image.pixelColor(x,y).blue()<180 and image.pixelColor(x,y).red()<100)
        self.assertGreater(dark,20)

    def test_zero_grading_uses_shared_math_font_at_larger_size(self):
        from ssg_database.desktop import QTreeWidget
        nodes=self.window.db.children(['6','N','N.0.1'])
        node=next(item for item in nodes if item['label']=='kχ=0')
        tree=QTreeWidget();tree.setColumnCount(3);item=self.window._add_node(tree,node)
        self.assertEqual(item.text(1),'kχ=0')
        self.assertEqual(item.font(1).pointSize(),16)
        self.assertIsNone(item.data(1,Qt.UserRole+1))
        tree.close()

    def test_tag_lookup_has_own_field_and_buttons(self):
        w=self.window;w.clear_filters();w.tag_input.setText('L5.2.2');w.search_tag()
        self.assertEqual(w.current_total,1)
        self.assertEqual(w.current_detail['xiao'],'L5.2.2')
        w.clear_filters()

    def test_group_detail_has_separate_window_and_exact_operation_rows(self):
        w=self.window;w.open_detail('N6.9.1');w.show_group_detail()
        self.assertTrue(w.detail_window.isVisible())
        self.assertEqual(w.operation_table.columnCount(),6)
        self.assertEqual(w.operation_table.rowCount(),5)
        self.assertIn('−1',w.operation_table.item(4,1).text())
        self.assertEqual(w.operation_table.item(0,0).text(),'T1')
        self.assertEqual(w.operation_table.item(0,4).text(),'1')
        w.detail_window.close()

    def test_spatial_operation_names_are_not_repeated_or_matrix_fallbacks(self):
        w=self.window;w.open_detail('P201.4.3');w.show_group_detail(use_match=False)
        self.assertNotIn('M[',w.current_detail['display_name'])
        self.assertEqual(w.operation_table.rowCount(),27)
        names=[w.operation_table.item(i,5).text() for i in range(3,27)]
        self.assertEqual(len(names),24)
        self.assertEqual(len(set(names)),24)
        self.assertTrue(all('| ' in name and name!='{R | 0,0,0}' for name in names))
        w.detail_window.close()

    def test_result_list_has_no_collapse_button(self):
        self.assertFalse(hasattr(self.window,'result_toggle'))

    def test_count_column_and_expansion_level_are_configurable(self):
        from ssg_database.desktop import QAction
        w=self.window
        self.assertFalse(w.tree.header().stretchLastSection())
        # Native header styles can enforce a few pixels above the requested
        # width on Windows; keep the compact count column within a tight bound.
        self.assertGreaterEqual(w.tree.columnWidth(2),55)
        self.assertLessEqual(w.tree.columnWidth(2),64)
        action=next(a for a in w.findChildren(QAction) if a.text()=='Show counts')
        action.setChecked(False);self.assertTrue(w.tree.isColumnHidden(2))
        action.setChecked(True);self.assertFalse(w.tree.isColumnHidden(2))
        w.set_expansion_level(2)
        self.assertEqual(w.tree_threshold.currentIndex(),2)
        self.assertEqual([a.isChecked() for a in w.expansion_actions],[False,False,True,False,False])
        w.set_expansion_level(4)

    def test_group_detail_includes_translation_cosets(self):
        w=self.window;w.open_detail('N1.9.4');w.show_group_detail()
        self.assertEqual(w.operation_table.rowCount(),4)
        self.assertNotIn('Representatives of K',w.operation_title.text())
        w.detail_window.close()

    def test_continuous_parameter_shows_exact_specialized_group(self):
        w=self.window;w.open_detail('N143.5.2');w.show_group_detail()
        w.parameter_input.setText('1/7');w.evaluate_parameters()
        self.assertEqual(w.operation_table.rowCount(),6)
        self.assertIn('Exact',w.parameter_result.text())
        self.assertEqual(w.detail_tabs.currentIndex(),1)
        w.reset_parameters()
        self.assertEqual(w.operation_table.rowCount(),6)
        self.assertTrue(any('u0' in w.operation_table.item(i,1).text() for i in range(3)))
        w.detail_window.close()

    def test_open_detail_updates_visible_operation_table(self):
        w=self.window;w.open_detail('N6.9.1');w.show_group_detail()
        self.assertEqual(w.operation_table.rowCount(),5)
        w.open_detail('N1.9.4')
        self.assertEqual(w.operation_table.rowCount(),4)
        w.detail_window.close()

    def test_empty_search_does_not_leave_stale_group_details(self):
        w=self.window;w.open_detail('N6.9.1');w.show_group_detail()
        w.set_results({'text':'this-ssg-does-not-exist'})
        self.assertEqual(w.current_total,0)
        self.assertFalse(w.detail_window.isVisible())
        self.assertEqual(w.operation_table.rowCount(),0)

    def test_group_button_opens_continuous_family_without_sampling(self):
        w=self.window;w.set_results({'text':'N143.5.2'})
        from ssg_database.desktop import QPushButton
        button=w.results.cellWidget(0,9).findChild(QPushButton)
        button.click();self.app.processEvents()
        session=w.detail_sessions[-1]
        self.assertTrue(session.detail_window.isVisible())
        self.assertEqual(session.operation_table.rowCount(),6)
        session.detail_window.close()

    def test_approximate_parameter_entry_has_fixed_number_of_spatial_operations(self):
        w=self.window;w.open_detail('N143.5.2');w.show_group_detail()
        for text in ('0.81','1/997','sqrt(2)/10'):
            w.parameter_input.setText(text);w.evaluate_parameters()
            self.assertIn('Approximate',w.parameter_result.text(),text)
            self.assertEqual(w.operation_table.rowCount(),6,text)
            self.assertNotIn('u0',w.operation_table.item(2,1).text())
        w.reset_parameters();self.assertIn('u0',w.operation_table.item(2,1).text())
        w.detail_window.close()

    def test_formula_cells_fit_natural_size_without_shrinking(self):
        from ssg_database.desktop import formula_renderer,formula_size
        w=self.window;w.set_results({'parent':5});self.app.processEvents()
        for row in range(w.results.rowCount()):
            svg=w.results.item(row,2).data(Qt.UserRole+1)
            size=formula_size(formula_renderer(svg))
            self.assertGreaterEqual(w.results.rowHeight(row),size.height()+12)
            self.assertGreaterEqual(w.results.columnWidth(2),size.width()+18)


if __name__=='__main__': unittest.main()
