"""Match published Xiao representatives to the independently enumerated charts.

Source matrices are evaluated in ISO-IR conventional coordinates, transported
to our primitive setting, then normalized in spin space. Phase recovery is
checked on a specified rational grid, and torus membership uses integer
arithmetic. Numeric orthogonal bases are not asserted to be symbolic witnesses.
"""
import argparse
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import permutations, product
import json
from pathlib import Path
import time

import numpy as np
from sympy import ImmutableMatrix as M, Rational as Q, sympify

from ssg_enumeration.exact import is_integral
from ssg_enumeration.torus import annihilator, solve_torus

DEN = 144 * 101
PARAM = np.array([1, 3, 7], dtype=float) / 101
TOL = 2e-8


def mat(blob):
    return M(blob['entries'])


def rational_grid(values):
    values = np.asarray(values)
    integers = np.rint(values * DEN).astype(np.int64)
    if np.max(np.abs(values * DEN - integers), initial=0) > 1e-6:
        raise ValueError('Recovered phase is not on the certified rational grid')
    return integers % DEN


def signed_key(matrices):
    a = np.rint(matrices).astype(np.int8)
    if np.max(np.abs(a-matrices)) > TOL:
        raise ValueError('Expected signed monomial matrices')
    d = a.shape[1]
    keys = []
    for perm in permutations(range(d)):
        b = a[:, perm, :][:, :, perm]
        for tail in product((-1, 1), repeat=d-1):
            signs = np.array((1,)+tail, dtype=np.int8)
            keys.append(tuple((b*signs[:, None]*signs[None, :]).reshape(-1).tolist()))
    return min(keys)


def grade_key(k, bits):
    return tuple(k)+tuple(bits)


