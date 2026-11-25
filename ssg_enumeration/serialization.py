"""Portable, human-readable exact catalog export (no executable pickles)."""
import json
from pathlib import Path
from .type1 import Type1Record


def matrix_data(matrix):
    return {'shape':[matrix.rows,matrix.cols],
            'entries':[[str(matrix[i,j]) for j in range(matrix.cols)] for i in range(matrix.rows)]}


def record_data(ssg):
    """Exact representation payload, independent of a catalogue row number."""
    item = {'dimension':ssg.dimension}
    if ssg.grading is not None:
        item['grading'] = {'k':matrix_data(ssg.grading.k),'section_bits':ssg.grading.bits}
    r = ssg.representation
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
    return item


def catalog_dict(result, *, space_group=None):
    charts = [dict(chart=i,label=ssg.label,**record_data(ssg)) for i,ssg in enumerate(result.charts)]
    if space_group is not None:
        from .naming import label_for_record, naming_setting
        from .xiao import to_xiao_label, from_xiao_label
        setting = naming_setting(space_group)
        for item,ssg in zip(charts,result.charts):
            formal = label_for_record(space_group,ssg)
            published = to_xiao_label(formal)
            item.update(formal_label=formal,category=item['label'],
                        catalogue_id=from_xiao_label(published),xiao_label=published,
                        naming_version='1.1',hall_number=setting['hall_number'])
    relations = []
    for rel in result.relations:
        item = {'source':rel.source,'target':rel.target,'name':rel.name}
        if rel.parameters is not None:
            item['parameter_equation'] = {
                'source_matrix':matrix_data(rel.parameters.source),
                'target_matrix':matrix_data(rel.parameters.target),
                'rhs':matrix_data(rel.parameters.rhs),
                'convention':'source_matrix*u + target_matrix*v = rhs mod 1'}
            item['ambient_map'] = matrix_data(rel.ambient_map)
        relations.append(item)
    automorphisms = [{'name':a.name,'linear':matrix_data(a.linear),'point_permutation':a.permutation,
                      'section_shifts':[matrix_data(u) for u in a.shifts]} for a in result.automorphisms]
    return {'schema':'ssg-enumeration-0.1','units':'reciprocal lattice coordinates; phases in turns',
            'summary':result.summary(),'charts':charts,'orbits':result.orbits,'relations':relations,
            'automorphisms':automorphisms}


def save_catalog(result, path, *, space_group=None):
    path = Path(path)
    path.write_text(json.dumps(catalog_dict(result,space_group=space_group),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return path

