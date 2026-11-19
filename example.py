"""Import the installed package, classify P1, and evaluate one continuous family.

Run from the project root after: python -m pip install .
    python example.py
    python example.py --output example_output
The example uses built-in exact P1 operations; spglib is not required.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from sympy import Rational, pprint
import ssg_enumeration as ssg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional folder for the full catalogue and summary')
    args = parser.parse_args()

    group = ssg.example_space_group('P1')
    result = ssg.enumerate_ssg(group, automorphisms='full', verify=True)
    counts = Counter(record.label[0] for record in result)
    print(f'Package version: {ssg.__version__}')
    print(f'Parent space group: {group.name}')
    print(f'Spatial quotient: {result.spatial_scope}')
    print(f'L={counts["L"]}, P={counts["P"]}, N={counts["N"]}, total={len(result)}')
    print(f'Continuous parameter families: {sum(r.parameter_count > 0 for r in result)}')
    print('Counts by the 17 types:')
    for label in ssg.LABELS:
        print(f'  {label}: {len(result.by_label(label))}')

    # One coplanar continuous family, with exact wavevector (1/3, 0, 0).
    # Smith coordinates need not equal wavevector coordinates.
    family = result.by_label('P.1.2')[0]
    print('\nFormal family name:', family.name(1).text)
    parameters = family.representation.parameters_at_wavevector([Rational(1, 3), 0, 0])[0]
    print('\nTranslation by (1,0,0) at wavevector (1/3,0,0), in the spin plane:')
    pprint(family.evaluate([1, 0, 0], parameters=parameters, embedded=False))

    # These are genuine checks of different parameter values, not just labels.
    i = result.locate(family)
    rotated = family.representation.parameters_at_wavevector([0, Rational(1, 3), 0])[0]
    different = family.representation.parameters_at_wavevector([Rational(1, 4), 0, 0])[0]
    print('Equivalent to wavevector (0,1/3,0):', result.equivalent_points(i, parameters, i, rotated).status)
    print('Equivalent to wavevector (1/4,0,0):', result.equivalent_points(i, parameters, i, different).status)
    assert len(result) == 17 and counts == {'L': 2, 'P': 5, 'N': 10}
    assert result.normalizer_certificate['complete']

    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'P1_summary.json').write_text(
            json.dumps(result.summary(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        ssg.save_catalog(result, args.output / 'P1_catalogue.json', space_group=1)
        print(f'Exact summary, parameter domains and equivalence relations saved to: {args.output}')


if __name__ == '__main__':
    main()
