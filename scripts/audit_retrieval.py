"""Full read-back audit of every stored class and quotient projection."""
from collections import Counter
import argparse
from hashlib import sha256
import json
from pathlib import Path
import time
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ssg_database.retrieval import SearchDatabase,_unpack

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--database',type=Path,default=ROOT/'output/retrieval/SSGclassify.sqlite')
path=parser.parse_args().database.resolve()
db=SearchDatabase(path);c=db.connection;start=time.monotonic()
parents={n:db.parent(n)['setting'] for n in range(1,231)}
assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert c.execute('SELECT count(*),count(distinct xiao),count(distinct name) FROM classes').fetchone()[:]==(67475,67475,67475)
counts=Counter();projection_checks=0
for row in c.execute('SELECT * FROM classes'):
    d=_unpack(row['data']);r=d['crystal'];p=parents[row['parent']]
    kernel=r['kernel'];projection=r['projection'];q=r['q_table']
    assert len(q)*len(kernel)==p['point_order']
    assert kernel==[i for i,x in enumerate(projection) if x==0]
    assert len(projection)==p['point_order']
    for a in range(p['point_order']):
        for b in range(p['point_order']):
            assert projection[p['table'][a][b]]==q[projection[a]][projection[b]]
            projection_checks+=1
    if r['mode']=='finite':
        assert r['h_order']*r['q_order']==r['k_order']
        assert sorted(d['finite_profile_isomorphism'])==list(range(r['k_order']))
    else:
        assert r['mode']=='generic' and row['family']==1
    assert row['parameter_count']==len(d['name_data']['basis'][0])
    counts[row['dimension']]+=1
assert dict(counts)=={'L':1421,'P':9542,'N':56512}
assert c.execute('SELECT count(*) FROM charts').fetchone()[0]==206288
assert not c.execute('SELECT 1 FROM charts a LEFT JOIN classes b ON a.class_id=b.id WHERE b.id IS NULL LIMIT 1').fetchone()
assert not c.execute('SELECT 1 FROM classes a LEFT JOIN charts b ON a.id=b.class_id WHERE b.class_id IS NULL LIMIT 1').fetchone()
formula_count=0
if c.execute("SELECT 1 FROM sqlite_master WHERE name='label_formulas'").fetchone():
    for row in c.execute('SELECT f.class_id,f.latex_sha256,c.liu_latex FROM label_formulas f JOIN classes c ON f.class_id=c.id ORDER BY c.parent,c.id'):
        assert row[1]==sha256(row[2].encode()).hexdigest()
        svg=db.formula_svg(row[0])
        assert b'<path' in svg and b'<image' not in svg and b'data:image' not in svg
        formula_count+=1
    assert formula_count==67475
expected={
 'N.2.1':{'D2','D4','D2h','D2d','T','Th','D4h','O','Td','Oh'},
 'N.2.2':{'C2v','C4v','D2h','D2d','D4h'},
 'N.2.3':{'D2h','D4h','Th','Oh'},
}
for category,allowed in expected.items():
    observed={r[0] for r in c.execute('SELECT DISTINCT k_name FROM classes WHERE category=?',(category,))}
    assert observed<=allowed,(category,observed-allowed)
queries=[]
for filters in ({'parent':47},{'bravais':'oP','k1':'0,0,1/2'},
                {'parent':27,'bravais':'oP','category':'P.1.2','k1':'0,0,1/3','q_name':'C2'},
                {'parent':27,'bravais':'oP','category':'P.1.2','k1':'0,0,1/3','q_name':'C2 × C2'}):
    before=time.monotonic();result=db.search(filters)
    queries.append({'filters':filters,'matches':result['total'],'seconds':round(time.monotonic()-before,4)})
assert 'P27.5.2' in {r['xiao'] for r in db.search(queries[2]['filters'])['rows']}
assert 'P27.5.2' not in {r['xiao'] for r in db.search(queries[3]['filters'])['rows']}
report={'classes':67475,'parents':230,'charts':206288,'by_dimension':dict(counts),
        'latex_vector_formulas':formula_count,
        'quotient_product_equalities':projection_checks,'all_checks_passed':True,
        'seconds':round(time.monotonic()-start,3),'queries':queries,
        'database_sha256':sha256(path.read_bytes()).hexdigest()}
db.close();out=path.with_name('validation.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