class ParentMatcher:
    def __init__(self, number, source, catalogue):
        self.number = number
        self.source = source
        self.data = catalogue
        self.parameters = PARAM.copy()
        self.pir_cache = {}
        self.constants = np.array([float(sympify(x)) for x in source['ExactConstantTable']])
        self.pirs = {k.split(':', 1)[1]:v for k,v in source['PIRRecords'].items()
                     if k.startswith(str(number)+':')}
        self.rows = {k:v for k,v in source['XiaoRecords'].items()
                     if v['ParentSpaceGroup'] == number}
        self.group_order = catalogue['parent']['point_order']
        self.B = M(catalogue['parent']['primitive_basis'])
        self.rotations = [mat(x) for x in catalogue['parent']['rotations']]
        self.sections = [mat(x) for x in catalogue['parent']['sections']]
        self._align()
        self.chart_orbit = {i:o for o,orbit in enumerate(catalogue['orbits']) for i in orbit}
        self.simple = {}
        self.phase = defaultdict(list)
        self._index()

    def _align(self):
        first = next(iter(self.pirs.values()))
        raw = [M(op['AugmentedMatrix']) for op in first['Operators']]
        ops = [a/a[3,3] for a in raw]
        self.source_ops = ops
        self.Bs = M.hstack(*(M(v[:3])/v[3] for v in first['PrimitiveTranslations']))
        self.Tchange = self.Bs.inv()*self.B
        if not is_integral(self.Tchange):
            raise ValueError('Primitive translation lattices do not agree')
        inverse = self.B.inv()
        source_rotations = [inverse*a[:3,:3]*self.B for a in ops]
        indices = []
        lhs, rhs = [], []
        for r,t in zip(self.rotations, self.sections):
            candidates = [j for j,rs in enumerate(source_rotations) if rs == r]
            if not candidates:
                raise ValueError('Conventional axes need an additional setting transformation')
            j = candidates[0]
            indices.append(j)
            lhs.append(M.eye(3)-r)
            rhs.append(t-inverse*ops[j][:3,3])
        solutions = solve_torus(M.vstack(*lhs), M.vstack(*rhs))
        if not solutions:
            raise ValueError('No origin shift aligns the source sections')
        y = solutions[0].offset
        self.origin = self.B*y
        self.section_source_indices = indices
        self.section_corrections = []
        for r,t,j in zip(self.rotations,self.sections,indices):
            delta = self.Bs.inv()*(self.B*(t-(M.eye(3)-r)*y)-ops[j][:3,3])
            if not is_integral(delta):
                raise ArithmeticError('Nonintegral section correction')
            self.section_corrections.append(tuple(map(int,delta)))

    def _translation(self, pir, vector):
        d = pir['Dimension']
        count = pir['PMKCount']
        width = d//count
        t = np.array(vector[:3], dtype=float)/vector[3]
        result = np.zeros((d,d))
        for block, kv in enumerate(pir['KVectors']):
            k = np.array(kv[0][:3], dtype=float)/kv[0][3]
            for j in range(3):
                if kv[j+1][3]:
                    k += self.parameters[j]*np.array(kv[j+1][:3])/kv[j+1][3]
            phase = 2*np.pi*np.dot(k,t)
            start = block*width
            result[start:start+width,start:start+width] = np.eye(width)*np.cos(phase)
            for j in range(width//2):
                result[start+j,start+width//2+j] = np.sin(phase)
                result[start+width//2+j,start+j] = -np.sin(phase)
        return result

    def pir_matrices(self, name):
        if name in self.pir_cache:
            return self.pir_cache[name]
        pir = self.pirs[name]
        raw_t = [self._translation(pir,v) for v in pir['PrimitiveTranslations']]
        def translation(coeffs):
            out = np.eye(pir['Dimension'])
            for a,n in zip(raw_t,coeffs):
                out = out@np.linalg.matrix_power(a,int(n))
            return out
        ts = [translation(self.Tchange[:,j]) for j in range(3)]
        ss = []
        for j,delta in zip(self.section_source_indices,self.section_corrections):
            op = pir['Operators'][j]
            aug = M(op['AugmentedMatrix']); aug = aug/aug[3,3]
            if aug != self.source_ops[j]:
                raise ValueError('PIR operation lists are not aligned')
            a = self.constants[np.array(op['PointMatrixCodes'])]
            if not pir['KSpecial']:
                a = self._translation(pir, op['IRTranslation'])@a
            ss.append(translation(delta)@a)
        self.pir_cache[name] = np.array(ts+ss)
        return self.pir_cache[name]

    def _put(self, key, chart):
        orbit = self.chart_orbit[chart]
        old = self.simple.get(key)
        if old is not None and old != orbit:
            raise ValueError('Distinct computed classes have the same normalization key')
        self.simple[key] = orbit

    def _index(self):
        phase_groups = {}
        constraints = {}
        representation_cache = {}
        for chart in self.data['charts']:
            i = chart['chart']; dim = chart['dimension']
            gd = chart.get('grading')
            gkey = None if gd is None else grade_key(
                tuple(int(2*x) for x in mat(gd['k'])),gd['section_bits'])
            if dim == 'Collinear':
                self._put(('L',gkey),i); continue
            r = chart['representation']
            prefix = 'P' if dim == 'Coplanar' else 'N'
            if prefix == 'N' and r['kind'] == 'type0':
                self._put((prefix,gkey,'zero',tuple(r['kernel'])),i)
            elif 'eta' not in r:
                raw = tuple(tuple(tuple(row) for row in m['entries'])
                            for m in r['translations']+r['sections'])
                if raw not in representation_cache:
                    representation_cache[raw] = signed_key(np.array(raw,dtype=float))
                self._put((prefix,gkey,'monomial',representation_cache[raw]),i)
            else:
                raw = ('phase',tuple(tuple(x) for x in r['basis']['entries']),
                       tuple(x[0] for x in r['offset']['entries']))
                if raw not in representation_cache:
                    basis = mat(r['basis']); off = mat(r['offset'])
                    bkey = (basis.shape,tuple(basis))
                    if bkey not in constraints:
                        constraints[bkey] = annihilator(basis)
                    c = constraints[bkey]
                    constant = c*off
                    target = tuple(int(x*DEN)%DEN for x in constant)
                    if not all((x*DEN).is_integer for x in constant):
                        raise ValueError('Catalogue denominator outside the phase grid')
                    representation_cache[raw] = (bkey,np.array(c).astype(np.int64),target)
                bkey,c,target = representation_cache[raw]
                key = (prefix,gkey,tuple(r['eta']),r['stratum'],bkey)
                if key not in phase_groups:
                    phase_groups[key] = (c,{})
                table = phase_groups[key][1]
                orbit = self.chart_orbit[i]
                for sign in (1,-1):
                    signed_target = tuple(sign*x%DEN for x in target)
                    old = table.get(signed_target)
                    if old is not None and old != orbit:
                        raise ValueError('Duplicate phase chart orbit')
                    table[signed_target] = orbit
        for key, value in phase_groups.items():
            self.phase[key[:4]].append(value)

    def match(self, label, alternative=0):
        row = self.rows[label]
        names = row['Alternatives'][alternative]['Constituents']
        blocks = [self.pir_matrices(name) for name in names]
        d = sum(a.shape[1] for a in blocks)
        matrices = np.zeros((self.group_order+3,d,d))
        start = 0
        for a in blocks:
            size = a.shape[1];matrices[:,start:start+size,start:start+size] = a;start += size
        if np.max(np.abs(matrices.transpose(0,2,1)@matrices-np.eye(d))) > TOL:
            raise ValueError('Source representation is not orthogonal')
        prefix = label[0]
        if prefix == 'L':
            bits = np.rint((1-matrices[:,0,0])/2).astype(int)
            return self.simple.get(('L',grade_key(bits[:3],bits[3:])))
        if prefix == 'N':
            signs = np.rint(np.linalg.det(matrices)).astype(int)
            bits = (1-signs)//2
            gkey = grade_key(bits[:3],bits[3:])
            matrices = matrices*signs[:,None,None]
        else:
            gkey = None
        ts, ss = matrices[:3],matrices[3:]
        identity_translations = np.max(np.abs(ts-np.eye(d))) < TOL
        if prefix == 'N' and identity_translations:
            kernel = tuple(np.where(np.max(np.abs(ss-np.eye(d)),axis=(1,2)) < TOL)[0].tolist())
            return self.simple.get((prefix,gkey,'zero',kernel))
        if d == 3:
            rank = np.linalg.matrix_rank(np.concatenate([a-np.eye(3) for a in ts]),tol=TOL)
            if rank == 3:
                _, basis = np.linalg.eigh(ts[0]+2*ts[1]+4*ts[2])
                canonical = basis.T@matrices@basis
                return self.simple.get((prefix,gkey,'monomial',signed_key(canonical)))
            if rank != 2:
                raise ValueError('Unexpected SO(3) translation fixed-space dimension')
            _,_,vh = np.linalg.svd(np.concatenate([a-np.eye(3) for a in ts]))
            axis = vh[-1]
            unit = np.eye(3)[np.argmin(abs(axis))]
            e1 = unit-axis*np.dot(axis,unit);e1 /= np.linalg.norm(e1)
            e2 = np.cross(axis,e1)
            basis = np.column_stack((e1,e2,axis))
            canonical = basis.T@matrices@basis
            if np.max(abs(canonical[:,:2,2])) > TOL or np.max(abs(canonical[:,2,:2])) > TOL:
                raise ValueError('Point operations do not preserve the spin axis')
            plane = canonical[:,:2,:2]
        else:
            if np.any(np.linalg.det(ts) < 0):
                _, basis = np.linalg.eigh(ts[0]+2*ts[1]+4*ts[2])
                return self.simple.get((prefix,gkey,'monomial',signed_key(basis.T@matrices@basis)))
            plane = matrices
        eta = tuple(np.rint(np.linalg.det(plane[3:])).astype(int).tolist())
        angles = np.arctan2(plane[:,1,0],plane[:,0,0])/(2*np.pi)
        if -1 in eta:
            pivot = angles[3+eta.index(-1)]
            for j,e in enumerate(eta):
                if e == -1:angles[3+j] -= pivot
        x = rational_grid(angles)
        q = x[:3]
        stratum = 'zero' if not any(q) else 'trim' if all((2*q)%DEN == 0) else 'general'
        found = set()
        for c, table in self.phase.get((prefix,gkey,eta,stratum),[]):
            orbit = table.get(tuple((c@x%DEN).tolist()))
            if orbit is not None:found.add(orbit)
        if len(found)>1:
            raise ValueError('Source matches multiple computed classes')
        return next(iter(found)) if found else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--catalogues',type=Path,default=Path('recomputed_results/full_export_230_20261029'))
    parser.add_argument('--numbers',nargs='+',type=int,default=list(range(1,231)))
    parser.add_argument('--output',type=Path,default=Path('audits/xiao_mapping/results'))
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--verify-second',action='store_true')
    args = parser.parse_args()
    source = json.loads(args.source.read_text())
    args.output.mkdir(parents=True,exist_ok=True)
    for number in args.numbers:
        previous = args.output/f'sg{number:03d}.json'
        if args.resume and not args.verify_second and previous.exists():
            prior = json.loads(previous.read_text())
            if prior['matched'] == prior['expected'] == prior['unique_orbits'] and not prior['failures']:
                continue
        start = time.perf_counter()
        catalogue = json.loads((args.catalogues/f'sg{number:03d}.catalogue.json').read_text())
        matcher = ParentMatcher(number,source,catalogue)
        if args.verify_second:
            output = json.loads(previous.read_text())
            matcher.parameters = np.array([2,5,11],dtype=float)/101
            count = 0
            for row in output['rows']:
                chart = catalogue['charts'][catalogue['orbits'][row['orbit']][0]]
                if chart.get('representation',{}).get('parameter_count',0):
                    got = matcher.match(row['xiao_label'])
                    if got != row['orbit']:
                        raise ValueError(f'Second parameter check failed: {row["xiao_label"]}')
                    count += 1
            output['second_parameter_checked'] = count
            previous.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
            print('Second sample',number,count,round(time.perf_counter()-start,3),flush=True)
            continue
        matches = [];failures = []
        for label in matcher.rows:
            try:
                orbit = matcher.match(label)
                if orbit is None:raise ValueError('No matching computed chart')
                matches.append({'xiao_label':label,'orbit':orbit})
            except Exception as exc:
                failures.append({'xiao_label':label,'error':str(exc)})
        occupied = Counter(x['orbit'] for x in matches)
        collisions = {str(k):v for k,v in occupied.items() if v>1}
        output = dict(number=number,seconds=time.perf_counter()-start,
                      expected=len(catalogue['orbits']),matched=len(matches),
                      unique_orbits=len(occupied),collisions=collisions,failures=failures,rows=matches,
                      origin_shift=list(map(str,matcher.origin)))
        (args.output/f'sg{number:03d}.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
        print({k:v for k,v in output.items() if k not in ('rows','failures')},flush=True)
        if failures: print('First failures:',failures[:3],flush=True)


if __name__ == '__main__': main()
