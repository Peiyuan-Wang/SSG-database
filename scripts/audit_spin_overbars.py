"""Check a display-only overbar migration against its source database."""
import argparse, hashlib, sqlite3, sys, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.rebuild_spin_overbars import correct

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous',type=Path,required=True);parser.add_argument('--current',type=Path,required=True)
    args=parser.parse_args()
    old=sqlite3.connect(args.previous.resolve().as_uri()+'?mode=ro',uri=True)
    new=sqlite3.connect(args.current.resolve().as_uri()+'?mode=ro',uri=True)
    for conn in (old,new):
        assert conn.execute('select count(*) from classes').fetchone()[0]==67475
        assert conn.execute('select count(*) from label_formulas').fetchone()[0]==67475
    columns=[x[1] for x in old.execute('pragma table_info(classes)')]
    nonlabel=','.join('"'+x+'"' for x in columns if x!='liu_latex')
    a=old.execute('select '+nonlabel+',liu_latex from classes order by id')
    b=new.execute('select '+nonlabel+',liu_latex from classes order by id')
    changed=0;total=0
    for x,y in zip(a,b):
        assert x[:-1]==y[:-1],x[0]
        assert y[-1]==correct(x[-1]),x[0]
        changed+=x[-1]!=y[-1];total+=1
    assert total==67475 and changed==3278,(total,changed)
    checked=0
    for cid,latex,digest,compressed in new.execute('select c.id,c.liu_latex,f.latex_sha256,f.svg from classes c join label_formulas f on f.class_id=c.id'):
        assert hashlib.sha256(latex.encode()).hexdigest()==digest,cid
        svg=zlib.decompress(compressed);assert b'<path' in svg and b'<image' not in svg,cid
        checked+=1
    assert checked==67475 and new.execute('pragma integrity_check').fetchone()[0]=='ok'
    for x,y in zip(old.execute('select class_id,latex_sha256,svg from label_formulas order by class_id'),
                   new.execute('select class_id,latex_sha256,svg from label_formulas order by class_id')):
        assert x[0]==y[0]
        if x[1]==y[1]:assert x[2]==y[2],x[0]
    for table in ('parents','patterns','class_patterns','charts','crystals','metadata'):
        ca=old.execute(f'select count(*) from {table}').fetchone()[0];cb=new.execute(f'select count(*) from {table}').fetchone()[0]
        assert ca==cb,(table,ca,cb)
        for x,y in zip(old.execute(f'select * from {table} order by rowid'),new.execute(f'select * from {table} order by rowid')):assert x==y,table
        print(table,ca,flush=True)
    print('classes:',total,'corrected:',changed,'formula hashes and SVG checked:',checked,flush=True)
    old.close();new.close()

if __name__=='__main__':main()
