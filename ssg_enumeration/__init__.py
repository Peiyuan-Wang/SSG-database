"""Exact SSG enumeration. Angles are in turns (2*pi), wavevectors in reciprocal coordinates."""
__version__ = "0.9.17"

from .exact import trim_vectors, is_trim, mod1, mod_vector, permutation_matrix, oriented_permutation
from .gf2 import BinarySolution, solve_gf2
from .torus import (AffineTorus, ParameterRelation, smith_decomposition, reduce_congruences,
    annihilator, solve_torus, parameter_relation)
from .groups import SpaceGroup, from_generators, example_space_group
from .gradings import Grading, build_grading_system, enumerate_gradings, point_gradings
from .finite import (element_order, generated_subgroup, normal_closure, normal_subgroups,
    quotient_group, small_generating_set, find_isomorphism)
from .representations import MatrixRepresentation, rotation_2d, embed_o2
from .type0 import rotation_group_catalog, enumerate_noncoplanar_type0
from .type1 import (Type1Record, cocycle_matrix, covariance_matrix, gauge_matrix,
    solve_covariant_wavevectors, solve_obstructed_1_cocycle, solve_h1_eta,
    joint_type1_system, split_type1_strata, deduplicate_type1, enumerate_noncoplanar_type1)
from .type2 import (invariant_kernel_vectors, annihilator_trims, induced_permutations,
    build_twisted_binary_system, solve_twisted_binary_cocycle,
    monomial_spin_key, deduplicate_monomial, enumerate_noncoplanar_type2)
from .coplanar import enumerate_coplanar_type0, enumerate_coplanar_type1, enumerate_coplanar_type2
from .labels import LABELS, label_17
from .records import SSG, build_collinear_ssgs, combine
from .automorphisms import (SpaceGroupAutomorphism, affine_automorphism, p1_outer_generators,
    transform_grading, type1_pullback_matrix, transform_representation, transform_ssg)
from .normalizers import (CompleteAutomorphismAction, invariant_metric_dimension,
    lattice_isometries, point_normalizer_generators, proper_linear_generators,
    complete_automorphism_action)
from .deduplication import (EnumerationResult, EquivalenceDecision, QuotientRelation, spin_key,
    deduplicate_spin_conjugation, deduplicate_automorphisms, equivalence_loci,
    stabilizer_loci, rational_p1_wavevector_orbit_key, verify_equivalence_witness)
from .validation import validate_representation, spin_equivalent_matrices
from .enumerate import enumerate_ssg
from .serialization import catalog_dict, save_catalog, record_data
from .database import standard_hall_numbers, primitive_operations, load_standard_space_group, space_group_from_number
from .xiao import (XiaoCorrespondence, to_xiao_label, from_xiao_label,
    xiao_correspondences, xiao_mapping_metadata, xiao_label_for_record)
from .naming import (SSGName, canonical_torus, naming_setting, name_for_label,
    label_for_record, name_for_chart, parse_label, naming_metadata)
from .crystal import spin_crystal_class, analyze_chart, conjugate_finite_pairs

__all__ = [name for name, value in list(globals().items())
           if not name.startswith('_') and (callable(value) or name == 'LABELS')]

