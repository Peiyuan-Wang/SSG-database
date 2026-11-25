"""Published Xiao IDs for the standard 230-parent SSGclassify catalogue.

A 17-category label alone cannot specify an individual representation class.
Full local IDs have the form SG143/N.1.2/0001 and are stable within the bundled
catalogue version. The published final serial is read from the matched source,
never manufactured from our enumeration order.
"""
from dataclasses import dataclass
from functools import lru_cache
import gzip
import hashlib
from importlib.resources import files
import json
import re

from .labels import LABELS
from .type1 import Type1Record
from .serialization import matrix_data


@dataclass(frozen=True)
class XiaoCorrespondence:
    our_label: str
    space_group: int
    category: str
    class_index: int
    xiao_label: str
    xiao_type: int
    constituents: tuple
    parameter_count: int
    orbit_index: int
    chart_index: int

    @property
    def formal_label(self):
        """Full HM spin name; our_label remains the stable short identifier."""
        from .naming import name_for_label
        return name_for_label(self.our_label).text

    @property
    def name(self):
        from .naming import name_for_label
        return name_for_label(self.our_label)


@lru_cache(maxsize=1)
def _catalogue():
    path = files('ssg_enumeration').joinpath('data/xiao_correspondence.json.gz')
    payload = json.loads(gzip.decompress(path.read_bytes()))
    rows = tuple(XiaoCorrespondence(
        row[0],row[1],row[2],row[3],row[4],int(row[4].split('.')[1]),
        tuple(row[5]),row[6],row[7],row[8]) for row in payload['rows'])
    if len(rows) != 67475 or len({r.our_label for r in rows}) != len(rows) or len({r.xiao_label for r in rows}) != len(rows):
        raise RuntimeError('The bundled Xiao correspondence is incomplete or not bijective')
    return (rows,{r.our_label:r for r in rows},{r.xiao_label:r for r in rows},
            payload['representative_keys'],payload['metadata'])


def _space_group(number):
    if isinstance(number,bool) or not isinstance(number,int) or not 1 <= number <= 230:
        raise ValueError('space_group must be an integer in 1..230')
    return number


def _full_label(label, space_group=None, class_index=None):
    if not isinstance(label,str):
        raise TypeError('Use a full local label, or a category with space_group and class_index')
    if label in LABELS:
        if space_group is None or class_index is None:
            raise ValueError('A category is not a unique class. Supply space_group and class_index, '
                             'or use xiao_correspondences(category=...) to list its classes.')
        _space_group(space_group)
        if isinstance(class_index,bool) or not isinstance(class_index,int) or class_index < 1:
            raise ValueError('class_index must be a positive, one-based integer')
        return f'SG{space_group:03d}/{label}/{class_index:04d}'
    if space_group is not None or class_index is not None:
        raise ValueError('Do not combine a full local label with extra identifiers')
    match = re.fullmatch(r'SG(\d{1,3})/([LPN]\.\d+(?:\.\d+)?)/(\d+)',label)
    if not match:
        raise ValueError('Expected a label such as SG143/N.1.2/0001')
    number,category,index = int(match[1]),match[2],int(match[3])
    _space_group(number)
    if category not in LABELS or index < 1:
        raise ValueError('Invalid category or class index')
    return f'SG{number:03d}/{category}/{index:04d}'


def to_xiao_label(label, *, space_group=None, class_index=None):
    """Return the published complete ID for a complete local class identifier.

    Examples: to_xiao_label('SG143/N.1.2/0001'), or
    to_xiao_label('N.1.2', space_group=143, class_index=1).
    """
    if isinstance(label,str) and label.startswith(('L: ', 'P: ', 'N: ')):
        if space_group is not None or class_index is not None:
            raise ValueError('Do not combine a formal name with extra identifiers')
        from .naming import _name_catalogue
        try: return _name_catalogue()[2][label]['xiao']
        except KeyError: raise KeyError('Formal name is not a canonical catalogue name') from None
    key = _full_label(label,space_group,class_index)
    try:
        return _catalogue()[1][key].xiao_label
    except KeyError:
        raise KeyError(f'No class {key} in the bundled standard catalogue') from None


def from_xiao_label(label, *, formal=False):
    """Return the old stable ID, or the formal HM name with formal=True."""
    if formal:
        from .naming import name_for_label
        return name_for_label(label).text
    try:
        return _catalogue()[2][label].our_label
    except (KeyError,TypeError):
        raise KeyError(f'Unknown published Xiao ID: {label!r}') from None


def xiao_correspondences(*, category=None, space_group=None):
    """List matched class-to-class rows, optionally restricted by category/parent."""
    if category is not None and category not in LABELS:
        raise ValueError('Unknown 17-category label')
    if space_group is not None:
        _space_group(space_group)
    return tuple(row for row in _catalogue()[0]
                 if (category is None or row.category == category)
                 and (space_group is None or row.space_group == space_group))


def xiao_mapping_metadata():
    """Return an independent copy of source and matching provenance."""
    return json.loads(json.dumps(_catalogue()[4]))


def _chart_signature(chart):
    payload = {k:v for k,v in chart.items() if k not in ('chart','label')}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _record_signature(record):
    item = {'dimension':record.dimension}
    if record.grading is not None:
        item['grading'] = {'k':matrix_data(record.grading.k),'section_bits':record.grading.bits}
    r = record.representation
    if isinstance(r,Type1Record):
        item['representation'] = {'kind':r.kind,'native_dimension':r.spin_dimension,
            'eta':r.eta,'stratum':r.stratum,'offset':matrix_data(r.torus.offset),
            'basis':matrix_data(r.torus.basis),'parameter_count':r.parameter_count,
            'excluded':'all k with 2*k integral' if r.stratum == 'general' else None}
    elif r is not None:
        item['representation'] = {'kind':r.kind,'native_dimension':r.spin_dimension,
            'image':r.image,'translations':[matrix_data(m) for m in r.translations],
            'sections':[matrix_data(m) for m in r.sections],
            'wavevectors':[matrix_data(k) for k in r.wavevectors],'kernel':r.kernel}
    return _chart_signature(item)


def xiao_label_for_record(space_group, record):
    """Look up a standard representative from enumerate_ssg(..., 'full').

    This is a catalogue lookup, not a recognizer for arbitrary coordinate
    systems or custom bases. Such inputs require explicit representation matching.
    """
    _space_group(space_group)
    key = f'{space_group}:{_record_signature(record)}'
    try:
        return _catalogue()[3][key]
    except KeyError:
        from .naming import label_for_record
        return to_xiao_label(label_for_record(space_group,record))
