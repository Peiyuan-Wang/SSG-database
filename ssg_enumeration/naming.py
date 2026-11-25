"""Exact HM spin labels (label规则 v1.1), separate from catalogue identifiers.

Conventional coordinates are used for display, primitive coordinates for
evaluation. No fractional root is chosen for a discrete translation image.
"""
import ast
from dataclasses import dataclass
from functools import cached_property, lru_cache
import gzip
from importlib.resources import files
import json
import re

from sympy import (ImmutableMatrix as M, Rational, cos, sin, pi, sqrt, simplify,
                   symbols, latex, expand)
from sympy.matrices.normalforms import hermite_normal_form
from .exact import mod1, is_integral
from .torus import AffineTorus, solve_torus, smith_decomposition
from .representations import rotation_2d, embed_o2

NAMING_VERSION = '1.1'


def _sign(exponent):
    return -1 if int(exponent) % 2 else 1


@lru_cache(maxsize=16384)
def _expr(text):
    """Small, non-executing expression reader for exact label arithmetic."""
    if not isinstance(text, str) or len(text) > 4096:
        raise ValueError('Invalid exact expression')
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return Rational(node.value)
        if isinstance(node, ast.Name):
            if node.id == 'pi':
                return pi
            if re.fullmatch(r'u\d+', node.id):
                return symbols(node.id, real=True)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a+b
            if isinstance(node.op, ast.Sub): return a-b
            if isinstance(node.op, ast.Mult): return a*b
            if isinstance(node.op, ast.Div): return a/b
            if isinstance(node.op, ast.Pow) and b.is_Integer and abs(b) <= 12: return a**b
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1 and not node.keywords:
            if node.func.id in ('sqrt', 'sin', 'cos'):
                return {'sqrt':sqrt, 'sin':sin, 'cos':cos}[node.func.id](visit(node.args[0]))
        raise ValueError('Only exact arithmetic, sqrt, sin and cos are allowed')
    try:
        result = visit(ast.parse(text, mode='eval').body)
    except (SyntaxError, TypeError, ZeroDivisionError, RecursionError) as exc:
        raise ValueError('Invalid exact expression') from exc
    if result.has(float('inf')) or result.is_finite is False:
        raise ValueError('Nonfinite exact expression')
    return result


def _matrix(data):
    if isinstance(data, dict):
        return _matrix_cached(tuple(data['shape']),tuple(x for row in data['entries'] for x in row))
    return _matrix_cached((len(data),len(data[0]) if data else 0),tuple(str(x) for row in data for x in row))


@lru_cache(maxsize=65536)
def _matrix_cached(shape,values):
    return M(*shape, [_expr(x) for x in values])


@lru_cache(maxsize=1)
def _settings():
    return json.loads(gzip.decompress(files('ssg_enumeration').joinpath('data/naming_settings.json.gz').read_bytes()))


def naming_setting(number):
    """Independent copy of the frozen Hall origin, primitive basis and HM lifts."""
    if type(number) is not int or not 1 <= number <= 230:
        raise ValueError('space_group must be an integer in 1..230')
    return json.loads(json.dumps(_settings()[str(number)]))


@lru_cache(maxsize=230)
def _parent(number):
    from .groups import SpaceGroup
    s = _settings()[str(number)]
    g = SpaceGroup(tuple(_matrix(r) for r in s['rotations']),
                   tuple(M([_expr(x) for x in t]) for t in s['sections']),s['hm'])
    return g, _matrix(s['primitive_basis'])


@lru_cache(maxsize=32768)
def canonical_torus(torus):
    """Row-HNF equations, lexicographic torus offset, saturated column-HNF basis.

    Coordinate restrictions retain *all* finite components. Restricting to the
    first SNF component would give a basis-dependent offset.
    """
    a, b = torus.constraints
    _, _, v = smith_decomposition(a)
    basis = M(hermite_normal_form(v[:, a.rank():]))
    candidates = (AffineTorus(torus.offset, basis),)
    for i in range(torus.offset.rows):
        if any(any(c.basis[i,j] for j in range(c.basis.cols)) for c in candidates):
            minimum = Rational(0)
        else:
            minimum = min(c.offset[i] for c in candidates)
            candidates = tuple(c for c in candidates if c.offset[i] == minimum)
            continue
        row = M(1, torus.offset.rows, lambda r,j: int(j == i))
        candidates = tuple(d for c in candidates for d in c.intersect(row,M([minimum])))
        if not candidates:
            raise ArithmeticError('Lost all components during canonical offset selection')
        if all(c.parameter_count == 0 for c in candidates):
            break
    offset = min((c.offset for c in candidates), key=tuple)
    result = AffineTorus(offset, basis)
    if result.key != torus.key:
        raise ArithmeticError('Canonical torus changed the represented component')
    return result


