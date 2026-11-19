import unittest
from sympy import ImmutableMatrix as M,Rational as Q
from ssg_enumeration import example_space_group
from ssg_enumeration.type1 import enumerate_noncoplanar_type1
from ssg_enumeration.type0 import enumerate_noncoplanar_type0
from ssg_enumeration.validation import spin_equivalent_matrices
from audits.continuous_branches.zero_bridge import path_certificate,completed_evaluate


class ZeroBridgeProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.group=example_space_group('P41')
        cls.rep=next(r for r in enumerate_noncoplanar_type1(cls.group)
            if r.parameter_count==1 and r.eta==(1,1,1,1)
            and r.torus.offset==M.zeros(7,1)
            and r.torus.basis==M([0,0,4,0,1,2,3]))

    def test_exact_path_crosses_zero_without_breaking_joint_equations(self):
        x,delta=path_certificate(self.group,self.rep,[Q(1,16)],[Q(5,16)])
        self.assertEqual(x[2],Q(1,4)); self.assertEqual(delta[2],1)
        at_zero=x+Q(3,4)*delta
        self.assertEqual(at_zero[2],1)
        self.assertEqual(at_zero[4],Q(1,4))
        self.assertEqual(completed_evaluate(self.rep,[Q(1,4)],[0,0,1],0),M.eye(3))
        self.assertEqual(completed_evaluate(self.rep,[Q(1,4)],[0,0,0],1),M([[0,-1,0],[1,0,0],[0,0,1]]))

    def test_zero_is_a_separate_type0_member_not_a_generic_endpoint(self):
        with self.assertRaises(ValueError):self.rep.point([Q(1,4)])
        matrices=tuple(completed_evaluate(self.rep,[Q(1,4)],[0,0,0],p)
                       for p in range(self.group.order))
        self.assertTrue(any(spin_equivalent_matrices(matrices,r.sections)
                            for r in enumerate_noncoplanar_type0(self.group)))

    def test_nonzero_trim_remains_separate(self):
        with self.assertRaises(ValueError):self.rep.point([Q(1,8)])
        special=self.rep.torus.evaluate([Q(1,8)])
        self.assertTrue(any(r.stratum=='trim' and r.eta==self.rep.eta
                            and (r.torus.contains(special) or r.torus.contains(-special))
                            for r in enumerate_noncoplanar_type1(self.group)))

    def test_same_wavevector_does_not_join_distinct_joint_components(self):
        records=enumerate_noncoplanar_type1(example_space_group('P4'))
        axial=[r for r in records if r.parameter_count==1 and r.eta==(1,1,1,1)
               and r.torus.offset[:3,:]==M.zeros(3,1)]
        a=next(r for r in axial if r.torus.offset[4]==0)
        b=next(r for r in axial if r.torus.offset[4] in (Q(1,4),Q(3,4)))
        self.assertNotEqual(a.torus.key,b.torus.key)
        self.assertNotEqual(a.spin_key,b.spin_key)
        self.assertEqual(a.torus.basis[4,0],0)
        self.assertEqual(b.torus.basis[4,0],0)

if __name__=='__main__':unittest.main()
