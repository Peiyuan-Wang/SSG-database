"""Safe parser for real parameter values entered in the desktop interface."""
import ast
from sympy import Float,Integer,pi,sqrt


def parse_parameters(text,count):
    parts=text.split(',')
    if len(parts)!=count or any(not p.strip() for p in parts):
        raise ValueError(f'Enter exactly {count} parameter value(s), separated by commas.')
    if len(text)>1024:raise ValueError('Parameter input is too long.')
    def parse(part):
        part=part.strip()
        approximate=False
        def visit(node):
            nonlocal approximate
            if isinstance(node,ast.Constant) and type(node.value) in (int,float):
                if isinstance(node.value,float):
                    approximate=True
                    return Float(ast.get_source_segment(part,node))
                if abs(node.value)>10**12:raise ValueError('Number is too large.')
                return Integer(node.value)
            if isinstance(node,ast.Name) and node.id=='pi':approximate=True;return pi
            if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
                value=visit(node.operand);return -value if isinstance(node.op,ast.USub) else value
            if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow)):
                a,b=visit(node.left),visit(node.right)
                if isinstance(node.op,ast.Add):return a+b
                if isinstance(node.op,ast.Sub):return a-b
                if isinstance(node.op,ast.Mult):return a*b
                if isinstance(node.op,ast.Div):
                    if b==0:raise ValueError('Division by zero.')
                    return a/b
                if not b.is_Integer or abs(b)>12:raise ValueError('Invalid exponent.')
                return a**int(b)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='sqrt' and len(node.args)==1 and not node.keywords:
                approximate=True;return sqrt(visit(node.args[0]))
            raise ValueError('Use numbers, fractions, pi, or sqrt(...).')
        try:
            value=visit(ast.parse(part.strip(),mode='eval').body)
            if value.is_real is not True or value.is_finite is not True or abs(float(value))>10**12:
                raise ValueError('Parameters must be finite real numbers of reasonable size.')
            if value.is_Rational and value.q>48:approximate=True
            return value,approximate
        except (SyntaxError,TypeError,OverflowError,ZeroDivisionError,RecursionError) as exc:
            raise ValueError('Invalid parameter value.') from exc
    parsed=[parse(p) for p in parts]
    return tuple(value for value,_ in parsed),any(flag for _,flag in parsed)