@lru_cache(maxsize=32768)
def _clean(m):
    return m.applyfunc(expand)


def _rotation_about(axis, turns):
    """Exact rotation by ``turns`` of a full turn about a unit vector."""
    cross = M([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]])
    angle = 2*pi*turns
    return _clean(cos(angle)*M.eye(3)+(1-cos(angle))*axis*axis.T+sin(angle)*cross)


# Spin rotations are not restricted to crystallographic orders, but only a
# short symbolic axis and a small denominator are readable. Larger orders fall
# back to the exact matrix, which is always unambiguous. Ascending order keeps
# the reported n equal to the actual order of the matrix.
_SPIN_ORDERS = (2,3,4,5,6,7,8,9,10,12,14,16,18,20,24)


@lru_cache(maxsize=16384)
def _spin_symbol(m):
    """Finite spin operation as a readable symbol, with an exact matrix fallback."""
    m = _clean(m)
    sign = int(m.det())
    if sign not in (-1,1) or _clean(m.T*m) != M.eye(3):
        raise ValueError('Spin operation must be an exact orthogonal 3x3 matrix')
    r = sign*m
    if r == M.eye(3):
        return '1' if sign == 1 else '-1'
    axis = (r-M.eye(3)).nullspace()[0]
    first = next(x for x in axis if x != 0)
    axis = (axis/first).applyfunc(simplify)
    if axis == M([1,0,0]): name = 'x'
    elif axis == M([0,1,0]): name = 'y'
    elif axis == M([0,0,1]): name = 'z'
    else: name = '['+','.join(str(simplify(x)) for x in axis)+']'
    # Every power j/n is a distinct operation with the same trace, so the
    # whole matrix must match; a trace test alone cannot name the rotation.
    unit = (axis/sqrt(axis.dot(axis))).applyfunc(simplify)
    power = None
    trace = simplify(r.trace())
    for n in _SPIN_ORDERS:
        for j in range(1,n):
            if simplify(1+2*cos(2*pi*Rational(j,n))-trace) != 0: continue
            if _rotation_about(unit,Rational(j,n)) == r:
                power = (n,j)
                break
        if power is not None: break
    if power is None:
        return 'M['+';'.join(','.join(str(x) for x in row) for row in m.tolist())+']'
    n, j = power
    if sign == -1 and n == 2:
        return 'm_'+name
    return ('-' if sign == -1 else '')+str(n)+'_'+name+('^'+str(j) if j != 1 else '')


