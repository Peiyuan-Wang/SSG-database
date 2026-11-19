"""Read saved XLSX and compare all 67,475 old and new correspondence rows."""
import json
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[2]
old=json.loads((ROOT/'audits/xiao_mapping/table_data.json').read_text())
new=json.loads((ROOT/'tmp/naming_rule/table_rows.json').read_text())
path=ROOT/'outputs/xiao_mapping/SSGclassify_Xiao_67475.xlsx'
wb=load_workbook(path,read_only=True,data_only=False)
assert wb.sheetnames==['类别汇总','逐项对应']
sheet=wb['逐项对应']
sheet.calculate_dimension(force=True)  # XLSX may legally omit the optional dimension element.
assert sheet.max_row==67476 and sheet.max_column==11
it=sheet.iter_rows(values_only=True)
header=next(it)
assert list(header[1:9])==old['headers']
for i,(actual,expected,added) in enumerate(zip(it,old['rows'],new['rows']),2):
    assert list(actual[1:9])==expected,(i,'old columns changed',actual,expected)
    assert [actual[0],actual[9],actual[10]]==added,(i,'new columns changed')
assert wb['类别汇总']['C23'].value=='=SUM(C5:C21)'
assert wb['类别汇总']['D23'].value=='=SUM(D5:D21)'
values=load_workbook(path,read_only=True,data_only=True)
assert values['类别汇总']['C23'].value==67475
assert values['类别汇总']['D23'].value==8520
import zipfile
from xml.etree import ElementTree as ET
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(path) as z:
    table_ranges=[]
    for f in z.namelist():
        if f.startswith('xl/tables/') and f.endswith('.xml'):
            root=ET.fromstring(z.read(f));table_ranges.append(root.attrib['ref'])
    assert 'A1:K67476' in table_ranges
    root=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
    pane=root.find('.//s:pane',ns)
    assert pane is not None and pane.attrib.get('ySplit')=='1' and pane.attrib.get('xSplit')=='1'
print('PASS: all 67,475 rows, original columns, formal names, formulas, totals, filter and panes')
