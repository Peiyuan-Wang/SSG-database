import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from ssg_enumeration import LABELS,example_space_group,enumerate_ssg
from ssg_enumeration.census import aggregate_census,write_census_tables


class CensusTests(unittest.TestCase):
    def row(self,number,name):
        result = enumerate_ssg(example_space_group(name))
        labels = {label:sum(r.label == label for r in result) for label in LABELS}
        continuous = {label:sum(r.label == label and r.parameter_count > 0 for r in result) for label in LABELS}
        return {'number':number,'international_short':name,'hall_number':number,'point_group':'test',
                'point_order':1,'status':'complete','labels':labels,'continuous_labels':continuous,
                'L':sum(n for label,n in labels.items() if label[0]=='L'),
                'P':sum(n for label,n in labels.items() if label[0]=='P'),
                'N':sum(n for label,n in labels.items() if label[0]=='N'),
                'total':len(result),'continuous_family_count':sum(continuous.values()),
                'discrete_count':len(result)-sum(continuous.values())}

    def test_partial_never_claims_complete(self):
        row=self.row(1,'P1')
        summary=aggregate_census([row],range(1,231),'test')
        self.assertEqual(summary['status'],'partial')
        self.assertEqual(summary['completed_parents'],1)
        self.assertFalse(summary['full_out_plus_applied'])
        self.assertEqual(summary['totals']['total'],173)

    def test_aggregation_and_csv(self):
        rows=[self.row(1,'P1'),self.row(2,'P-1')]
        summary=aggregate_census(rows,[1,2],'test')
        self.assertEqual(summary['status'],'complete')
        self.assertEqual(summary['totals']['total'],1158)
        self.assertEqual(sum(summary['labels'].values()),1158)
        self.assertEqual(summary['totals']['discrete_count']+summary['totals']['continuous_family_count'],1158)
        with TemporaryDirectory() as d:
            write_census_tables(summary,d)
            payload=json.loads((Path(d)/'summary.json').read_text())
            with (Path(d)/'by_type.csv').open(encoding='utf-8-sig') as f: types=list(csv.DictReader(f))
            with (Path(d)/'by_space_group.csv').open(encoding='utf-8-sig') as f: parents=list(csv.DictReader(f))
        self.assertEqual(len(types),17)
        self.assertEqual(len(parents),2)
        self.assertEqual(payload['totals'],summary['totals'])
        self.assertEqual(sum(int(r['total']) for r in types),1158)


if __name__ == '__main__': unittest.main()