@lru_cache(maxsize=16384)
def _spin_matrix(token):
    if token == '1': return M.eye(3)
    if token == '-1': return -M.eye(3)
    if token.startswith('M[') and token.endswith(']'):
        m = _matrix([row.split(',') for row in token[2:-1].split(';')])
    else:
        match = re.fullmatch(r'(-?)(\d+|m)_(x|y|z|\[[^\]]+\])(?:\^(\d+))?', token)
        if not match:
            raise ValueError('Invalid spin symbol: '+token)
        neg,n,axis,j = match.groups()
        if axis in ('x','y','z'):
            a = M([int(axis == k) for k in ('x','y','z')])
        else:
            a = M([_expr(x) for x in axis[1:-1].split(',')])
        if a.shape != (3,1) or a.dot(a) == 0 or any(x.free_symbols for x in a):
            raise ValueError('Invalid fixed spin axis')
        a = a/sqrt(a.dot(a))
        angle = pi if n == 'm' else 2*pi*Rational(int(j or 1),int(n))
        cross = M([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
        m = cos(angle)*M.eye(3)+(1-cos(angle))*a*a.T+sin(angle)*cross
        m = _clean((-1 if neg or n == 'm' else 1)*m)
    if m.shape != (3,3) or _clean(m.T*m) != M.eye(3):
        raise ValueError('Invalid spin matrix')
    return m


def _spin_latex(m):
    token=_spin_symbol(m)
    if token=='-1': return r'\overline{1}'
    if token=='1': return '1'
    if token.startswith('M['): return latex(m)
    match=re.fullmatch(r'(-?)(\d+|m)_(x|y|z|\[[^\]]+\])(?:\^(\d+))?',token)
    neg,n,axis,power=match.groups()
    if axis.startswith('['):
        axis='['+','.join(latex(_expr(x)) for x in axis[1:-1].split(','))+']'
    symbol=(r'\overline{'+n+'}' if neg else n)
    return symbol+'_{'+axis+'}'+('^{'+power+'}' if power else '')


@lru_cache(maxsize=8192)
def _finite_image(sections):
    image=set(sections)
    size=len(image)
    if size in (1,2,3): return f'C{size}'
    orders=[]
    for m in image:
        power=M.eye(3)
        for n in range(1,7):
            power=_clean(power*m)
            if power==M.eye(3): orders.append(n); break
        else: raise ValueError('Not a crystallographic finite spin image')
    maximum=max(orders)
    if size==maximum: return f'C{size}'
    if size==2*maximum: return f'D{maximum}'
    if size==12 and maximum==3: return 'T'
    if size==24 and maximum==4: return 'O'
    raise ValueError('Unrecognized finite spin image')


def _affine_text(offset, basis):
    u = M(symbols(f'u0:{basis.cols}', real=True)) if basis.cols else M.zeros(0,1)
    return '('+','.join(str(expand(x)).replace(' ','') for x in offset+basis*u)+')'


@dataclass(frozen=True)
class SSGName:
    """A self-contained name in a frozen parent setting, evaluable after parsing."""
    space_group: int
    dimension: str
    translation_kind: str
    q: M
    basis: M
    translation_spins: tuple
    grading_q: M
    spins: tuple
    general: bool = False

    @property
    def parameter_count(self): return self.basis.cols

    @property
    def parameters(self): return symbols(f'u0:{self.parameter_count}', real=True)

    @property
    def wavevector(self):
        _, c = _parent(self.space_group)
        u = M(self.parameters) if self.parameters else M.zeros(0,1)
        return c.inv().T*(self.q+self.basis*u)

    @property
    def parameter_domain(self):
        if not self.parameter_count: return ''
        domain = ','.join(map(str,self.parameters))+' in R/Z'
        return domain+('; 2*C^T*k notin Z^3' if self.general else '')

    @cached_property
    def text(self):
        s = _settings()[str(self.space_group)]
        _,c = _parent(self.space_group)
        k = ''
        if self.translation_kind == 'axial' and (any(self.q) or any(self.basis)):
            k = '^{'+_affine_text(c.inv().T*self.q,c.inv().T*self.basis)+'}'
        elif self.translation_kind == 'discrete' and any(m != M.eye(3) for m in self.translation_spins):
            k = '^{<'+','.join(_spin_symbol(m) for m in self.translation_spins)+'>}'
        chi = '_{'+_affine_text(c.inv().T*self.grading_q,M.zeros(3,0))+'}' if any(self.grading_q) else ''
        atoms = [ ('^{'+_spin_symbol(m)+'}' if m != M.eye(3) else '')+a['symbol']
                  for a,m in zip(s['atoms'],self.spins)]
        result = self.dimension+': '+k+s['lattice']+chi+' '+' '.join('/'.join(atoms[i] for i in slot) for slot in s['layout'])
        return result+(' | '+self.parameter_domain if self.parameter_count else '')

    @cached_property
    def latex(self):
        s = _settings()[str(self.space_group)]
        _,c = _parent(self.space_group)
        k = ''
        if self.translation_kind == 'axial' and (any(self.q) or any(self.basis)):
            k = '{}^{('+','.join(latex(x) for x in self.wavevector)+')}'
        elif self.translation_kind == 'discrete' and any(m != M.eye(3) for m in self.translation_spins):
            k = '{}^{\\langle '+','.join(_spin_latex(m) for m in self.translation_spins)+'\\rangle}'
        chi = '_{('+','.join(latex(x) for x in c.inv().T*self.grading_q)+')}' if any(self.grading_q) else ''
        def hm_latex(symbol):
            return re.sub(r'-(\d+)',lambda match:r'\bar{'+match.group(1)+'}',symbol)
        atoms = [('{}^{'+_spin_latex(m)+'}' if m != M.eye(3) else '')+hm_latex(a['symbol']) for a,m in zip(s['atoms'],self.spins)]
        result = '\\mathrm{'+self.dimension+'}:\\;'+k+s['lattice']+chi+'\\,'+'\\,'.join('/'.join(atoms[i] for i in slot) for slot in s['layout'])
        if self.parameter_count:
            result += r',\quad '+','.join(latex(u) for u in self.parameters)+r'\in\mathbb R/\mathbb Z'
            if self.general: result += r',\quad 2C_B^T\mathbf k\notin\mathbb Z^3'
        return result

    @property
    def liu_latex(self):
        """Display the spin-only group as a Liu-style suffix in LaTeX.

        The canonical ASCII name and its parser remain unchanged. A spin-only
        identity is implicit for noncoplanar records.
        """
        parts = self.latex.split(r',\quad ', 1)
        prefix = r'\mathrm{'+self.dimension+r'}:\;'
        if not parts[0].startswith(prefix):
            raise ValueError('Unexpected label rendering')
        result = parts[0][len(prefix):] + {
            'L':r'\,{}^{\infty m}\!1', 'P':r'\,{}^{m}\!1', 'N':''}[self.dimension]
        return result+(r',\quad '+parts[1] if len(parts)>1 else '')

    @cached_property
    def exact_key(self):
        return (self.dimension, self.translation_kind, tuple(self.q), tuple(self.basis),
                tuple(x for m in self.translation_spins for x in m), tuple(self.grading_q),
                tuple(x for m in self.spins for x in m), self.parameter_count, self.general)

    def to_dict(self):
        return {'version':NAMING_VERSION,'space_group':self.space_group,'dimension':self.dimension,
                'translation_kind':self.translation_kind,'q':[str(x) for x in self.q],
                'basis':[[str(x) for x in row] for row in self.basis.tolist()],
                'translation_spins':[_spin_symbol(m) for m in self.translation_spins],
                'grading_q':[str(x) for x in self.grading_q],
                'spins':[_spin_symbol(m) for m in self.spins], 'general':self.general}

    @classmethod
    def from_dict(cls,data, *, validate=True):
        if data.get('version') != NAMING_VERSION:
            raise ValueError('Unsupported naming version')
        naming_setting(data['space_group'])
        obj = cls(data['space_group'], data['dimension'],data['translation_kind'],
                  M([_expr(x) for x in data['q']]),_matrix(data['basis']),
                  tuple(_spin_matrix(x) for x in data['translation_spins']),
                  M([_expr(x) for x in data['grading_q']]),
                  tuple(_spin_matrix(x) for x in data['spins']),data['general'])
        if validate: obj.validate()
        return obj

    def _translation(self,t,parameters):
        t = M(t)
        if t.shape != (3,1) or not is_integral(t): raise ValueError('Expected an integer primitive translation')
        q = self.q+self.basis*(M(parameters) if len(parameters) else M.zeros(0,1))
        proper = M.eye(3)
        if self.translation_kind == 'axial': proper = embed_o2(rotation_2d(q.dot(t)))
        elif self.translation_kind == 'discrete':
            for m,power in zip(self.translation_spins,t): proper = _clean(proper*m**int(power))
        return _sign(2*self.grading_q.dot(t))*proper

    def _sections(self,parameters):
        g,c = _parent(self.space_group)
        s = _settings()[str(self.space_group)]
        q = self.q+self.basis*(M(parameters) if len(parameters) else M.zeros(0,1))
        gens = []
        for a,spin in zip(s['atoms'],self.spins):
            tau = g.translations[a['point']]+M(a['shift'])
            gens.append(embed_o2(rotation_2d(q.dot(tau)))*spin if self.translation_kind == 'axial' else spin)
        sections = {0:M.eye(3)}
        queue = [0]
        for p in queue:
            for a,spin in zip(s['atoms'],gens):
                r = g.table[p][a['point']]
                if r in sections: continue
                shift = g.cocycle[p][a['point']]+g.rotations[p]*M(a['shift'])
                sections[r] = _clean(self._translation(-shift,parameters)*sections[p]*spin)
                queue.append(r)
        if len(sections) != g.order: raise ValueError('Incomplete HM generating set')
        return tuple(sections[p] for p in range(g.order))

    def evaluate(self,translation=(0,0,0),point=0,parameters=(),*,embedded=True):
        """Recover varrho(t*s(point)); parameters are exact rational values."""
        if len(parameters) != self.parameter_count: raise ValueError('Wrong number of parameters')
        parameters = tuple(Rational(x) for x in parameters)
        q = self.q+self.basis*(M(parameters) if parameters else M.zeros(0,1))
        if self.general and is_integral(2*q): raise ValueError('Excluded TRIM/zero member; use its separate class')
        sections = self._sections(parameters)
        if type(point) is not int or not 0 <= point < len(sections): raise ValueError('Invalid point index')
        result = _clean(self._translation(translation,parameters)*sections[point])
        return result[:2,:2] if self.dimension == 'P' and not embedded else result

    def validate(self):
        """Validate all generator relations; axial families use affine phases."""
        _validate_name(self)
        return True

    def to_record(self):
        """Recover an SSG record, restoring the solver's theta_r=0 gauge.

        A phase-stripped display may use a parameter-dependent spin frame.
        Restoring the original gauge is essential before constructing an
        integral AffineTorus; fractional display slopes must not be rounded.
        """
        from .records import SSG
        from .gradings import Grading
        from .type1 import Type1Record
        from .representations import MatrixRepresentation
        dimension = {'L':'Collinear','P':'Coplanar','N':'Noncoplanar'}[self.dimension]
        if self.translation_kind == 'axial':
            sections,_ = _affine_sections(self)
            eta = tuple(e for _,e,_ in sections)
            phases = M.vstack(*(p for p,_,_ in sections))
            if -1 in eta:
                pivot = eta.index(-1)
                phases = M.vstack(*(phases[p,:]-(1-eta[p])//2*phases[pivot,:] for p in range(len(eta))))
            z = self.q.row_join(self.basis).col_join(phases)
            if not is_integral(z[:,1:]):
                raise ValueError('The stated parameter periods do not close the gauge-fixed representation')
            torus = AffineTorus(z[:,0],z[:,1:])
            representation = Type1Record(eta,torus,'general' if self.general else 'trim',2 if self.dimension=='P' else 3)
            grading = Grading(self.grading_q,tuple(int(c==-1) for _,_,c in sections)) if self.dimension!='P' else None
        else:
            sections = self._sections(())
            bits = tuple(int(m.det()==-1) for m in sections)
            grading = Grading(self.grading_q,bits) if self.dimension!='P' else None
            if self.dimension=='L': return SSG(dimension,grading=grading)
            proper = tuple(_clean(int(m.det())*m) for m in sections)
            translations = self.translation_spins or (M.eye(3),)*3
            if self.dimension=='P':
                proper = tuple(m[:2,:2] for m in proper)
                translations = tuple(m[:2,:2] for m in translations)
                if self.translation_kind=='trivial':
                    components=tuple(_axial_parts(embed_o2(m)) for m in proper)
                    eta=tuple(e for _,e,_ in components)
                    phases=M([x for x,_,_ in components])
                    if -1 in eta:
                        pivot=eta.index(-1)
                        phases=M([phases[p]-(1-eta[p])//2*phases[pivot] for p in range(len(eta))])
                    torus=AffineTorus(M.zeros(3,1).col_join(phases),M.zeros(3+len(eta),0))
                    return SSG(dimension,Type1Record(eta,torus,'zero',2))
            kind = 'type2' if self.translation_kind=='discrete' else 'type0'
            waves = tuple(M([Rational(1-translations[j][i,i],4) for j in range(3)]) for i in range(translations[0].rows))
            waves = tuple(dict.fromkeys(w for w in waves if any(w)))
            image = ('D1' if self.dimension=='P' and len(set(translations+(M.eye(2),)))==2 else 'V4') if kind=='type2' else _finite_image(proper)
            representation = MatrixRepresentation(translations,proper,kind,image,waves,
                tuple(i for i,m in enumerate(proper) if m==M.eye(m.rows)))
        return SSG(dimension,representation,grading)


def _chart_name(number, chart):
    """Construct a chart name and verify removal of *all* parameter dependence."""
    g,c = _parent(number)
    setting = _settings()[str(number)]
    dim = {'Collinear':'L','Coplanar':'P','Noncoplanar':'N'}[chart['dimension']]
    grading = chart.get('grading')
    chiq = _matrix(grading['k']) if grading else M.zeros(3,1)
    bits = grading['section_bits'] if grading else [0]*g.order
    r = chart.get('representation')
    q, basis, ts, spins = M.zeros(3,1), M.zeros(3,0), (), []
    kind, general = 'trivial', False
    if r and 'offset' in r:
        torus = canonical_torus(AffineTorus(_matrix(r['offset']),_matrix(r['basis'])))
        off, bas, eta = torus.offset,torus.basis,r['eta']
        q, basis = off[:3,:], bas[:3,:]
        axial = r['stratum'] != 'zero'
        kind = 'axial' if axial else 'trivial'
        general = r['stratum'] == 'general'
        ph = M([off[3+p]-(q.dot(g.translations[p]) if axial else 0) for p in range(g.order)])
        pb = M(g.order,bas.cols,lambda p,j:bas[3+p,j]-(basis[:,j].dot(g.translations[p]) if axial else 0))
        if -1 in eta:
            pivot = eta.index(-1)
            ph = M([ph[p]-(1-eta[p])//2*ph[pivot] for p in range(g.order)])
            pb = M(g.order,bas.cols,lambda p,j:pb[p,j]-(1-eta[p])//2*pb[pivot,j])
        if any(pb): raise ArithmeticError('Reduced spin operation still depends on family parameters')
        for a in setting['atoms']:
            p = a['point']; shift = M(a['shift'])
            phase = mod1(ph[p])
            # The axial q.shift cancels against F(tau+shift).
            if not axial: phase = mod1(phase+q.dot(shift))
            sign = _sign(bits[p]+int(2*chiq.dot(shift)))
            spins.append(_clean(sign*embed_o2(rotation_2d(phase)*M.diag(1,eta[p]))))
    elif r:
        trans = tuple(_matrix(t) for t in r['translations'])
        sections = tuple(_matrix(t) for t in r['sections'])
        if trans[0].rows == 2:
            trans = tuple(embed_o2(t) for t in trans)
            sections = tuple(embed_o2(t) for t in sections)
        if any(t != M.eye(3) for t in trans): kind,ts = 'discrete',trans
        for a in setting['atoms']:
            p = a['point']; shift = M(a['shift'])
            m = sections[p]
            for t,power in zip(trans,shift): m = t**int(power)*m
            spins.append(_clean(_sign(bits[p]+int(2*chiq.dot(shift)))*m))
    else:
        spins = [_sign(bits[a['point']]+int(2*chiq.dot(M(a['shift']))))*M.eye(3) for a in setting['atoms']]
    return SSGName(number,dim,kind,q,basis,ts,chiq,tuple(spins),general)


@lru_cache(maxsize=1)
def _name_catalogue():
    path = files('ssg_enumeration').joinpath('data/ssg_names.json.gz')
    data = json.loads(gzip.decompress(path.read_bytes()))
    rows = data['rows']
    return data, {r['id']:r for r in rows}, {r['text']:r for r in rows}


@lru_cache(maxsize=8192)
def name_for_label(label):
    """Resolve a full old ID, Xiao ID, or new formal name to its canonical name."""
    from .xiao import from_xiao_label
    data,ids,names = _name_catalogue()
    if label in names: row = names[label]
    else:
        if not label.startswith('SG'): label = from_xiao_label(label)
        try: row = ids[label]
        except KeyError: raise KeyError('Unknown classification label: '+label) from None
    return SSGName.from_dict(row['name'],validate=False)


def label_for_record(space_group,record):
    """Canonical formal label for any stored standard chart, not only orbit[0]."""
    from .xiao import _record_signature
    key = f'{space_group}:{_record_signature(record)}'
    data,ids,_ = _name_catalogue()
    try: return ids[data['chart_ids'][key]]['text']
    except KeyError:
        from .serialization import record_data
        semantic = f'{space_group}:{_semantic_signature(record_data(record))}'
        try: return ids[data['semantic_ids'][semantic]]['text']
        except KeyError:
            raise KeyError('Record is outside the frozen standard charts; use name_for_chart for a noncanonical display') from None


def name_for_chart(space_group, record):
    """Display a standard-setting record without claiming catalogue recognition."""
    from .serialization import record_data
    return _chart_name(space_group,record_data(record))


def _semantic_signature(chart):
    """Parameter-basis independent key; finite image names are not matrix data."""
    import hashlib
    from .serialization import matrix_data
    data = {k:v for k,v in chart.items() if k not in ('chart','label')}
    if 'representation' in data:
        r = dict(data['representation'])
        for field in ('image','kernel','wavevectors','parameter_count','excluded'): r.pop(field,None)
        if 'offset' in r:
            t = canonical_torus(AffineTorus(_matrix(r['offset']),_matrix(r['basis'])))
            r['offset'],r['basis'] = matrix_data(t.offset),matrix_data(t.basis)
        data['representation']=r
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def naming_metadata():
    return json.loads(json.dumps(_name_catalogue()[0]['metadata']))


@lru_cache(maxsize=16384)
def _axial_parts(m):
    chi = int(m.det())
    r = chi*m
    eta = int(r[2,2])
    if eta not in (-1,1) or any(r[i,2] or r[2,i] for i in range(2)):
        raise ValueError('Axial spin operation does not preserve the z axis')
    # Exact comparison, never angle extraction from floating point matrices.
    for den in (1,2,3,4,6,8,12,16,24,48):
        for num in range(den):
            x = Rational(num,den)
            if cos(2*pi*x) == r[0,0] and sin(2*pi*x) == r[1,0]:
                return x,eta,chi
    raise ValueError('Unsupported exact axial phase')


def _affine_sections(name):
    """Reconstruct all section phases without trigonometric simplification."""
    g,_ = _parent(name.space_group)
    setting = _settings()[str(name.space_group)]
    q = name.q.row_join(name.basis)
    generators = []
    for atom,spin in zip(setting['atoms'],name.spins):
        x,eta,chi = _axial_parts(spin)
        phase = (g.translations[atom['point']]+M(atom['shift'])).T*q
        phase = M(phase); phase = phase+M([[x]+[0]*name.parameter_count])
        generators.append((phase,eta,chi))
    out = {0:(M.zeros(1,name.parameter_count+1),1,1)}
    queue = [0]
    for p in queue:
        ph,ep,cp = out[p]
        for atom,(pa,ea,ca) in zip(setting['atoms'],generators):
            r = g.table[p][atom['point']]
            if r in out: continue
            shift = g.cocycle[p][atom['point']]+g.rotations[p]*M(atom['shift'])
            value = ph+ep*pa-shift.T*q
            value = M([[mod1(value[0])]+list(value)[1:]])
            out[r] = (value,ep*ea,cp*ca*_sign(2*name.grading_q.dot(shift)))
            queue.append(r)
    return tuple(out[p] for p in range(g.order)),tuple(generators)


def _validate_name(name):
    g,_ = _parent(name.space_group)
    atoms = _settings()[str(name.space_group)]['atoms']
    if name.dimension not in ('L','P','N') or name.translation_kind not in ('trivial','axial','discrete'):
        raise ValueError('Invalid name branch')
    if name.q.shape != (3,1) or name.grading_q.shape != (3,1) or name.basis.rows != 3:
        raise ValueError('Invalid wavevector shape')
    if any(x.is_Rational is not True for x in (*name.q,*name.basis,*name.grading_q)):
        raise ValueError('Wavevector coefficients must be rational')
    if not is_integral(2*name.grading_q) or len(name.spins) != len(atoms):
        raise ValueError('Invalid grading or incomplete HM spin data')
    if name.dimension == 'P' and (any(name.grading_q) or any(m.det() != 1 or any(m[i,2] or m[2,i] for i in range(2)) for m in name.spins+name.translation_spins)):
        raise ValueError('P names must preserve the spin plane and use the proper lift')
    if name.dimension == 'L' and (name.translation_kind != 'trivial' or any(m not in (M.eye(3),-M.eye(3)) for m in name.spins)):
        raise ValueError('L names use chi*I3')
    if name.translation_kind != 'axial' and (any(name.q) or name.parameter_count or name.general):
        raise ValueError('Only axial branches carry wavevector parameters')
    if name.translation_kind == 'discrete':
        if len(name.translation_spins) != 3: raise ValueError('Expected three primitive translation images')
        allowed = (M.eye(3),M.diag(1,-1,-1),M.diag(-1,1,-1),M.diag(-1,-1,1))
        if any(t not in allowed for t in name.translation_spins): raise ValueError('Invalid discrete translation spin')
        image={M.eye(3)}
        for t in name.translation_spins: image |= {a*t for a in tuple(image)}
        if name.dimension=='N' and len(image)!=4:
            raise ValueError('N discrete translation image must be the full V4')
        if name.dimension=='P' and (len(image) not in (2,4) or image=={allowed[0],allowed[3]}):
            raise ValueError('Use an axial wavevector for plane-rotation-only translations')
    elif name.translation_spins:
        raise ValueError('Unexpected discrete translations')
    if name.translation_kind == 'axial':
        sections,gens = _affine_sections(name)
        q = name.q.row_join(name.basis)
        for p,(ph,eta,chi) in enumerate(sections):
            covariance = g.rotations[p].T*q-eta*q
            if not is_integral(covariance[:,0]) or any(covariance[:,1:]):
                raise ValueError('Wavevector covariance fails')
            if not is_integral(g.rotations[p].T*name.grading_q-name.grading_q):
                raise ValueError('Grading covariance fails')
            for a,(pa,ea,ca) in zip(atoms,gens):
                r = g.table[p][a['point']]
                shift = g.cocycle[p][a['point']]+g.rotations[p]*M(a['shift'])
                expected = ph+eta*pa-shift.T*q
                rhs,er,cr = sections[r]
                defect = expected-rhs
                if not defect[0].is_integer or any(defect[:,1:]) or er != eta*ea or cr != chi*ca*_sign(2*name.grading_q.dot(shift)):
                    raise ValueError('Axial generator relation fails')
        name.to_record()  # Also certify the stated periods in the joint (q,theta) torus.
    else:
        ts = tuple(name._translation(M.eye(3)[:,j],()) for j in range(3))
        if any(_clean(a*b-b*a) != M.zeros(3) for a in ts for b in ts):
            raise ValueError('Translation images do not commute')
        sections = name._sections(())
        for p,spin in enumerate(sections):
            for j in range(3):
                if _clean(spin*ts[j]-name._translation(g.rotations[p][:,j],())*spin) != M.zeros(3):
                    raise ValueError('Translation covariance fails')
            for a,sa in zip(atoms,name.spins):
                r = g.table[p][a['point']]
                shift = g.cocycle[p][a['point']]+g.rotations[p]*M(a['shift'])
                if _clean(spin*sa-name._translation(shift,())*sections[r]) != M.zeros(3):
                    raise ValueError('Generator relation fails')


def _split_top(text):
    result,depth,start = [],0,0
    for i,c in enumerate(text):
        if c in '([': depth += 1
        elif c in ')]': depth -= 1
        elif c == ',' and depth == 0:
            result.append(text[start:i]); start = i+1
    result.append(text[start:])
    return result


def parse_label(text, *, validate=True):
    """Parse the formal ASCII notation, without consulting class IDs.

    Unknown or malformed names raise; by default all group relations are
    checked. The exact structured JSON representation is also supported by
    SSGName.from_dict. LaTeX is an output format, not an input language.
    """
    if not isinstance(text,str) or len(text) > 20000: raise ValueError('Invalid label')
    parts = text.split(' | ')
    if len(parts) > 2: raise ValueError('Invalid parameter domain')
    match = re.fullmatch(r'([LPN]): (?:\^\{([^{}]+)\})?([PABCIFR])(?:_\{([^{}]+)\})? (.+)', parts[0])
    if not match: raise ValueError('Invalid formal label')
    dim,ktoken,lattice,chitoken,body = match.groups()
    hm = lattice+' '+re.sub(r'\^\{[^{}]*\}','',body)
    numbers = [int(n) for n,s in _settings().items() if s['hm'] == hm]
    if len(numbers) != 1: raise ValueError('Unknown or ambiguous standard HM symbol')
    number = numbers[0]; g,c = _parent(number)
    s = _settings()[str(number)]
    tokens = []
    # A slash in a spin axis expression is enclosed in braces, not an HM separator.
    pos = 0
    for slot_index,slot in enumerate(s['layout']):
        for atom_index,i in enumerate(slot):
            if pos < len(body) and body[pos:pos+2] == '^{':
                end = body.find('}',pos)
                if end < 0: raise ValueError('Unterminated spin superscript')
                token = body[pos+2:end]; pos = end+1
            else: token = '1'
            symbol = s['atoms'][i]['symbol']
            if body[pos:pos+len(symbol)] != symbol: raise ValueError('HM operation mismatch')
            pos += len(symbol); tokens.append(_spin_matrix(token))
            separator = '/' if atom_index+1 < len(slot) else (' ' if slot_index+1 < len(s['layout']) else '')
            if body[pos:pos+len(separator)] != separator: raise ValueError('Invalid HM separator')
            pos += len(separator)
    if pos != len(body): raise ValueError('Trailing label content')
    def vector(token):
        if not token.startswith('(') or not token.endswith(')'): raise ValueError('Expected a wavevector tuple')
        vec = M([_expr(x) for x in _split_top(token[1:-1])])
        if vec.shape != (3,1): raise ValueError('Expected a three-component wavevector')
        return vec
    chiq = c.T*vector(chitoken) if chitoken else M.zeros(3,1)
    q,basis,ts,kind = M.zeros(3,1),M.zeros(3,0),(),'trivial'
    if ktoken:
        if ktoken.startswith('<') and ktoken.endswith('>'):
            ts = tuple(_spin_matrix(t) for t in _split_top(ktoken[1:-1])); kind='discrete'
        else:
            expr = c.T*vector(ktoken)
            params = sorted(set().union(*(v.free_symbols for v in expr)),key=lambda u:int(str(u)[1:]))
            if tuple(params) != symbols(f'u0:{len(params)}',real=True): raise ValueError('Parameters must be numbered from u0')
            q = expr.subs({u:0 for u in params})
            basis = M(3,len(params),lambda i,j:expr[i].diff(params[j]))
            if any(x.free_symbols for x in basis) or expr != q+basis*(M(params) if params else M.zeros(0,1)):
                raise ValueError('Wavevector must be affine in the parameters')
            kind='axial'
    general = len(parts) == 2 and '; 2*C^T*k notin Z^3' in parts[1]
    # A fixed non-TRIM axial point is a discrete Type 1 chart.
    if kind == 'axial' and basis.cols == 0: general = not is_integral(2*q)
    name = SSGName(number,dim,kind,q,basis,ts,chiq,tuple(tokens),general)
    if name.text != text: raise ValueError('Noncanonical spelling or inconsistent parameter domain')
    if validate: name.validate()
    return name
