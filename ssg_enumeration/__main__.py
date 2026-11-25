"""Run `python -m ssg_enumeration --group P21` after importing/installing the package."""
import argparse
import json
from . import example_space_group,enumerate_ssg,save_catalog


def main():
    parser = argparse.ArgumentParser(description='Exact SSG family enumeration')
    parser.add_argument('--group',default='P1',help='Built-in example name, e.g. P1, P21, Pc, P31, P41')
    parser.add_argument('--p1-full',action='store_true',help='Use the full SL(3,Z) outer group for P1')
    parser.add_argument('--output',help='Export exact charts and relations as JSON')
    args = parser.parse_args()
    group = example_space_group(args.group)
    result = enumerate_ssg(group,'p1_full' if args.p1_full else None)
    if args.output:
        save_catalog(result,args.output)
    print(json.dumps(result.summary(),ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
