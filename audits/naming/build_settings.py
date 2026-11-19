"""Freeze exact HM/Seitz settings. Liu Tables S3--S9 fix viewing directions.

The paper's translations are transformed by a common exact origin shift to
our existing Hall setting. Additional operations in the full HM symbol use
the lexicographically least database lift, saved explicitly.
"""
import gzip
import json
from pathlib import Path
import spglib
from sympy import ImmutableMatrix as M, Rational, cos, sin, pi, sqrt, simplify
from ssg_enumeration.database import load_standard_space_group, _database_rational
from ssg_enumeration.torus import solve_torus
from ssg_enumeration.exact import mod_vector, is_integral

ROOT = Path(__file__).resolve().parents[2]
references=json.loads((ROOT/'audits/naming/liu_operations.json').read_text())
out = {}
for number in range(1, 231):
    g, meta = load_standard_space_group(number)
    info = spglib.get_spacegroup_type(meta['hall_number'])
    words = info.international_full.split()
    positions = words[1:]
    axes = ([(1,0,0),(0,1,0),(0,0,1)] if number < 75 else
            [(0,0,1),(1,0,0),(1,1,0)] if number < 143 else
            [(0,0,1),(1,0,0),(2,1,0)] if number < 195 else
            [(1,0,0),(1,1,1),(1,1,0)])
    cart = M([[1,-Rational(1,2),0],[0,sqrt(3)/2,0],[0,0,1]]) if 143 <= number <= 194 else M.eye(3)
    c = M(meta['primitive_basis'])
    db = spglib.get_symmetry_from_database(meta['hall_number'])
    ops = [(M(r.tolist()), M([_database_rational(x) for x in t]))
           for r,t in zip(db['rotations'], db['translations'])]
    refops=[]
    for entry in references[str(number)]:
        symbol=entry['rotation_symbol']
        if symbol in ('1','-1'):
            rotation=int(symbol)*M.eye(3)
        else:
            proper_symbol=symbol.lstrip('-')
            n=2 if proper_symbol[0]=='m' else int(proper_symbol[0])
            axis=cart*M([int(x) for x in proper_symbol[-3:]])
            axis=axis/sqrt(axis.dot(axis))
            cross=M([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]])
            rc=cos(2*pi/n)*M.eye(3)+(1-cos(2*pi/n))*axis*axis.T+sin(2*pi/n)*cross
            rotation=(cart.inv()*rc*cart).applyfunc(simplify)
            if symbol.startswith(('-', 'm')): rotation=-rotation
        rp=c.inv()*rotation*c
        assert rp in g.rotations,(number,symbol,rotation)
        refops.append((rotation,M([Rational(x) for x in entry['translation']]),g.rotations.index(rp)))
    equations=M.vstack(*(M.eye(3)-g.rotations[p] for _,_,p in refops))
    rhs=M.vstack(*(g.translations[p]-c.inv()*t for _,t,p in refops))
    origins=solve_torus(equations,rhs)
    assert origins,(number,'No common origin transformation for the Liu representatives')
    origin=min((x.offset for x in origins),key=tuple)
    reference_lifts={r:mod_vector(t+c*(M.eye(3)-g.rotations[p])*origin) for r,t,p in refops}
    assert all(is_integral(c.inv()*reference_lifts[r]-g.translations[p]) for r,t,p in refops)
    atoms, layout = [], []
    for pos, word in enumerate(positions):
        # Monoclinic empty directions carry no independent generator.
        if 3 <= number <= 15 and word == '1':
            continue
        slots = []
        for token in word.split('/'):
            direction = M(axes[pos])
            improper = token.startswith('-') or token[0].isalpha()
            n = 2 if token[0].isalpha() else int(token.lstrip('-').split('_')[0])
            target_trace = 1 + 2*cos(2*pi/n)
            matches = []
            for r,t in ops:
                proper = -r if improper else r
                if proper.det() != 1 or proper.trace() != target_trace:
                    continue
                if n > 1 and proper*direction != direction:
                    continue
                if n > 2:
                    rc = cart*proper*cart.inv()
                    v = M([rc[2,1]-rc[1,2],rc[0,2]-rc[2,0],rc[1,0]-rc[0,1]])
                    if simplify(v.dot(cart*direction)) <= 0:
                        continue
                matches.append((tuple(t),r,t))
            if not matches:
                raise ValueError((number, token, direction))
            _,r,t = min(matches, key=lambda v:v[0])
            if r in reference_lifts:
                t=reference_lifts[r]
            rp, tp = c.inv()*r*c, c.inv()*t
            p = g.rotations.index(rp)
            shift = tp-g.translations[p]
            assert all(x.is_integer for x in shift)
            slots.append(len(atoms))
            atoms.append({'symbol':token,'point':p,'shift':[int(x) for x in shift],
                          'rotation':[[str(x) for x in row] for row in r.tolist()],
                          'translation':[str(x) for x in t]})
        layout.append(slots)
    reached = {0}
    while True:
        more = reached | {g.table[p][a['point']] for p in reached for a in atoms}
        if more == reached:
            break
        reached = more
    assert len(reached) == g.order, (number, reached, g.order)
    meta.update(hm=words[0]+' '+' '.join('/'.join(atoms[i]['symbol'] for i in slot) for slot in layout),
                lattice=words[0], layout=layout, atoms=atoms,
                liu_origin_shift_primitive=[str(x) for x in origin],
                liu_reference_operation_count=len(refops),
                operation_source='Liu SM Tables S3-S9, exact common origin shift; redundant full-HM operations from frozen Hall database',
                rotations=[[[str(x) for x in row] for row in r.tolist()] for r in g.rotations],
                sections=[[str(x) for x in t] for t in g.translations],
                table=g.table)
    out[str(number)] = meta
target = ROOT/'ssg_enumeration/data/naming_settings.json.gz'
target.write_bytes(gzip.compress(json.dumps(out,separators=(',',':')).encode(),mtime=0))
print('Validated and saved 230 complete HM/Seitz settings', target)
