"""Spin quotient followed by spatial quotient, retaining exact continuous relations.

A quotient of a continuous chart is a presentation by parameter relations.
It is never represented by a single sampled point or by a hash of a family label.
"""
from dataclasses import dataclass
from functools import cached_property,lru_cache
from collections import Counter,deque
from sympy import ImmutableMatrix as Matrix, ilcm
from .exact import is_integral,exact_matrix
from .type1 import Type1Record
from .type2 import monomial_spin_key
from .torus import parameter_relation,solve_torus,ParameterRelation
from .automorphisms import transform_ssg,type1_pullback_matrix,transform_representation,transform_grading


def spin_key(ssg):
    grading = None if ssg.grading is None else ssg.grading.key
    return ssg.dimension,grading,representation_spin_key(ssg.representation)


def representation_spin_key(r):
    if r is None:
        key = None
    elif isinstance(r,Type1Record):
        key = r.spin_key
    elif r.kind == 'type0':
        key = ('type0',r.image,r.kernel)
    else:
        key = monomial_spin_key(r)
    return key


def deduplicate_spin_conjugation(records):
    out = {}
    for s in records:
        out.setdefault(spin_key(s),s)
    return tuple(out.values())


@dataclass(frozen=True)
class QuotientRelation:
    source: int
    target: int
    name: str
    parameters: object = None
    ambient_map: object = None


@dataclass(frozen=True)
class EquivalenceDecision:
    status: str  # equivalent, distinct, unknown
    reason: str
    witness: tuple = ()


@dataclass(frozen=True)
class EnumerationResult:
    """Finite chart catalogue plus an exact presentation of its quotient.

    `records` has one chart per orbit of charts; each continuous chart still
    denotes infinitely many groups, identified only by `relations`.
    `charts` preserves all coordinates needed to interpret those relations.
    """
    charts: tuple
    orbits: tuple
    relations: tuple
    automorphisms: tuple = ()
    spatial_scope: str = 'spin_only'
    verified: bool = False
    normalizer_certificate: object = None

    @property
    def records(self):
        return tuple(self.charts[orbit[0]] for orbit in self.orbits)

    def __iter__(self):
        return iter(self.records)

    def __len__(self):
        return len(self.orbits)

    def by_label(self, label):
        return tuple(s for s in self.records if s.label == label)

    def summary(self):
        return {'spatial_scope':self.spatial_scope,'verified':self.verified,
                'continuous_family_convention':'one punctured parameter domain, regardless of connected components',
                'normalizer_certificate':self.normalizer_certificate,
                'spin_charts':len(self.charts),'chart_orbits':len(self),
                'continuous_chart_orbits':sum(s.parameter_count > 0 for s in self.records),
                'labels':dict(sorted(Counter(s.label for s in self.records).items())),
                'parameter_relations':len(self.relations)}

    @cached_property
    def chart_index(self):
        return {spin_key(s):i for i,s in enumerate(self.charts)}

    def locate(self, ssg):
        """Find a spin-equivalent chart, not an assertion of pointwise equivalence."""
        return self.chart_index.get(spin_key(ssg))

    def equivalent_points(self, source, u, target, v, max_states=10000):
        """Exact orbit search for supplied points, with an explicit unknown result.

        Infinite or very large orbits are not truncated into a false 'distinct'.
        Rational points have finite orbits in these integral torus coordinates.
        Irrational values support direct spin checks; further search is reported
        as unknown, while the symbolic quotient presentation remains exact.
        """
        if max_states < 1:
            raise ValueError("max_states must be positive.")
        first,second = self.charts[source],self.charts[target]
        r,s = first.representation,second.representation
        if first.label != second.label or not any(source in o and target in o for o in self.orbits):
            return EquivalenceDecision('distinct','Different invariant strata or chart orbits.')
        if not first.parameter_count and not second.parameter_count:
            if u or v:
                raise ValueError("Discrete records take no parameters.")
            return EquivalenceDecision('equivalent','The finite chart orbit proves equivalence.')
        if not isinstance(r,Type1Record) or not isinstance(s,Type1Record):
            raise ValueError("Parameters are only available for Type 1 charts.")
        r.point(u)
        s.point(v)
        if source == target and r.same_point(u,s,v):
            return EquivalenceDecision('equivalent','Exact spin conjugacy at the specified points.',('spin',))
        x,y = r.torus.evaluate(u),s.torus.evaluate(v)
        if not all(z.is_Rational for z in tuple(x)+tuple(y)):
            return EquivalenceDecision('unknown','Irrational orbit search is not decided; use the exact parameter relations.')
        graph = {}
        for rel in self.relations:
            if rel.ambient_map is not None:
                graph.setdefault(rel.source,[]).append(rel)
        queue = deque([(source,x,())])
        seen = {(source,tuple(x))}
        while queue:
            i,point,word = queue.popleft()
            if i == target and is_integral(point-y):
                return EquivalenceDecision('equivalent','Exact orbit witness.',word)
            for rel in graph.get(i,()):
                from .exact import mod_vector
                image = mod_vector(rel.ambient_map*point)
                state = (rel.target,tuple(image))
                if state in seen:
                    continue
                if len(seen) >= max_states:
                    return EquivalenceDecision('unknown','Orbit search reached max_states; no inequivalence claim is made.')
                seen.add(state)
                queue.append((rel.target,image,word+(rel.name,)))
        return EquivalenceDecision('distinct','Exhausted the exact finite point orbit.')


