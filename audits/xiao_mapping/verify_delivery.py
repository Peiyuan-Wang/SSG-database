"""Read the exported XLSX and wheel independently of their writers."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def main():
    expected = json.loads((ROOT/'audits/xiao_mapping/table_data.json').read_text())
    path = ROOT/'outputs/xiao_mapping/SSGclassify_Xiao_67475.xlsx'
    with zipfile.ZipFile(path) as book:
        strings = []
        if 'xl/sharedStrings.xml' in book.namelist():
            strings = [''.join(x.itertext()) for x in ET.fromstring(book.read('xl/sharedStrings.xml'))]
        def value(cell):
            kind = cell.attrib.get('t')
            if kind == 'inlineStr':
                return ''.join(cell.find('s:is',NS).itertext())
            raw = cell.findtext('s:v',default='',namespaces=NS)
            if kind == 's': return strings[int(raw)]
            if kind in ('str','e'): return raw
            return int(float(raw)) if raw else None
        sheet = ET.fromstring(book.read('xl/worksheets/sheet2.xml'))
        rows = [[value(cell) for cell in row] for row in sheet.findall('s:sheetData/s:row',NS)]
        assert rows[0] == expected['headers']
        assert rows[1:] == expected['rows']
        tables = [n for n in book.namelist() if n.startswith('xl/tables/') and n.endswith('.xml')]
        assert len(tables) == 1
        table = ET.fromstring(book.read(tables[0]))
        assert table.attrib['ref'] == 'A1:H67476'
        assert table.find('s:autoFilter',NS) is not None
        pane = sheet.find('s:sheetViews/s:sheetView/s:pane',NS)
        assert pane is not None and float(pane.attrib['ySplit']) == 1
        summary = ET.fromstring(book.read('xl/worksheets/sheet1.xml'))
        totals = {c.attrib['r']:value(c) for c in summary.findall('.//s:c',NS)}
        assert (totals['C23'], totals['D23']) == (67475,8520)
    wheel = ROOT/'dist/ssg_enumeration-0.3.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as package:
        assert package.read('ssg_enumeration/data/xiao_correspondence.json.gz') == (ROOT/'ssg_enumeration/data/xiao_correspondence.json.gz').read_bytes()
        assert package.read('ssg_enumeration/xiao.py') == (ROOT/'ssg_enumeration/xiao.py').read_bytes()
    report = {'excel_rows_compared':len(rows)-1,'all_eight_columns_equal':True,
              'excel_table_and_filter_verified':True,'header_freeze_verified':True,
              'summary_totals_verified':True,'wheel_embedded_data_verified':True,
              'xlsx_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()}
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
