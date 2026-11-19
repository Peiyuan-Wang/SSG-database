"""Offline SQLite catalogue, five-level navigation, and exact wavevector search."""
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
import gzip
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import sqlite3
import time
import zlib

from sympy import ImmutableMatrix as M, Rational

from ssg_enumeration.crystal import (analyze_chart, affine_crystal, abstract_group_name,
                      conjugate_finite_pairs, _digest)
from ssg_enumeration.naming import _settings, _matrix, SSGName, _affine_sections
from ssg_enumeration.torus import AffineTorus, solve_torus

DIMENSIONS={'L':'Collinear','P':'Coplanar','N':'Noncoplanar'}


def hm_display(symbol):
    """Readable HM notation without changing the stored ASCII identifier."""
    import re
    symbol=re.sub(r'-(\d+)',lambda m:''.join(ch+'̅' for ch in m.group(1)),symbol)
    symbol=re.sub(r'_(\d+)',lambda m:m.group(1).translate(str.maketrans('0123456789','₀₁₂₃₄₅₆₇₈₉')),symbol)
    return ''.join(symbol.split())
LEVELS=('parent','dimension','category','spin_bravais','crystal_id')
LEVEL_NAMES=('Parent space group','Configuration','Spin-lattice type','Spin Bravais lattice','Spin crystal class')


