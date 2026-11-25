"""python example_labels.py -- formal names, exact matrices and Xiao IDs."""
from sympy import Rational
from ssg_enumeration import (name_for_label, parse_label, to_xiao_label,
                             label_for_record, naming_metadata)


def main():
    name = name_for_label('N143.5.2')
    print('正式名称:', name.text)
    print('LaTeX:', name.latex)
    print('Xiao:', to_xiao_label(name.text))
    parsed = parse_label(name.text)
    record = parsed.to_record()
    print('17 类类型:', record.category)
    print('回算后的名称:', label_for_record(name.space_group,record))
    parameters = [Rational(1,11)]*name.parameter_count
    print('第一个非恒等截面的自旋矩阵:')
    print(parsed.evaluate(point=1,parameters=parameters))
    screw = parse_label('N: ^{(0,2*u0,0)}P 2_1 | u0 in R/Z; 2*C^T*k notin Z^3')
    print('P21 螺旋族:',screw.text)
    print('u0=1/6 的螺旋操作:',screw.evaluate(point=1,parameters=[Rational(1,6)]))
    print('目录分类数:',naming_metadata()['class_count'])


if __name__ == '__main__':
    main()
