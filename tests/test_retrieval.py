import tempfile
import unittest
from pathlib import Path
from ssg_database.retrieval import SearchDatabase, build_database

ROOT=Path(__file__).resolve().parents[1]


class RetrievalTests(unittest.TestCase):
    def test_hm_display_uses_overbars_and_subscripts(self):
        from ssg_database.retrieval import hm_display
        self.assertEqual(hm_display('P -1'),'P1̅')
        self.assertEqual(hm_display('P 4_2/m'),'P4₂/m')
        self.assertEqual(hm_display('R -3 2/c'),'R3̅2/c')
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.path=Path(cls.tmp.name)/'small.sqlite'
        build_database(cls.path,ROOT/'tests/fixtures/retrieval',parents=[1,4,27])
        cls.db=SearchDatabase(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.db.close();cls.tmp.cleanup()

    def test_tree_totals_and_no_omitted_pagination(self):
        nodes=self.db.children([])
        self.assertEqual({n['value'] for n in nodes},{'1','4','27'})
        first=self.db.search({'parent':1},limit=5)
        allrows=[]
        for offset in range(0,first['total'],5):
            allrows+=self.db.search({'parent':1},offset=offset,limit=5)['rows']
        self.assertEqual(len({r['id'] for r in allrows}),17)

    def test_constraints_are_enforced(self):
        for filters in ({},{'k1':'0,0,1/2'},{'parent':4,'point_group':'mmm'},
                        {'parent':231},{'bravais':'mP','k1':'bad'}, {'typo':'value'}):
            with self.subTest(filters=filters),self.assertRaises(ValueError):
                self.db.search(filters)
        self.assertEqual(self.db.parent(4)['point_group'],'2')

    def test_equivalent_antitranslations_are_searchable(self):
        a=self.db.search({'parent':1,'bravais':'aP','dimension':'L','kchi':'1/2,0,0'})
        b=self.db.search({'parent':1,'bravais':'aP','dimension':'L','kchi':'0,0,1/2'})
        self.assertEqual(a['total'],1)
        self.assertEqual([r['id'] for r in a['rows']],[r['id'] for r in b['rows']])

    def test_family_wavevector_membership_excludes_trim(self):
        a=self.db.search({'parent':4,'bravais':'mP','category':'P.1.2','k1':'0,1/3,0'})
        b=self.db.search({'parent':4,'bravais':'mP','category':'P.1.2','k1':'0,1/2,0'})
        self.assertGreater(a['total'],0)
        self.assertEqual(b['total'],0)

    def test_detail_recovers_new_properties_and_xiao_alias(self):
        detail=self.db.detail('L1.1.1')
        self.assertEqual(detail['crystal']['q_name'],'1')
        self.assertEqual(detail['crystal']['kernel'],[0])
        self.assertEqual(len(detail['hierarchy']),5)
        self.assertIn('liu_latex',detail)

    def test_concrete_wave_and_quotient_filters_use_same_members(self):
        base={'parent':27,'bravais':'oP','category':'P.1.2','k1':'0,0,1/3'}
        impossible=self.db.search(dict(base,q_name='C2 × C2'))
        actual=self.db.search(dict(base,q_name='C2'))
        self.assertNotIn('P27.5.2',{r['xiao'] for r in impossible['rows']})
        self.assertIn('P27.5.2',{r['xiao'] for r in actual['rows']})


if __name__=='__main__': unittest.main()
