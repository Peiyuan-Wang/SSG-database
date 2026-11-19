"""Create a compact database while preserving every precompiled SVG byte."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ssg_database.formula_storage import compact_formula_database

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('source',type=Path)
parser.add_argument('destination',type=Path)
parser.add_argument('--block-size',type=int,default=64)
args=parser.parse_args()
print(json.dumps(compact_formula_database(args.source,args.destination,block_size=args.block_size),indent=2))
