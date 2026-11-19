"""Compare every formula and every non-formula table against the source."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ssg_database.retrieval import SearchDatabase

def audit(source,destination):
    start=time.monotonic();old=SearchDatabase(source);new=SearchDatabase(destination)
    try:
        if old._formula_format!='legacy' or new._formula_format!='block':raise ValueError('Unexpected formula formats')
        if new.connection.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Integrity check failed')
        tables={'parents':'number','classes':'id','charts':'parent,chart_index',
                'patterns':'id','class_patterns':'class_id,pattern_id','crystals':'id','metadata':'key'}
        counts={}
        for table,order in tables.items():
            # Include all columns, including the exact compressed representations.
            a=old.connection.execute('SELECT * FROM '+table+' ORDER BY '+order)
            b=new.connection.execute('SELECT * FROM '+table+' ORDER BY '+order)
            n=0
            while True:
                x=a.fetchone();y=b.fetchone()
                if x is None and y is None:break
                if x is None or y is None or tuple(x)!=tuple(y):raise ValueError('Table mismatch: '+table)
                n+=1
            counts[table]=n
        n=0
        rows=old.connection.execute('SELECT c.id,f.latex_sha256 FROM classes c JOIN label_formulas f ON f.class_id=c.id ORDER BY c.parent,c.id')
        for cid,digest in rows:
            other=new.connection.execute('SELECT latex_sha256 FROM label_formulas WHERE class_id=?',(cid,)).fetchone()
            if other is None or other[0]!=digest or old.formula_svg(cid)!=new.formula_svg(cid):
                raise ValueError('Formula mismatch: '+cid)
            n+=1
        if n!=counts['classes'] or n!=new.connection.execute('SELECT count(*) FROM label_formulas').fetchone()[0]:
            raise ValueError('Formula count mismatch')
        return {'tables':counts,'formula_bytes_exact':n,'integrity':'ok','seconds':round(time.monotonic()-start,2)}
    finally:old.close();new.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('destination');args=p.parse_args()
    print(json.dumps(audit(args.source,args.destination),indent=2))
