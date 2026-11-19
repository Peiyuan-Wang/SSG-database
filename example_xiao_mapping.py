"""Run: python example_xiao_mapping.py (install ssg-enumeration first)."""
from ssg_enumeration import (to_xiao_label, from_xiao_label,
                             xiao_correspondences, xiao_mapping_metadata)


def main():
    local = 'SG143/N.1.2/0002'
    published = to_xiao_label(local)
    print(f'{local} -> {published}')
    print(f'{published} -> {from_xiao_label(published)}')
    print(to_xiao_label('N.1.2', space_group=143, class_index=2))
    print('\nP143, category N.1.2:')
    for row in xiao_correspondences(space_group=143, category='N.1.2'):
        print(row.formal_label, row.xiao_label, row.our_label, ' + '.join(row.constituents))
    metadata = xiao_mapping_metadata()
    print('\nTotal:',metadata['class_count'], 'Parents:',metadata['parent_count'])


if __name__ == '__main__':
    main()