def _json(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def _pack(x): return zlib.compress(_json(x).encode(),6)
def _unpack(x): return json.loads(zlib.decompress(x))


def bravais_type(number, lattice):
    system=('a' if number<=2 else 'm' if number<=15 else 'o' if number<=74 else
            't' if number<=142 else 'h' if number<=194 else 'c')
    return system+('R' if lattice=='R' else 'C' if lattice in 'ABC' else lattice)


def _kernel_table(table,kernel):
    index={p:i for i,p in enumerate(kernel)}
    return tuple(tuple(index[table[a][b]] for b in kernel) for a in kernel)


def _liu_latex(row):
    from ssg_enumeration.naming import SSGName
    import re
    setting=_settings()[str(row['name']['space_group'])]
    if (any(re.search(r'-\d',a['symbol']) for a in setting['atoms'])
            or re.search(r'\^\{-[346]_',row['latex'])):
        return SSGName.from_dict(row['name'],validate=False).liu_latex.split(r',\quad ',1)[0]
    main=row['latex'].split(r',\quad ',1)[0]
    prefix=r'\mathrm{'+row['name']['dimension']+r'}:\;'
    if not main.startswith(prefix): raise ValueError('Invalid formal LaTeX label')
    return main[len(prefix):]+{'L':r'\,{}^{\infty m}\!1','P':r'\,{}^{m}\!1','N':''}[row['name']['dimension']]


def _display_text(row):
    text=row['text'].split(' | ',1)[0][3:]
    return text+{'L':' · ∞m1','P':' · m1','N':''}[row['name']['dimension']]


def _pattern(chart):
    grading=chart.get('grading')
    qchi=tuple(_matrix(grading['k'])) if grading else (Rational(0),)*3
    r=chart.get('representation',{})
    if 'offset' in r:
        off,bas=_matrix(r['offset'])[:3,:],_matrix(r['basis'])[:3,:]
        kind='axial';general=r['stratum']=='general'
        # For translation equivalence, retain the image torus, not its covering.
        t=AffineTorus(off,bas)
        key=min(str(t.key),str(AffineTorus(-off,-bas).key))
        vectors=[]
    else:
        kind='discrete';general=False;off=M.zeros(3,1);bas=M.zeros(3,0)
        ts=tuple(_matrix(x) for x in r.get('translations',[]))
        vectors=sorted(set(tuple(Rational(1-ts[j][i,i],4) for j in range(3))
                           for i in range(ts[0].rows))) if ts else [(Rational(0),)*3]
        key=str(vectors)
    data={'kind':kind,'qchi':list(map(str,qchi)),'offset':list(map(str,off)),
          'basis':[[str(x) for x in row] for row in bas.tolist()],
          'vectors':[list(map(str,v)) for v in vectors],'general':general}
    return _digest((chart['label'],tuple(map(str,qchi)),key)),data


SCHEMA='''
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE parents(number INTEGER PRIMARY KEY,hm TEXT,bravais TEXT,point_group TEXT,hall INTEGER,data BLOB);
CREATE TABLE crystals(id TEXT PRIMARY KEY,mode TEXT,h_name TEXT,k_name TEXT,q_name TEXT,data BLOB);
CREATE TABLE patterns(id TEXT PRIMARY KEY,parent INTEGER,data BLOB);
CREATE TABLE class_patterns(class_id TEXT,pattern_id TEXT,PRIMARY KEY(class_id,pattern_id));
CREATE TABLE charts(parent INTEGER,chart_index INTEGER,class_id TEXT,pattern_id TEXT,data BLOB,PRIMARY KEY(parent,chart_index));
CREATE TABLE classes(id TEXT PRIMARY KEY,xiao TEXT UNIQUE,parent INTEGER,dimension TEXT,category TEXT,
 family INTEGER,parameter_count INTEGER,spin_bravais TEXT,crystal_id TEXT,h_name TEXT,k_name TEXT,
 q_name TEXT,kernel_name TEXT,kernel_order INTEGER,name TEXT,display_name TEXT,liu_latex TEXT,data BLOB);
CREATE INDEX hierarchy_idx ON classes(parent,dimension,category,spin_bravais,crystal_id);
CREATE INDEX type_idx ON classes(category,parent);
CREATE INDEX crystal_idx ON classes(crystal_id);
CREATE INDEX k_idx ON classes(k_name,q_name);
CREATE INDEX kernel_idx ON classes(kernel_name,kernel_order);
CREATE INDEX pattern_parent_idx ON patterns(parent);
CREATE INDEX pattern_class_idx ON class_patterns(pattern_id,class_id);
CREATE INDEX chart_class_idx ON charts(class_id,pattern_id);
'''


def build_database(path, source_dir, *, parents=range(1,231), progress=None):
    """Build atomically from exact exported charts; never fabricate missing rows."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    source_dir=Path(source_dir);parents=tuple(sorted(parents))
    if not parents or any(type(n) is not int or not 1<=n<=230 for n in parents):
        raise ValueError('Invalid parent selection')
    start=time.monotonic()
    names_bytes=files('ssg_enumeration').joinpath('data/ssg_names.json.gz').read_bytes()
    names=json.loads(gzip.decompress(names_bytes))['rows']
    byparent=defaultdict(list)
    for row in names: byparent[row['name']['space_group']].append(row)
    tmp=path.with_suffix('.building.sqlite')
    if tmp.exists(): tmp.unlink()
    db=sqlite3.connect(tmp);db.executescript(SCHEMA)
    registry=defaultdict(list);counts=defaultdict(int);source_hashes={}
    try:
        for number in parents:
            before=time.monotonic();setting=_settings()[str(number)]
            raw=(source_dir/f'{number:03d}.json.gz').read_bytes()
            source_hashes[str(number)]=hashlib.sha256(raw).hexdigest()
            catalogue=json.loads(gzip.decompress(raw))
            db.execute('INSERT INTO parents VALUES(?,?,?,?,?,?)',
                       (number,setting['hm'],bravais_type(number,setting['lattice']),
                        setting['point_group'],setting['hall_number'],_pack(setting)))
            # Every chart in a complete class orbit contributes its translation
            # representative. Shared restrictions join the translation orbits.
            root={};patterns={};chartpatterns={}
            def find(x):
                root.setdefault(x,x)
                while root[x]!=x:
                    root[x]=root[root[x]];x=root[x]
                return x
            for i,chart in enumerate(catalogue['charts']):
                signature,pat=_pattern(chart)
                pid=f'{number}:{_digest(pat)}'
                patterns[pid]=pat;chartpatterns[i]=(signature,pid)
            orbit_for_chart={}
            for orbit in catalogue['orbits']:
                sigs=sorted({chartpatterns[i][0] for i in orbit})
                representative=min(find(s) for s in sigs)
                for s in sigs: root[find(s)]=representative
                for i in orbit: orbit_for_chart[i]=orbit
            for pid,pat in patterns.items(): db.execute('INSERT INTO patterns VALUES(?,?,?)',(pid,number,_pack(pat)))
            for row in byparent[number]:
                ci=row['selected_chart'];chart=catalogue['charts'][ci]
                result=analyze_chart(chart,setting)
                if result['mode']=='generic':
                    original_kernel=result['kernel']
                    # Use the displayed parameters, not an unrelated raw-chart gauge.
                    name=SSGName.from_dict(row['name'],validate=False)
                    sections,_=_affine_sections(name)
                    q=name.q.row_join(name.basis)
                    ts=tuple((tuple(q[j,:]),int(2*name.grading_q[j])) for j in range(3))
                    ss=tuple((tuple(ph),eta,int(chi==-1)) for ph,eta,chi in sections)
                    result=affine_crystal(ts,ss,tuple(map(tuple,setting['table'])),2 if name.dimension=='P' else 3)
                    if result['kernel']!=original_kernel:
                        raise ArithmeticError('Displayed parameter change altered the generic kernel')
                candidates=registry[result['pair_fingerprint']]
                crystal_id=None
                certificate=None
                for cid,profile in candidates:
                    if result['mode']=='generic':equivalent=profile==result['pair']
                    else:
                        certificate=conjugate_finite_pairs(profile,result['pair'])
                        equivalent=certificate is not None
                    if equivalent: crystal_id=cid;break
                if crystal_id is None:
                    crystal_id=f"{'F' if result['mode']=='finite' else 'G'}-{result['pair_fingerprint']}-{len(candidates)+1}"
                    candidates.append((crystal_id,result['pair']))
                    if result['mode']=='finite':certificate=tuple(range(result['k_order']))
                    db.execute('INSERT INTO crystals VALUES(?,?,?,?,?,?)',
                               (crystal_id,result['mode'],result['h_name'],result['k_name'],result['q_name'],_pack(result['pair'])))
                kernel=result['kernel'];kt=_kernel_table(setting['table'],kernel)
                kernel_name=abstract_group_name(kt)
                orbit=orbit_for_chart[ci]
                sb=f'{number}:{find(chartpatterns[ci][0])}'
                result={k:v for k,v in result.items() if k!='pair'}
                payload={'name_data':row['name'],'chart':chart,'crystal':result,
                         'source_chart':ci,'source_orbit_size':len(orbit),
                         'parameter_convention':'Displayed name parameters; fixed primitive/Hall setting',
                         'finite_profile_isomorphism':certificate,
                         'profile_convention':'Finite matrices are a common spin-conjugacy representative; the isomorphism maps profile elements to the sorted image of the stored chart'}
                values=(row['id'],row['xiao'],number,row['name']['dimension'],chart['label'],
                        int(bool(row['name']['basis'][0])),len(row['name']['basis'][0]),sb,crystal_id,
                        result['h_name'],result['k_name'],result['q_name'],kernel_name,len(kernel),
                        row['text'],_display_text(row),_liu_latex(row),_pack(payload))
                db.execute('INSERT INTO classes VALUES('+','.join('?' for _ in values)+')',values)
                db.executemany('INSERT INTO class_patterns VALUES(?,?)',
                               [(row['id'],pid) for pid in sorted({chartpatterns[i][1] for i in orbit})])
                db.executemany('INSERT INTO charts VALUES(?,?,?,?,?)',
                               [(number,i,row['id'],chartpatterns[i][1],_pack(catalogue['charts'][i])) for i in orbit])
                counts['rows']+=1;counts[result['mode']]+=1
            db.commit()
            if progress: progress(number,len(byparent[number]),time.monotonic()-before)
        expected=sum(len(byparent[n]) for n in parents)
        if counts['rows']!=expected: raise ArithmeticError('Missing catalogue rows')
        if len(parents)==230 and expected!=67475: raise ArithmeticError('Incomplete full catalogue')
        audit={'schema':2,'classes':counts['rows'],'parents':len(parents),
               'finite':counts['finite'],'generic':counts['generic'],
               'crystal_profiles':db.execute('SELECT count(*) FROM crystals').fetchone()[0],
               'spin_bravais_nodes':db.execute('SELECT count(DISTINCT spin_bravais) FROM classes').fetchone()[0],
               'charts':db.execute('SELECT count(*) FROM charts').fetchone()[0],
               'seconds':round(time.monotonic()-start,3),'source_names_sha256':hashlib.sha256(names_bytes).hexdigest(),
               'source_charts_sha256':source_hashes,'exact_quotient_and_kernel_checks':True,
               'finite_class_merging':'trace-preserving group isomorphism preserving H',
               'continuous_class_merging':'equal affine H/K modules in displayed coordinates; no unproved reparameterization merges',
               'generic_scope':'1,u0,... rationally independent; rational specializations may differ'}
        db.execute('INSERT INTO metadata VALUES(?,?)',('build',_json(audit)));db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ArithmeticError('SQLite integrity failure')
        db.execute('ANALYZE');db.commit();db.close();tmp.replace(path)
        path.with_suffix('.audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
        return audit
    except Exception:
        db.close();raise


def parse_vector(text):
    if not isinstance(text,str) or len(text)>120: raise ValueError('Enter three exact rational components, e.g. 0,0,1/2')
    parts=text.strip().strip('()[]').split(',')
    if len(parts)!=3: raise ValueError('Wavevectors require three comma-separated components')
    try:
        values=[Fraction(p.strip()) for p in parts]
        if any(abs(x.numerator)>10**9 or x.denominator>10**6 for x in values): raise ValueError()
        return M([Rational(x.numerator,x.denominator) for x in values])
    except (ValueError,ZeroDivisionError):
        raise ValueError('Wavevector components must be rational, e.g. 0,0,1/2') from None


def _modvec(v): return tuple(x%1 for x in v)


def _pattern_matches(pattern, basis, kchi, waves):
    if kchi is not None and _modvec(basis.T*kchi)!=tuple(map(Rational,pattern['qchi'])): return False
    if not waves: return True
    requested=[M(_modvec(basis.T*k)) for k in waves]
    if pattern['kind']=='discrete':
        available={tuple(map(Rational,v)) for v in pattern['vectors']}
        return all(tuple(v) in available for v in requested)
    if len(requested)>1: return False
    q=requested[0]
    if pattern['general'] and all((2*x).is_integer for x in q): return False
    t=AffineTorus(M(list(map(Rational,pattern['offset']))),_matrix(pattern['basis']))
    return t.contains(q) or t.contains(-q)


class SearchDatabase:
    """Read-only database API; one connection per thread or process."""
    allowed={'parent','bravais','point_group','dimension','category','family',
             'kchi','k1','k2','k3','q_name','k_name','kernel_name','kernel_order',
             'kernel_indices','spin_bravais','crystal_id','text'}

    def __init__(self,path):
        self.path=Path(path).resolve()
        if not self.path.is_file(): raise FileNotFoundError(self.path)
        self.connection=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
        self.connection.row_factory=sqlite3.Row
        self.metadata=json.loads(self.connection.execute("SELECT value FROM metadata WHERE key='build'").fetchone()[0])
        columns={row[1] for row in self.connection.execute('PRAGMA table_info(label_formulas)')}
        if columns and not ('svg' in columns or {'block_id','position'}<=columns):
            self.connection.close();raise ValueError('Unsupported formula catalogue schema')
        self._formula_format='legacy' if 'svg' in columns else 'block' if {'block_id','position'}<=columns else 'none'

    def close(self):
        self.formula_svg.cache_clear();self._formula_block.cache_clear();self.connection.close()

    @lru_cache(maxsize=8)
    def _formula_block(self,block_id):
        from .formula_storage import decode_formula_block
        row=self.connection.execute('SELECT data FROM label_formula_blocks WHERE id=?',(block_id,)).fetchone()
        if row is None:raise ValueError('Missing formula block')
        return decode_formula_block(row[0])

    @lru_cache(maxsize=256)
    def formula_svg(self,identifier):
        """Return the precompiled vector formula; no raster or runtime TeX."""
        if self._formula_format=='none':return None
        if self._formula_format=='legacy':
            row=self.connection.execute('SELECT svg FROM label_formulas WHERE class_id=?',(identifier,)).fetchone()
            return zlib.decompress(row[0]) if row else None
        row=self.connection.execute('SELECT block_id,position FROM label_formulas WHERE class_id=?',(identifier,)).fetchone()
        if row is None:return None
        block=self._formula_block(row[0]);position=row[1]
        if type(position) is not int or not 0<=position<len(block):raise ValueError('Invalid formula block position')
        return block[position]

    def parent(self,number):
        row=self.connection.execute('SELECT * FROM parents WHERE number=?',(number,)).fetchone()
        if row is None: raise ValueError('The parent space group is not in this database')
        d=dict(row);d['setting']=_unpack(d.pop('data'));return d

    def options(self):
        result={'parents':[dict(r) for r in self.connection.execute('SELECT number,hm,bravais,point_group FROM parents ORDER BY number')]}
        for key,table in [('bravais','parents'),('point_group','parents'),('category','classes'),
                          ('q_name','classes'),('k_name','classes'),('kernel_name','classes')]:
            result[key]=[r[0] for r in self.connection.execute(f'SELECT DISTINCT {key} FROM {table} ORDER BY {key}')]
        return result

    def _where(self,filters,allow_empty=False):
        if set(filters)-self.allowed: raise ValueError('Unknown search conditions: '+','.join(sorted(set(filters)-self.allowed)))
        f={k:v for k,v in filters.items() if v is not None and str(v).strip()!=''}
        if not f and not allow_empty: raise ValueError('Enter at least one search condition')
        if 'dimension' in f and f['dimension'] not in DIMENSIONS: raise ValueError('Configuration must be L, P, or N')
        from ssg_enumeration.labels import LABELS
        if 'category' in f and f['category'] not in LABELS: raise ValueError('Unknown spin-lattice type')
        if 'category' in f and 'dimension' in f and not f['category'].startswith(f['dimension']+'.'):
            raise ValueError('Configuration conflicts with the spin-lattice type')
        if 'bravais' in f and f['bravais'] not in {'aP','mP','mC','oP','oC','oI','oF','tP','tI','hP','hR','cP','cI','cF'}:
            raise ValueError('Unknown Bravais lattice')
        if 'parent' in f:
            try: number=int(f['parent'])
            except (ValueError,TypeError): raise ValueError('Space-group number must be an integer from 1 to 230') from None
            if str(number)!=str(f['parent']) or not 1<=number<=230: raise ValueError('Space-group number must be an integer from 1 to 230')
            parent=self.parent(number)
            for key in ('bravais','point_group'):
                if key in f and f[key]!=parent[key]: raise ValueError('The parent space group conflicts with '+key+' filter')
            f['parent']=number
        if any(k in f for k in ('kchi','k1','k2','k3')) and not f.get('bravais'):
            raise ValueError('Select a Bravais lattice before entering a wavevector')
        clauses=[];args=[]
        specialize=any(k in f for k in ('k1','k2','k3')) and any(k in f for k in ('q_name','k_name','kernel_name','kernel_order','kernel_indices'))
        for key in ('parent','dimension','category','family','spin_bravais','crystal_id','q_name','k_name','kernel_name','kernel_order'):
            if key in f:
                if key in ('kernel_order','family'):
                    try: f[key]=int(f[key])
                    except (TypeError,ValueError): raise ValueError('Invalid numerical condition') from None
                    if (key=='family' and f[key] not in (0,1)) or (key=='kernel_order' and f[key]<1): raise ValueError('Invalid numerical condition')
                if not (specialize and key in ('q_name','k_name','kernel_name','kernel_order')):
                    clauses.append('c.'+key+'=?');args.append(f[key])
        for key in ('bravais','point_group'):
            if key in f: clauses.append('p.'+key+'=?');args.append(f[key])
        if 'text' in f:
            clauses.append('(c.id LIKE ? ESCAPE \'\\\' OR c.xiao LIKE ? ESCAPE \'\\\' OR c.name LIKE ? ESCAPE \'\\\')')
            value=str(f['text']).replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            args.extend(['%'+value+'%']*3)
        if 'kernel_indices' in f and 'parent' not in f: raise ValueError('Select a parent space group before specifying kernel indices')
        if 'kernel_indices' in f:
            try:
                indices=sorted({int(s.strip()) for s in str(f['kernel_indices']).split(',')})
                if any(i<0 or i>=self.parent(f['parent'])['setting']['point_order'] for i in indices): raise ValueError()
            except (TypeError,ValueError): raise ValueError('Kernel indices must be comma-separated point-operation indices of the parent group') from None
            if not specialize:
                clauses.append('c.id IN (SELECT id FROM classes WHERE kernel_order=?)');args.append(len(indices))
            f['_kernel_indices']=indices
        if any(k in f for k in ('kchi','k1','k2','k3')):
            kchi=parse_vector(f['kchi']) if 'kchi' in f else None
            waves=[parse_vector(f[k]) for k in ('k1','k2','k3') if k in f]
            parents=[f['parent']] if 'parent' in f else [r[0] for r in self.connection.execute('SELECT number FROM parents WHERE bravais=?',(f['bravais'],))]
            matches=[]
            for n in parents:
                basis=_matrix(self.parent(n)['setting']['primitive_basis'])
                for r in self.connection.execute('SELECT id,data FROM patterns WHERE parent=?',(n,)):
                    if _pattern_matches(_unpack(r['data']),basis,kchi,waves): matches.append(r['id'])
            if not matches: clauses.append('0')
            else:
                clauses.append('c.id IN (SELECT class_id FROM class_patterns WHERE pattern_id IN ('+','.join('?' for _ in matches)+'))')
                args+=matches
            f['_matching_patterns']=set(matches)
        f['_specialize']=specialize
        return ' AND '.join(clauses) or '1',args,f

    def _specialized_match(self,row,filters):
        parent=self.parent(row['parent']);setting=parent['setting']
        basis=_matrix(setting['primitive_basis'])
        requested=next(parse_vector(filters[k]) for k in ('k1','k2','k3') if k in filters)
        target=M(_modvec(basis.T*requested))
        charts=self.connection.execute('SELECT chart_index,pattern_id,data FROM charts WHERE class_id=? ORDER BY chart_index',(row['id'],))
        for source in charts:
            if source['pattern_id'] not in filters['_matching_patterns']:continue
            chart=_unpack(source['data']);rep=chart.get('representation',{})
            parameters=[()]
            if rep.get('parameter_count',0):
                off=_matrix(rep['offset'])[:3,:];bas=_matrix(rep['basis'])[:3,:]
                if bas.rank()!=bas.cols:
                    raise ValueError('The specified wavevector leaves free phases; sampling cannot establish the parameter domain')
                parameters=[]
                for sign in (1,-1):
                    for component in solve_torus(bas,sign*target-off):
                        if component.parameter_count:raise ArithmeticError('Unexpected free specialization parameters')
                        p=tuple(component.offset)
                        if p not in parameters:parameters.append(p)
            for pars in parameters:
                result=analyze_chart(chart,setting,pars if pars else None)
                kernel_name=abstract_group_name(_kernel_table(setting['table'],result['kernel']))
                actual={'h_name':result['h_name'],'q_name':result['q_name'],'k_name':result['k_name'],'kernel_name':kernel_name,
                        'kernel_order':len(result['kernel'])}
                if any(key in filters and filters[key]!=value for key,value in actual.items()):continue
                if '_kernel_indices' in filters and filters['_kernel_indices']!=result['kernel']:continue
                return {**actual,'matched_specialization':{'chart_index':source['chart_index'],
                        'parameters':[str(x) for x in pars],'chart':chart,'crystal':result,
                        'wavevectors':{k:filters[k] for k in ('kchi','k1','k2','k3') if k in filters},
                        'convention':'Parameters of this stored orbit chart; may differ from displayed-name parameters'}}
        return None

    def search(self,filters,*,limit=100,offset=0):
        if type(limit) is not int or not 1<=limit<=10000 or type(offset) is not int or offset<0: raise ValueError('Invalid pagination parameters')
        where,args,f=self._where(filters)
        base=' FROM classes c JOIN parents p ON c.parent=p.number WHERE '+where
        cols='c.id,c.xiao,c.parent,c.dimension,c.category,c.family,c.spin_bravais,c.crystal_id,c.h_name,c.k_name,c.q_name,c.kernel_name,c.kernel_order,c.display_name,c.liu_latex'
        if f['_specialize']:
            rows=[]
            for r in self.connection.execute('SELECT '+cols+base+" ORDER BY c.parent,CASE c.dimension WHEN 'L' THEN 0 WHEN 'P' THEN 1 ELSE 2 END,c.category,c.id",args):
                row=dict(r);match=self._specialized_match(row,f)
                if match is not None:row.update(match);rows.append(row)
            return {'total':len(rows),'rows':rows[offset:offset+limit],'offset':offset,'limit':limit}
        if '_kernel_indices' in f:
            # Exact subgroup membership, rather than just an abstract group name.
            candidates=self.connection.execute('SELECT '+cols+',c.data'+base+" ORDER BY c.parent,CASE c.dimension WHEN 'L' THEN 0 WHEN 'P' THEN 1 ELSE 2 END,c.category,c.id",args)
            allrows=[]
            for r in candidates:
                if _unpack(r['data'])['crystal']['kernel']==f['_kernel_indices']:
                    d=dict(r);d.pop('data');allrows.append(d)
            return {'total':len(allrows),'rows':allrows[offset:offset+limit],'offset':offset,'limit':limit}
        total=self.connection.execute('SELECT count(*)'+base,args).fetchone()[0]
        rows=[dict(r) for r in self.connection.execute('SELECT '+cols+base+" ORDER BY c.parent,CASE c.dimension WHEN 'L' THEN 0 WHEN 'P' THEN 1 ELSE 2 END,c.category,c.id LIMIT ? OFFSET ?",args+[limit,offset])]
        return {'total':total,'rows':rows,'offset':offset,'limit':limit}

    def children(self,path):
        if len(path)>5: raise ValueError('Invalid hierarchy path')
        filters=dict(zip(LEVELS,path))
        if len(path)==5: return self.search(filters,limit=10000)['rows']
        column=LEVELS[len(path)]
        where,args,_=self._where(filters,allow_empty=True)
        rows=self.connection.execute(f'SELECT c.{column} AS value,count(*) AS count,min(c.id) AS example FROM classes c JOIN parents p ON c.parent=p.number WHERE '+where+f' GROUP BY c.{column} ORDER BY c.{column}',args)
        result=[]
        if column=='dimension':
            rows=sorted(rows,key=lambda r: {'L':0,'P':1,'N':2}[r['value']])
        for r in rows:
            value=str(r['value']);label=value
            if column=='parent': label=f"{value}  {hm_display(self.parent(int(value))['hm'])}"
            elif column=='dimension': label=DIMENSIONS[value]
            elif column=='spin_bravais':
                label=self.hierarchy_label(column,value,example=r['example'])
            elif column=='crystal_id':
                label=self.hierarchy_label(column,value)
            result.append({'level':len(path)+1,'value':value,'label':label,'count':r['count'],'path':list(path)+[value]})
        return result

    def hierarchy_label(self,column,value,*,filters=None,example=None):
        """Describe an internal hierarchy key using the same labels as the tree."""
        if column=='crystal_id':
            row=self.connection.execute('SELECT q_name,k_name FROM crystals WHERE id=?',(value,)).fetchone()
            return f"Q = {row['q_name']}, K = {row['k_name']}" if row else 'Unavailable'
        if column!='spin_bravais':raise ValueError('Unsupported hierarchy level')
        if example is not None:
            row=self.connection.execute('SELECT data FROM classes WHERE id=?',(example,)).fetchone()
        else:
            conditions=['spin_bravais=?'];args=[value]
            for key in ('parent','dimension','category'):
                if filters and key in filters:
                    conditions.append(key+'=?');args.append(filters[key])
            row=self.connection.execute('SELECT data FROM classes WHERE '+' AND '.join(conditions)+' ORDER BY id LIMIT 1',args).fetchone()
        if row is None:return 'Unavailable'
        payload=_unpack(row['data'])
        return self._wave_description(payload['name_data'],payload.get('chart'))

    @staticmethod
    def _wave_description(d,chart=None):
        from ssg_enumeration.naming import _affine_text
        setting=_settings()[str(d['space_group'])];c=_matrix(setting['primitive_basis'])
        pieces=[]
        if any(Rational(x) for x in d['grading_q']): pieces.append('kχ='+_affine_text(c.inv().T*M(list(map(Rational,d['grading_q']))),M.zeros(3,0)))
        if d['translation_kind']=='axial': pieces.append('k='+_affine_text(c.inv().T*M(list(map(Rational,d['q']))),c.inv().T*_matrix(d['basis'])))
        elif d['translation_kind']=='discrete':
            rep=(chart or {}).get('representation',{})
            vectors=rep.get('wavevectors',[])
            if vectors:
                pieces.extend('k'+str(i).translate(str.maketrans('123','₁₂₃'))+'='+_affine_text(c.inv().T*_matrix(v),M.zeros(3,0))
                              for i,v in enumerate(vectors,1))
            else:
                # A missing representation is not evidence that all waves vanish.
                pieces.append('Wavevector data unavailable')
        return '; '.join(pieces) or ('kχ=0' if d['dimension'] in ('L','N') else 'k=0')

    def detail(self,identifier):
        r=self.connection.execute('SELECT * FROM classes WHERE id=? OR xiao=? OR name=?',(identifier,identifier,identifier)).fetchone()
        if r is None: raise KeyError('Classification not found')
        row=dict(r);payload=_unpack(row.pop('data'));row.update(payload)
        profile=self.connection.execute('SELECT data FROM crystals WHERE id=?',(row['crystal_id'],)).fetchone()
        row['crystal']['pair']=_unpack(profile[0])
        row['parent_info']=self.parent(row['parent'])
        row['hierarchy']=[str(row[k]) for k in LEVELS]
        row['wave_description']=self._wave_description(row['name_data'],row.get('chart'))
        row['kernel_rotations']=[row['parent_info']['setting']['rotations'][p] for p in row['crystal']['kernel']]
        return row

    def evaluate(self,identifier,parameters):
        from ssg_enumeration.crystal import specialize_affine
        row=self.detail(identifier)
        if not row['family']: return row['crystal']
        pars=tuple(Rational(str(x)) for x in parameters)
        d=row['name_data'];name=SSGName.from_dict(d,validate=False)
        if len(pars)!=name.parameter_count: raise ValueError('Incorrect number of continuous parameters')
        q=name.q+name.basis*M(pars)
        if name.general and all((2*x).is_integer for x in q): raise ValueError('This value is an excluded special point; search for the corresponding discrete classification')
        result=row['crystal']
        ts=tuple((tuple(map(Rational,ph)),b) for ph,b in result['translations'])
        ss=tuple((tuple(map(Rational,ph)),e,b) for ph,e,b in result['sections'])
        return specialize_affine(ts,ss,tuple(map(tuple,row['parent_info']['setting']['table'])),pars,2 if row['dimension']=='P' else 3)


def main():
    import argparse
    p=argparse.ArgumentParser(description='Build the offline SSG database')
    p.add_argument('--output',required=True);p.add_argument('--source',required=True)
    p.add_argument('--parents',default='')
    args=p.parse_args()
    selection=[int(n) for n in args.parents.split(',')] if args.parents else range(1,231)
    audit=build_database(args.output,args.source,parents=selection,
                         progress=lambda n,c,s:print(f'SG {n:03d}: {c} classes; {s:.2f}s',flush=True))
    print(json.dumps(audit,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
