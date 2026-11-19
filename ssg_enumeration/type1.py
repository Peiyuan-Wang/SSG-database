"""MD module 3: coupled wavevector/cocycle tori, gauge quotient, and strata.

All phases are turns. Solving k and theta jointly retains finite-sheet monodromy.
The residual spin inversion is an identification, NOT equality of every point
in a connected family. Zero and TRIM loci are separated before type labelling.
"""
from dataclasses import dataclass, replace
from functools import lru_cache, cached_property
from sympy import ImmutableMatrix as Matrix, zeros
from .exact import exact_matrix, is_integral, is_trim, mod_vector
from .gradings import point_gradings
from .torus import solve_torus, AffineTorus, parameter_relation
from .representations import rotation_2d, embed_o2


def validate_eta(group, eta):
    eta = tuple(eta)
    if len(eta) != group.order or any(e not in (-1,1) for e in eta):
        raise ValueError("eta must give one sign for each point-group element.")
    if any(eta[a]*eta[b] != eta[group.table[a][b]] for a in range(group.order) for b in range(group.order)):
        raise ValueError("eta is not a homomorphism.")
    return eta


def cocycle_matrix(group, eta):
    eta = validate_eta(group,eta)
    rows = []
    for a in range(group.order):
        for b in range(group.order):
            row = [0]*group.order
            row[a] += 1
            row[b] += eta[a]
            row[group.table[a][b]] -= 1
            rows.append(row)
    return Matrix(rows)


def gauge_matrix(eta, include_wavevector=True):
    """Set theta_r=0 for the first eta_r=-1, modulo continuous coboundaries."""
    shift = 3 if include_wavevector else 0
    out = zeros(shift+len(eta))
    for j in range(out.rows):
        out[j,j] = 1
    if -1 in eta:
        r = eta.index(-1)
        for p,e in enumerate(eta):
            out[shift+p,shift+r] -= (1-e)//2
    return Matrix(out)


def covariance_matrix(group, eta):
    eta = validate_eta(group,eta)
    # R^T k=eta*k follows directly from k.Rt=eta*k.t. It is equivalent
    # to the R^(-T) convention applied consistently to the whole point group.
    return Matrix.vstack(*(r.T-e*Matrix.eye(3) for r,e in zip(group.rotations,eta)))


def solve_covariant_wavevectors(group, eta):
    """Return exact connected tori, including k=0 for later stratum splitting."""
    return solve_torus(covariance_matrix(group,eta))


def solve_obstructed_1_cocycle(group, eta, k):
    """At an exact fixed k, return all gauge-inequivalent phase components."""
    eta = validate_eta(group,eta)
    k = exact_matrix(k)
    if k.shape != (3,1) or not is_integral(covariance_matrix(group,eta)*k):
        return ()
    m = cocycle_matrix(group,eta)
    rhs = Matrix([k.dot(group.cocycle[a][b]) for a in range(group.order) for b in range(group.order)])
    if -1 in eta:
        row = zeros(1,group.order)
        row[0,eta.index(-1)] = 1
        m = m.col_join(row)
        rhs = rhs.col_join(Matrix([0]))
    return solve_torus(m,rhs)


def solve_h1_eta(group, eta):
    """H^1, not Z^1: the continuous phase coboundary has already been removed."""
    return solve_obstructed_1_cocycle(group,eta,Matrix.zeros(3,1))


def joint_type1_system(group, eta):
    eta = validate_eta(group,eta)
    covariance = covariance_matrix(group,eta)
    rows = covariance.row_join(Matrix.zeros(covariance.rows,group.order))
    t = Matrix([list(-group.cocycle[a][b]) for a in range(group.order) for b in range(group.order)])
    rows = rows.col_join(t.row_join(cocycle_matrix(group,eta)))
    if -1 in eta:
        row = zeros(1,3+group.order)
        row[0,3+eta.index(-1)] = 1
        rows = rows.col_join(row)
    return Matrix(rows)


