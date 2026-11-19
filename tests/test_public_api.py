import unittest
import json
from tempfile import TemporaryDirectory
from pathlib import Path
from sympy import Rational as Q,ImmutableMatrix as M
import ssg_enumeration as ssg


class PublicApiTests(unittest.TestCase):
    def test_exports(self):
        self.assertGreaterEqual(len(ssg.__all__),65)
        self.assertTrue(all(hasattr(ssg,name) for name in ssg.__all__))

    def test_custom_input_and_progress(self):
        group = ssg.SpaceGroup((M.eye(3),M.diag(-1,1,-1)),(M.zeros(3,1),M([0,Q(1,2),0])),name='custom P21')
        events = []
        result = ssg.enumerate_ssg(group,progress=lambda name,n:events.append(name))
        self.assertEqual(events, ['gradings','noncoplanar_type0','noncoplanar_type1','noncoplanar_type2',
                                 'coplanar_type0','coplanar_type1','coplanar_type2','quotient_and_labels'])
        self.assertTrue(result.verified)

    def test_json_export(self):
        result = ssg.enumerate_ssg(ssg.example_space_group('P1'))
        with TemporaryDirectory() as directory:
            path = ssg.save_catalog(result,Path(directory)/'catalog.json')
            payload = json.loads(path.read_text())
        self.assertEqual(len(payload['charts']),173)
        self.assertEqual(payload['summary'],result.summary())


if __name__ == '__main__': unittest.main()