def deduplicate_automorphisms(records, automorphisms=(), scope=None, verified=False):
    """Take orbits of already spin-quotiented charts and retain parameter actions.

    A generator list is sufficient even for infinite Out+(G): its action on
    chart labels is finite, while infinite parameter actions remain as relations.
    """
    charts = deduplicate_spin_conjugation(records)
    index = {spin_key(s):i for i,s in enumerate(charts)}
    parent = list(range(len(charts)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    relations = []
    actions = tuple(automorphisms)
    actions_with_inverse = actions+tuple(a.inverse() for a in actions)
    # Factor the product rho x chi: transform each rho and chi only once per
    # generator. In particular, Smith computations must not repeat for every
    # grading paired with the same continuous family.
    @lru_cache(maxsize=None)
    def grading_action(grading,alpha):
        return None if grading is None else transform_grading(grading,alpha).key

    @lru_cache(maxsize=None)
    def representation_action(r,alpha):
        transformed = None if r is None else transform_representation(r,alpha)
        return representation_spin_key(transformed),transformed

    @lru_cache(maxsize=None)
    def continuous_action(r,target,alpha):
        _,transformed = representation_action(r,alpha)
        linear = type1_pullback_matrix(r,alpha)
        if transformed.torus.key != target.torus.key: linear = -linear
        if r.torus.transform(linear).key != target.torus.key:
            raise ArithmeticError("Failed to certify a family reparametrization.")
        return parameter_relation(r.torus,target.torus,linear),linear
    for i,ssg in enumerate(charts):
        r = ssg.representation
        if isinstance(r,Type1Record):
            relation = r.inversion_relation()
            if relation is not None:
                relations.append(QuotientRelation(i,i,'spin inversion',relation,-Matrix.eye(r.torus.offset.rows)))
        for alpha in actions_with_inverse:
            key,_ = representation_action(r,alpha)
            j = index.get((ssg.dimension,grading_action(ssg.grading,alpha),key))
            if j is None:
                raise ValueError(f"Catalogue is not closed under {alpha.name}; refusing an incomplete quotient.")
            parent[root(j)] = root(i)
            params,linear = None,None
            if isinstance(r,Type1Record):
                params,linear = continuous_action(r,charts[j].representation,alpha)
            relations.append(QuotientRelation(i,j,alpha.name,params,linear))
    buckets = {}
    for i in range(len(charts)):
        buckets.setdefault(root(i),[]).append(i)
    orbits = tuple(sorted((tuple(v) for v in buckets.values()),key=lambda o:o[0]))
    if scope is None:
        scope = 'provided_generators' if actions else 'spin_only'
    return EnumerationResult(charts,orbits,tuple(relations),actions,scope,verified)


def equivalence_loci(first, second, alpha=None):
    """Exact parameter loci where two Type 1 SSGs are equivalent for one action.

    Returned affine tori parameterize (u,v); endpoints must additionally obey
    their stratum exclusions. This can find special loci even when entire
    charts are not equal. A union over a finite set of actions is exact for it.
    """
    if first.dimension != second.dimension or first.label != second.label:
        return ()
    a,b = first.representation,second.representation
    if not isinstance(a,Type1Record) or not isinstance(b,Type1Record):
        raise ValueError("Expected Type 1 parameter records.")
    transformed = first if alpha is None else transform_ssg(first,alpha)
    if transformed.grading != second.grading or transformed.representation.eta != b.eta:
        return ()
    linear = Matrix.eye(a.torus.offset.rows) if alpha is None else type1_pullback_matrix(a,alpha)
    output = {}
    for sign in (1,-1):
        relation = parameter_relation(a.torus,b.torus,sign*linear)
        for locus in relation.solution_components():
            output[locus.key] = locus
    return tuple(output.values())


def stabilizer_loci(record, alpha=None, spin_sign=1):
    """Parameter locus where rho = spin_sign*(rho pullback), in phase coordinates.

    This tests a specified action; it does not claim to enumerate every element
    of an infinite stabilizer. Remove the record's TRIM exclusions afterwards.
    """
    if not isinstance(record,Type1Record) or spin_sign not in (-1,1):
        raise ValueError("Expected a Type 1 record and sign +/-1.")
    n = record.torus.offset.rows
    if alpha is not None and tuple(record.eta[p] for p in alpha.permutation) != record.eta:
        return ()
    linear = Matrix.eye(n) if alpha is None else type1_pullback_matrix(record,alpha)
    delta = spin_sign*linear-Matrix.eye(n)
    return solve_torus(delta*record.torus.basis,-delta*record.torus.offset)


def rational_p1_wavevector_orbit_key(k):
    """SL(3,Z) orbit of a rational k mod Z^3: its exact additive order.

    Applies to k alone. A nontrivial grading or section data needs the joint
    action above and MUST NOT be discarded when using this invariant.
    """
    k = exact_matrix(k)
    if k.shape != (3,1):
        raise ValueError("Expected three rational reciprocal coordinates.")
    denominator = 1
    for x in k:
        denominator = ilcm(denominator,x.q)
    return int(denominator)


def verify_equivalence_witness(group, first, u, second, v, word=()):
    """Verify a finite automorphism word for exact rational OR irrational points.

    True proves equivalence; False only rejects THIS witness, not every possible
    spatial automorphism. None means integrality of an exact expression is undecided.
    Word order follows successive pullbacks, as in transform_ssg.
    """
    transformed = first
    for alpha in word:
        alpha.validate(group)
        transformed = transform_ssg(transformed,alpha)
    if transformed.dimension != second.dimension or transformed.grading != second.grading:
        return False
    r,s = transformed.representation,second.representation
    if isinstance(r,Type1Record) and isinstance(s,Type1Record):
        return r.same_point(u,s,v)
    if u or v:
        raise ValueError("Discrete representations take no parameters.")
    return spin_key(transformed) == spin_key(second)

