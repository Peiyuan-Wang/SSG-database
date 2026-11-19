"""Build-time LaTeX -> DVI -> vector SVG; no TeX installation needed at runtime."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import zlib


def _source(formulas):
    source=r'''\documentclass[multi=ssgformula,border=2pt]{standalone}
\usepackage{lmodern,amsmath,amssymb,xcolor}
\newenvironment{ssgformula}{\color[HTML]{183C55}}{}
\begin{document}
'''
    source+='\n'.join(r'\begin{ssgformula}$'+formula+r'$\end{ssgformula}' for formula in formulas)
    source+='\n'+r'\end{document}'+'\n'
    return source


def _read_vectors(directory,count):
    paths=sorted(Path(directory).glob('label-*.svg'),key=lambda p:int(p.stem.split('-')[-1]))
    if len(paths)!=count:raise ValueError('Unexpected formula page count')
    vectors=[]
    for i,path in enumerate(paths,1):
        if int(path.stem.split('-')[-1])!=i:raise ValueError('Nonconsecutive formula pages')
        raw=path.read_bytes()
        if b'<path' not in raw or b'<image' in raw or b'data:image' in raw:
            raise ValueError('Expected pure vector glyph outlines from LaTeX')
        vectors.append(raw)
    return vectors


def compile_formulas(formulas,directory):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    (directory/'labels.tex').write_text(_source(formulas))
    with (directory/'compile.log').open('w') as log:
        subprocess.run(['latex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','labels.tex'],
                       cwd=directory,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        subprocess.run(['dvisvgm','--no-fonts','--page=1-','--bbox=preview',
                        '--cache='+str(directory/'font-cache'),'--output=label-%p.svg','labels.dvi'],
                       cwd=directory,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    return _read_vectors(directory,len(formulas))


def build_formula_database(database,directory,workers=4,progress=None):
    """Compile every stored label, verify vector output, and persist atomically."""
    start=time.monotonic();database=Path(database);directory=Path(directory)
    connection=sqlite3.connect(database)
    connection.execute('CREATE TABLE IF NOT EXISTS label_formulas(class_id TEXT PRIMARY KEY,latex_sha256 TEXT,svg BLOB)')
    if 'svg' not in {row[1] for row in connection.execute('PRAGMA table_info(label_formulas)')}:
        connection.close();raise ValueError('Compile formulas into a legacy-format database before compacting it')
    groups={n:connection.execute('SELECT id,liu_latex FROM classes WHERE parent=? ORDER BY id',(n,)).fetchall()
            for n, in connection.execute('SELECT number FROM parents').fetchall()}
    count=0
    def compile_parent(number,rows):
        formulas=[f for _,f in rows]
        target=directory/f'{number:03d}'
        digest=sha256(json.dumps(formulas).encode()).hexdigest()
        marker=target/'source.sha256'
        if marker.exists() and marker.read_text()==digest:
            vectors=_read_vectors(target,len(rows))
        elif ((target/'labels.tex').exists() and (target/'labels.tex').read_text()==_source(formulas)
              and (target/'compile.log').exists() and f'{len(rows)} of {len(rows)} pages converted' in (target/'compile.log').read_text()):
            vectors=_read_vectors(target,len(rows));marker.write_text(digest)
        else:
            vectors=compile_formulas(formulas,target);marker.write_text(digest)
        return number,rows,vectors
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            jobs=[pool.submit(compile_parent,n,rows) for n,rows in groups.items()]
            for task in as_completed(jobs):
                n,rows,vectors=task.result()
                for (cid,formula),vector in zip(rows,vectors):
                    if b'<image' in vector or b'<path' not in vector:raise ValueError('Nonvector formula')
                    connection.execute('INSERT OR REPLACE INTO label_formulas VALUES(?,?,?)',
                                       (cid,sha256(formula.encode()).hexdigest(),zlib.compress(vector,9)))
                count+=len(rows)
                if progress:progress(n,len(rows),count)
        expected=connection.execute('SELECT count(*) FROM classes').fetchone()[0]
        assert count==expected==connection.execute('SELECT count(*) FROM label_formulas').fetchone()[0]
        report={'count':count,'all_vector':True,'engine':'LaTeX / DVI / dvisvgm --no-fonts',
                'seconds':round(time.monotonic()-start,3),'runtime_tex_required':False}
        connection.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',('formulas',json.dumps(report)))
        connection.commit();connection.close()
        database.with_name('formula_validation.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    except Exception:
        connection.rollback();connection.close();raise


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--database',required=True);p.add_argument('--workdir',required=True)
    p.add_argument('--workers',type=int,default=4);args=p.parse_args()
    print(build_formula_database(args.database,args.workdir,args.workers,
          lambda n,size,total:print(f'SG {n:03d}: {size} compiled; {total} total',flush=True)))