@dataclass(frozen=True)
class Type1Record:
    eta: tuple
    torus: AffineTorus
    stratum: str  # 'general', 'trim', 'zero' (zero is coplanar Type 0 only)
    spin_dimension: int = 3

    @property
    def kind(self):
        return "type0" if self.stratum == "zero" else "type1"

    @property
    def parameter_count(self):
        return self.torus.parameter_count

    @property
    def dimension(self):
        return self.torus.dimension

    @property
    def k(self):
        """Symbolic wavevector, with parameters available from symbolic()."""
        return self.torus.symbolic()[1][:3,:]

    def symbolic(self, prefix="u"):
        parameters,x = self.torus.symbolic(prefix)
        return parameters,x[:3,:],x[3:,:]

    def point(self, parameters=()):
        x = self.torus.evaluate(parameters)
        k = x[:3,:]
        if self.stratum == "general" and is_trim(k):
            raise ValueError("This point is on an excluded TRIM/zero stratum; select its separate record.")
        if self.stratum == "trim" and (not any(k) or not is_trim(k)):
            raise ValueError("Not a nonzero TRIM point.")
        return k,x[3:,:]

    def evaluate(self, t, point, parameters=(), embedded=False):
        from .exact import integer_matrix
        k,theta = self.point(parameters)
        t = integer_matrix(t)
        if t.shape != (3,1):
            raise ValueError("Expected a lattice vector.")
        m = rotation_2d(k.dot(t)+theta[point])*Matrix.diag(1,self.eta[point])
        return embed_o2(m) if self.spin_dimension == 3 or embedded else m

    def parameters_at_wavevector(self, k):
        """All parameter tuples over an exact rational k, retaining phase sheets.

        Parameter coordinates need not equal k coordinates. This method avoids
        assumptions about the Smith basis and handles screw-axis monodromy.
        """
        k = exact_matrix(k)
        if k.shape != (3,1):
            raise ValueError("Expected a rational reciprocal-coordinate column.")
        k = mod_vector(k)
        if self.stratum == 'general' and is_trim(k):
            raise ValueError("Choose the separate TRIM/zero record for this wavevector.")
        fibers = solve_torus(self.torus.basis[:3,:],k-self.torus.offset[:3,:])
        if any(f.dimension for f in fibers):
            raise ValueError("This chart has a continuous phase fiber; remove its gauge first.")
        return tuple(tuple(f.offset) for f in fibers)

    @cached_property
    def spin_key(self):
        positive = self.torus.key
        negative = self.torus.transform(-Matrix.eye(self.torus.offset.rows)).key
        return self.spin_dimension,self.stratum,self.eta,min(positive,negative)

    @lru_cache(maxsize=4096)
    def inversion_relation(self):
        """Self-identification u~v if inversion preserves this connected chart; else None."""
        negative = self.torus.transform(-Matrix.eye(self.torus.offset.rows))
        if negative.key == self.torus.key:
            return parameter_relation(self.torus,self.torus,-Matrix.eye(self.torus.offset.rows))
        return None

    def same_point(self, parameters, other, other_parameters):
        """Exact spin-conjugacy at specified parameters, not just same family.

        Return None if SymPy cannot decide integrality of exact real expressions.
        Rational parameter values always yield a boolean.
        """
        if self.spin_dimension != other.spin_dimension or self.eta != other.eta or self.stratum != other.stratum:
            return False
        self.point(parameters)
        other.point(other_parameters)
        x,y = self.torus.evaluate(parameters),other.torus.evaluate(other_parameters)
        tests = [[z.is_integer for z in v] for v in (x-y,x+y)]
        if any(all(z is True for z in values) for values in tests):
            return True
        if all(any(z is False for z in values) for values in tests):
            return False
        return None


def split_type1_strata(torus, eta, spin_dimension=3, include_zero=False):
    """Count a whole punctured torus as one family, even if disconnected.

    All special points are extracted into separate records. Connected pieces
    of the remainder are deliberately NOT separate counting units.
    """
    out = []
    n = torus.offset.rows
    constraint = Matrix.hstack(2*Matrix.eye(3),Matrix.zeros(3,n-3))
    trim_loci = torus.intersect(constraint,Matrix.zeros(3,1))
    if torus.dimension:
        # For a finite P after gauge removal, projection to k has finite fibers.
        if torus.basis[:3,:].rank() != torus.dimension:
            raise ArithmeticError("Unremoved continuous phase gauge.")
        out.append(Type1Record(eta,torus,"general",spin_dimension))
        for locus in trim_loci:
            if locus.dimension:
                raise ArithmeticError("A TRIM fiber unexpectedly has continuous phase freedom.")
            if any(locus.offset[:3,:]):
                out.append(Type1Record(eta,locus,"trim",spin_dimension))
            elif include_zero:
                out.append(Type1Record(eta,locus,"zero",spin_dimension))
    else:
        k = torus.offset[:3,:]
        if any(k):
            out.append(Type1Record(eta,torus,"trim" if is_trim(k) else "general",spin_dimension))
        elif include_zero:
            out.append(Type1Record(eta,torus,"zero",spin_dimension))
    return tuple(out)


def deduplicate_type1(records):
    return tuple({r.spin_key:r for r in records}.values())


@lru_cache(maxsize=128)
def enumerate_noncoplanar_type1(group):
    out = []
    for eta in point_gradings(group):
        for torus in solve_torus(joint_type1_system(group,eta)):
            out.extend(split_type1_strata(torus,eta))
    return deduplicate_type1(out)

