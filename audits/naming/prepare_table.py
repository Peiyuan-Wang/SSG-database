"""Join new formal names to the unchanged old correspondence row order."""
import gzip
import json
from pathlib import Path
from ssg_enumeration import naming_setting

ROOT=Path(__file__).resolve().parents[2]
old=json.loads((ROOT/'audits/xiao_mapping/table_data.json').read_text())
new=json.loads(gzip.decompress((ROOT/'ssg_enumeration/data/ssg_names.json.gz').read_bytes()))
byid={row['id']:row for row in new['rows']}
rows=[]
for row in old['rows']:
    entry=byid[row[0]]
    assert entry['xiao']==row[4]
    assert len(entry['name']['basis'][0])==row[7]
    rows.append([entry['text'],entry['latex'],naming_setting(row[1])['hall_number']])
assert len(rows)==67475 and len({row[0] for row in rows})==67475
example=next(i+2 for i,row in enumerate(old['rows']) if row[1]==4 and row[7]>0)
(ROOT/'tmp/naming_rule/table_rows.json').write_text(json.dumps({'rows':rows,'exampleRange':f'A{example}:F{example+5}'},ensure_ascii=False))
print('Prepared',len(rows),'rows; family example at row',example)
