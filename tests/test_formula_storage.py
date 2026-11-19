"""The compact formula catalogue preserves exact SVGs and legacy databases."""
import hashlib
import json
import sqlite3
import tempfile
import unittest
import zlib
from pathlib import Path

from ssg_database.retrieval import SearchDatabase


class FormulaStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'original.sqlite';self.output=self.root/'compact.sqlite'
        c=sqlite3.connect(self.source)
        c.executescript('''
          CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          INSERT INTO metadata VALUES('build','{}');
          CREATE TABLE classes(id TEXT PRIMARY KEY,parent INTEGER,liu_latex TEXT);
          CREATE TABLE label_formulas(class_id TEXT PRIMARY KEY,latex_sha256 TEXT,svg BLOB);
        ''')
        self.samples={}
        for i in range(135):
            cid=f'item-{i:03}';latex=f'P_{i}';svg=f'<svg><path d="M{i} 1"/></svg>'.encode()
            self.samples[cid]=svg
            c.execute('INSERT INTO classes VALUES(?,?,?)',(cid,1 if i<100 else 2,latex))
            c.execute('INSERT INTO label_formulas VALUES(?,?,?)',
                      (cid,hashlib.sha256(latex.encode()).hexdigest(),zlib.compress(svg)))
        c.commit();c.close()

    def tearDown(self):self.tmp.cleanup()

    def test_original_and_compacted_databases_return_identical_svg(self):
        from ssg_database.formula_storage import compact_formula_database
        original=SearchDatabase(self.source)
        self.assertEqual(original.formula_svg('item-000'),self.samples['item-000'])
        report=compact_formula_database(self.source,self.output,block_size=64)
        self.assertEqual(report['formulas'],135);self.assertEqual(report['blocks'],3)
        compact=SearchDatabase(self.output)
        for cid,svg in self.samples.items():self.assertEqual(compact.formula_svg(cid),svg,cid)
        self.assertIsNone(compact.formula_svg('not-present'))
        self.assertEqual(compact.connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertEqual(original.formula_svg('item-134'),self.samples['item-134'])
        original.close();compact.close()

    def test_source_and_existing_destination_are_never_overwritten(self):
        from ssg_database.formula_storage import compact_formula_database
        before=hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.output.write_bytes(b'keep this file')
        with self.assertRaises(FileExistsError):compact_formula_database(self.source,self.output)
        self.assertEqual(self.output.read_bytes(),b'keep this file')
        with self.assertRaises(ValueError):compact_formula_database(self.source,self.source)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),before)

    def test_missing_or_invalid_formula_rejects_without_creating_output(self):
        from ssg_database.formula_storage import compact_formula_database
        c=sqlite3.connect(self.source);c.execute("UPDATE label_formulas SET svg=? WHERE class_id='item-000'",(b'broken',));c.commit();c.close()
        with self.assertRaises(ValueError):compact_formula_database(self.source,self.output)
        self.assertFalse(self.output.exists())

    def test_missing_formula_is_rejected(self):
        from ssg_database.formula_storage import compact_formula_database
        c=sqlite3.connect(self.source);c.execute("DELETE FROM label_formulas WHERE class_id='item-000'");c.commit();c.close()
        with self.assertRaises(ValueError):compact_formula_database(self.source,self.output)
        self.assertFalse(self.output.exists())

    def test_corrupted_block_is_reported(self):
        from ssg_database.formula_storage import compact_formula_database
        compact_formula_database(self.source,self.output)
        c=sqlite3.connect(self.output);c.execute('UPDATE label_formula_blocks SET data=? WHERE id=1',(b'corrupt',));c.commit();c.close()
        db=SearchDatabase(self.output)
        try:
            with self.assertRaisesRegex(ValueError,'Corrupt formula block'):db.formula_svg('item-000')
        finally:db.close()


if __name__=='__main__':unittest.main()
