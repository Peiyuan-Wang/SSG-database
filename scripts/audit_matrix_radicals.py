"""Audit radical parsing for catalogue generators and exact axial rotations.

The audit covers every non-axial catalogue generator set and the complete spin
closure it generates.  For axial names it checks exact sine/cosine values for
single rational parameter denominators up to 48 combined with every possible
catalogue offset denominator.  Arbitrary multi-parameter denominator products,
future naming conventions and visual rendering on every OS are outside this
finite audit.
"""
import argparse
from fractions import Fraction
from math import lcm
from pathlib import Path
import json
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sympy import Rational,pi,sin,cos
from ssg_database.retrieval import _unpack
from ssg_enumeration.naming import _spin_matrix,_axial_parts
from ssg_enumeration.crystal import _closure
from ssg_database.desktop import MatrixDelegate


def count_roots(value):
    return sum(1+count_roots(text) for kind,text in MatrixDelegate.expression_parts(value) if kind=='root')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();start=time.monotonic();conn=sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True)
    signatures=set();axial_tokens=set();offset_denominators=set();basis_denominators=set();classes=0
    try:
        for family,blob in conn.execute('SELECT family,data FROM classes'):
            classes+=1;name=_unpack(blob)['name_data']
            if name['translation_kind']=='axial':
                axial_tokens.update(name['spins'])
                offset_denominators.update(Fraction(x).denominator for x in name['q'])
                basis_denominators.update(Fraction(x).denominator for row in name['basis'] for x in row)
            elif not family:
                signatures.add(tuple(sorted(set(name['spins']+name['translation_spins']))))
    finally:conn.close()
    spin_denominators={int(_axial_parts(_spin_matrix(token))[0].q) for token in axial_tokens}
    phase_lcm=lcm(*(offset_denominators|basis_denominators|spin_denominators))
    values=set();matrix_count=0
    for signature in signatures:
        generators=tuple(_spin_matrix(token) for token in signature) or (_spin_matrix('1'),)
        for matrix in _closure(generators):
            matrix_count+=1;values.update(str(value) for value in matrix)
    phases={Rational(p,lcm(q,phase_lcm)) for q in range(1,49) for p in range(lcm(q,phase_lcm))}
    for phase in phases:
        values.add(str(sin(2*pi*phase)));values.add(str(cos(2*pi*phase)))
    radicals=sorted(value for value in values if 'sqrt(' in value)
    invalid=[value for value in radicals if count_roots(value)!=value.count('sqrt(')]
    result={'classes':classes,'nonaxial_generator_sets':len(signatures),'closure_matrices':matrix_count,
            'axial_spin_tokens':len(axial_tokens),'offset_denominators':sorted(offset_denominators),
            'basis_denominators':sorted(basis_denominators),'spin_phase_denominators':sorted(spin_denominators),
            'single_parameter_phase_count':len(phases),'distinct_radical_expressions':len(radicals),
            'invalid_radical_parses':invalid,'seconds':round(time.monotonic()-start,2),
            'scope':'All catalogue non-axial closures and single rational parameter denominators <=48; not a visual or arbitrary multi-parameter exhaustive audit.'}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 1 if invalid else 0


if __name__=='__main__':raise SystemExit(main())
