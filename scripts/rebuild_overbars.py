"""Create a separate database with properly typeset HM rotoinversions."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
import sqlite3
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ssg_enumeration.naming import SSGName,_settings
from ssg_database.label_svg import compile_formulas
from ssg_database.retrieval import _unpack

source=ROOT/'output/retrieval/SSGclassify.sqlite'
target=ROOT/'output/retrieval/SSGclassify-redesign.sqlite'
if target.exists():raise SystemExit(f'Refusing to overwrite {target}')
shutil.copy2(source,target)
c=sqlite3.connect(target)
parents=[int(k) for k,v in _settings().items() if any(re.search(r'-\d',a['symbol']) for a in v['atoms'])]
groups={}
for parent in parents:
    rows=c.execute('SELECT id,data,liu_latex FROM classes WHERE parent=? ORDER BY id',(parent,)).fetchall()
    changed=[]
    for cid,data,old in rows:
        # The on-screen name excludes the separately recorded parameter domain.
        new=SSGName.from_dict(_unpack(data)['name_data'],validate=False).liu_latex.split(r',\quad ',1)[0]
        if old!=new:changed.append((cid,new))
    if changed:groups[parent]=changed
print('Compiling',sum(map(len,groups.values())),'names for',len(groups),'parent groups',flush=True)
def compile_one(pair):
    parent,rows=pair
    return parent,rows,compile_formulas([latex for _,latex in rows],ROOT/'tmp/redesign_overbars'/f'{parent:03d}')
try:
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks=[pool.submit(compile_one,pair) for pair in groups.items()]
        for task in as_completed(tasks):
            parent,rows,vectors=task.result()
            for (cid,latex),svg in zip(rows,vectors):
                c.execute('UPDATE classes SET liu_latex=? WHERE id=?',(latex,cid))
                c.execute('UPDATE label_formulas SET latex_sha256=?,svg=? WHERE class_id=?',
                          (sha256(latex.encode()).hexdigest(),zlib.compress(svg,9),cid))
            print('Verified',parent,len(rows),flush=True)
    assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert c.execute('SELECT count(*) FROM classes').fetchone()[0]==67475
    assert c.execute('SELECT count(*) FROM label_formulas').fetchone()[0]==67475
    c.commit()
finally:
    c.close()
report={'changed':sum(map(len,groups.values())),'parents':len(groups),'source':str(source),'database':str(target)}
target.with_name('overbars-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report),flush=True)
