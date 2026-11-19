"""Regenerate catalogue names that the old spin-symbol writer got wrong.

``_spin_symbol`` used a trace-only order test, so a spin rotation of order 12
matched no crystallographic order and fell back to the raw matrix string, which
then reached the displayed name. The names are precomputed at build time and
stored in ``ssg_names.json.gz`` and in the retrieval database, so fixing the
writer is not enough: both stores have to be rebuilt.

This script recomputes the name from each stored spin data (not from its text),
rewrites ``ssg_names.json.gz``, then copies a database and updates the affected
rows plus their compiled LaTeX vectors. It refuses to touch an existing target.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
from importlib.resources import files
import argparse, gzip, json, shutil, sqlite3, sys, zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ssg_database.label_svg import compile_formulas
from ssg_enumeration.naming import SSGName
from ssg_database.retrieval import _liu_latex


def rebuilt(row):
    """The row with its name and LaTeX recomputed from its own spin data."""
    name=SSGName.from_dict(row['name'],validate=False)
    return {**row,'text':name.text,'latex':name.latex,'name':name.to_dict()}


def liu_of(row):
    """The Liu-style suffix actually shown, from the rebuilt row."""
    return _liu_latex({'name':row['name'],'latex':row['latex']})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,help='Copy this database and update the stale rows')
    parser.add_argument('--output',type=Path,help='Target for the updated database')
    parser.add_argument('--names',type=Path,default=files('ssg_enumeration').joinpath('data/ssg_names.json.gz'))
    parser.add_argument('--write-names',action='store_true',help='Rewrite the names archive in place')
    parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()

    path=args.names.resolve()
    payload=json.loads(gzip.decompress(path.read_bytes()))
    stale=[r for r in payload['rows'] if 'M[' in r['text']]
    print(f'{len(stale)} stale names of {len(payload["rows"])}',flush=True)
    fixed={}
    for row in stale:
        new=rebuilt(row)
        # The spin data is the authority; the text must now be readable.
        assert 'M[' not in new['text'],new['text']
        fixed[row['id']]=new
    if args.write_names and fixed:
        rows=[fixed.get(r['id'],r) for r in payload['rows']]
        texts={}
        for row in rows:
            if row['text'] in texts: raise ValueError(('Name collision',row['id'],texts[row['text']],row['text']))
            texts[row['text']]=row['id']
        payload['rows']=rows
        path.write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0))
        print(f'Rewrote {path}',flush=True)

    if not args.database:return
    source=args.database.resolve();target=(args.output or source.with_name(source.stem+'-renamed.sqlite')).resolve()
    if target.exists():raise SystemExit(f'Refusing to overwrite {target}')
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    conn=sqlite3.connect(target)
    groups={}
    for cid,xiao,parent,text,latex,data in conn.execute('SELECT id,xiao,parent,name,liu_latex,data FROM classes ORDER BY parent,id'):
        if 'M[' not in text and 'M[' not in latex:continue
        row=fixed.get(cid)
        if row is None:
            # Fall back to the stored payload, which carries the same spin data.
            stored=json.loads(zlib.decompress(data))
            row=rebuilt({**stored,'id':cid,'xiao':xiao,'selected_chart':stored.get('source_chart',0)})
        groups.setdefault(parent,[]).append((cid,xiao,row['text'],row['latex'],row['name'],json.loads(zlib.decompress(data))))
    total=sum(map(len,groups.values()))
    print(f'Rebuilding {total} names in {len(groups)} parent groups',flush=True)
    def compile_one(parent,rows):
        return parent,rows,compile_formulas([liu_of({'name':r[4],'latex':r[3]}) for r in rows],
                                            ROOT/'tmp/spin_symbol_names'/f'{parent:03d}')
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            tasks=[pool.submit(compile_one,n,rows) for n,rows in groups.items()]
            for task in as_completed(tasks):
                parent,rows,vectors=task.result()
                for (cid,xiao,text,latex,name,payload_row),svg in zip(rows,vectors):
                    shown=liu_of({'name':name,'latex':latex})
                    payload_row['name_data']=name
                    conn.execute('UPDATE classes SET name=?,display_name=?,liu_latex=?,data=? WHERE id=?',
                                 (text,text+{'L':' · ∞m1','P':' · m1','N':''}[name['dimension']],shown,
                                  zlib.compress(json.dumps(payload_row,separators=(',',':')).encode(),6),cid))
                    conn.execute('UPDATE label_formulas SET latex_sha256=?,svg=? WHERE class_id=?',
                                 (sha256(shown.encode()).hexdigest(),zlib.compress(svg,9),cid))
                print(f'Compiled parent {parent}: {len(rows)}',flush=True)
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert conn.execute('SELECT count(*) FROM classes').fetchone()[0]==67475
        assert conn.execute('SELECT count(*) FROM classes WHERE name LIKE ?',('%M[%',)).fetchone()[0]==0
        conn.commit()
    except BaseException:
        conn.rollback();raise
    finally:conn.close()
    print(json.dumps({'changed':total,'parents':len(groups),'database':str(target)}),flush=True)


if __name__=='__main__':main()
