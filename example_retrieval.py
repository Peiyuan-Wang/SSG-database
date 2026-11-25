"""Read-only spin space group queries without launching the desktop application."""
from argparse import ArgumentParser
from pathlib import Path
from ssg_database.retrieval import SearchDatabase

parser = ArgumentParser(description=__doc__)
parser.add_argument('database', nargs='?', type=Path,
    default=Path(__file__).parent / 'output/retrieval/SSGclassify.sqlite')
db=SearchDatabase(parser.parse_args().database)
result=db.search({'parent':4,'bravais':'mP','category':'P.1.2','k1':'0,1/3,0'})
print('匹配数：',result['total'])
for row in result['rows']:
    print(row['xiao'],row['display_name'],'Q =',row['q_name'],'K =',row['k_name'])
    detail=db.detail(row['id'])
    print('一般参数的核：',detail['crystal']['kernel'])
    break
db.close()
