"""Copy a released database and recompile incorrectly signed spin superscripts."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
import argparse, json, re, shutil, sqlite3, sys, zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ssg_database.label_svg import compile_formulas

PATTERN=re.compile(r'(\^\{)-([346])(?=_)')
def correct(formula):
    formula=PATTERN.sub(lambda match:match.group(1)+r'\overline{'+match.group(2)+'}',formula)
    formula=re.sub(r'\\bar\{([^{}]+)\}',r'\\overline{\1}',formula)
    # Space-group symbols live at the outer level. Negative components in
    # wavevectors and spin subscripts live inside braces and must stay signed.
    result=[];depth=0;i=0
    while i<len(formula):
        ch=formula[i]
        if ch=='-' and depth==0 and i+1<len(formula) and formula[i+1] in '1346':
            result.append(r'\overline{'+formula[i+1]+'}');i+=2;continue
        result.append(ch)
        if ch=='{':depth+=1
        elif ch=='}':depth-=1
        i+=1
    return ''.join(result)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
    source=args.source.resolve();target=args.output.resolve()
    if target.exists():raise SystemExit(f'Refusing to overwrite {target}')
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    conn=sqlite3.connect(target);groups={}
    for parent,cid,old in conn.execute('SELECT parent,id,liu_latex FROM classes ORDER BY parent,id'):
        new=correct(old)
        if new!=old:groups.setdefault(parent,[]).append((cid,new))
    print(f'Compiling {sum(map(len,groups.values()))} formulas for {len(groups)} parent groups',flush=True)
    def compile_one(parent,rows):
        # This migration changes the formula set/count per parent. Keep its cache
        # separate from earlier experimental builds so stale SVG pages cannot be reused.
        return parent,rows,compile_formulas([value for _,value in rows],ROOT/'tmp/ui097_space_overbars'/f'{parent:03d}')
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            tasks=[pool.submit(compile_one,n,rows) for n,rows in groups.items()]
            for task in as_completed(tasks):
                parent,rows,vectors=task.result()
                for (cid,latex),svg in zip(rows,vectors):
                    conn.execute('UPDATE classes SET liu_latex=? WHERE id=?',(latex,cid))
                    conn.execute('UPDATE label_formulas SET latex_sha256=?,svg=? WHERE class_id=?',
                                 (sha256(latex.encode()).hexdigest(),zlib.compress(svg,9),cid))
                print(f'Compiled parent {parent}: {len(rows)}',flush=True)
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert conn.execute('SELECT count(*) FROM classes').fetchone()[0]==67475
        assert conn.execute('SELECT count(*) FROM label_formulas').fetchone()[0]==67475
        conn.commit()
    except BaseException:
        conn.rollback();raise
    finally:conn.close()
    print(json.dumps({'changed':sum(map(len,groups.values())),'parents':len(groups),'database':str(target)}),flush=True)

if __name__=='__main__':main()
