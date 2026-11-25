"""Structural normalizer and independent quotient regression checks."""
import importlib.util
import unittest
from collections import Counter
from sympy import ImmutableMatrix as M, Rational as Q
from ssg_enumeration import (example_space_group,load_standard_space_group,
    complete_automorphism_action,point_normalizer_generators,proper_linear_generators,
    enumerate_ssg,affine_automorphism,enumerate_noncoplanar_type1,
    enumerate_gradings,build_collinear_ssgs,deduplicate_automorphisms)
from ssg_enumeration.normalizers import _matrix_group


class NormalizerTests(unittest.TestCase):
    def test_finite_normalizer_orders_and_orientation_kernel(self):
        for name,order in (('P222',48),('P3',24),('P41',16),('P23',48),('P432',48)):
            g=example_space_group(name)
            generators,certificate=point_normalizer_generators(g.rotations)
            full=_matrix_group(generators)
            proper=_matrix_group(proper_linear_generators(generators))
            self.assertEqual(len(full),order,name)
            self.assertEqual(proper,frozenset(a for a in full if a.det()==1),name)

    def test_unimodular_basis_change_has_no_small_entry_cutoff(self):
        g=example_space_group('P3')
        change=M([[1,2,0],[0,1,0],[0,0,1]])
        original,_=point_normalizer_generators(g.rotations)
        transformed,_=point_normalizer_generators(tuple(change*r*change.inv() for r in g.rotations))
        expected={change*a*change.inv() for a in _matrix_group(original)}
        self.assertEqual(_matrix_group(transformed),expected)
        self.assertTrue(any(abs(x)>1 for a in expected for x in a))

    def test_extension_schreier_not_just_lifting_individual_generators(self):
        action=complete_automorphism_action(example_space_group('Pc'))
        self.assertEqual(action.certificate['extension_orbit_size'],3)
        self.assertGreater(action.certificate['schreier_edges_checked'],3)
        for a in action.generators: a.validate(example_space_group('Pc'))

    def test_full_p1_and_inversion_with_independent_origin_generators(self):
        for name,total,dimensions in (('P1',17,{'L':2,'P':5,'N':10}),('P-1',35,{'L':3,'P':9,'N':23})):
            g=example_space_group(name)
            result=enumerate_ssg(g,'full')
            self.assertEqual(len(result),total)
            self.assertEqual(Counter(s.label[0] for s in result),dimensions)
            self.assertTrue(result.normalizer_certificate['complete'])
        self.assertEqual(complete_automorphism_action(example_space_group('P-1')).certificate['origin_kernel_components'],8)

    def test_punctured_screw_family_counts_once(self):
        records=enumerate_noncoplanar_type1(example_space_group('P41'))
        axial=[r for r in records if r.eta==(1,1,1,1) and r.stratum=='general' and r.dimension==1
               and r.torus.offset[:2,:]==M.zeros(2,1)]
        self.assertEqual(len(axial),1)
        r=axial[0]
        self.assertEqual(abs(r.torus.basis[2,0]),4)
        for j in range(8):
            with self.assertRaises(ValueError): r.point([Q(j,8)])
        for j in range(8): r.point([Q(2*j+1,16)])

    @unittest.skipUnless(importlib.util.find_spec('spglib'),'Optional spglib input dependency missing')
    def test_centered_monoclinic_overlattice_and_extra_affine_maps(self):
        # Centering couples the rational plane and axis: solving GL(2,Z)
        # independently without the parent-lattice stabilizer is incorrect.
        for n in (5,8,9,12,15):
            g,_=load_standard_space_group(n)
            action=complete_automorphism_action(g)
            self.assertEqual(action.certificate['eigenlattice_index'],2)
            self.assertGreater(action.certificate['lattice_orbit_size'],1)
            for a in action.generators: a.validate(g)
        # Large powers of shear and independent half origins must not create
        # new grading identifications beyond the complete quotient.
        g=example_space_group('P-1')
        action=complete_automorphism_action(g)
        records=build_collinear_ssgs(enumerate_gradings(g))
        extra=(affine_automorphism(g,M([[1,7,0],[0,1,0],[0,0,1]]),[Q(1,2),Q(1,2),0]),)
        first=deduplicate_automorphisms(records,action.generators)
        second=deduplicate_automorphisms(records,action.generators+extra)
        self.assertEqual(first.orbits,second.orbits)


if __name__=='__main__': unittest.main()
