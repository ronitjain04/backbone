"""Bounded, deterministic parsing. Nothing submitted is executed as Python."""
import ast
import operator
import re
from fractions import Fraction

class Unclear(ValueError): pass


def parse_number(text):
    text=text.strip().replace('−','-').replace('×','*').replace('÷','/').replace('^','**')
    if len(text)>300: raise Unclear('Use a shorter calculation.')
    text=re.sub(r'\bx([0-9a-fA-F]+)\b',r'0x\1',text)
    text=re.sub(r'#(?=-?\d)','',text)
    try:tree=ast.parse(text,mode='eval')
    except (SyntaxError,ValueError):raise Unclear('Use numbers and arithmetic operators.') from None
    if len(list(ast.walk(tree)))>80:raise Unclear('Use a shorter calculation.')
    def visit(node):
        if isinstance(node,ast.Expression):return visit(node.body)
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            if abs(node.value)>2**64:raise Unclear('This value is outside the exercise range.')
            return Fraction(str(node.value))
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            return visit(node.operand)*(1 if isinstance(node.op,ast.UAdd) else -1)
        if isinstance(node,ast.BinOp):
            a,b=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Pow):
                if b.denominator!=1 or abs(b)>32 or abs(a)>2**32:raise Unclear('Use a small integer exponent.')
                value=a**int(b)
            else:
                op={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}.get(type(node.op))
                if op is None:raise Unclear('Use +, -, *, /, or a small power.')
                value=op(a,b)
            if abs(value)>2**64:raise Unclear('This calculation is outside the exercise range.')
            return value
        raise Unclear('Use numbers and arithmetic operators, without names or function calls.')
    try:return visit(tree)
    except (ZeroDivisionError,OverflowError,RecursionError):raise Unclear('I cannot interpret that calculation safely. Check the operations.') from None


def verdict(status,message,**extra):
    return {'status':status,'message':message,'misconception':None,'sources':[],'checker_version':'practice-1',**extra}


def check(exercise, answer, work=''):
    spec=exercise['checker']; kind=spec['kind'];text=answer.strip()
    if not text:return verdict('needs_clarification','Add a final answer so we can check the result separately from your reasoning.')
    if kind=='explanation':return verdict('needs_clarification','This explanation needs a source-grounded rubric assessment.',requires_rubric=True)
    if kind=='lc3_program':
        from .lc3 import check_program
        return check_program(spec,text)
    try:
        if kind=='choice':
            normalized=text.lower().rstrip('.!').strip()
            accepted=normalized in spec['accepted']
            if not accepted and normalized not in {'yes','no','true','false','overflow','no overflow','n','z','p','negative','zero','positive'}:
                raise Unclear('Give one unambiguous choice in Final answer, and put your explanation in Show your work.')
        else:
            unit_match=re.search(r'\s*([a-zA-Z]+)\s*$',text)
            # Hexadecimal digits belong to the number, not a trailing unit.
            if re.fullmatch(r'(?:0[xX]|x)[0-9a-fA-F]+',text):unit_match=None
            unit=unit_match.group(1) if unit_match else None
            expr=text[:unit_match.start()] if unit_match else text
            if spec.get('bits') and re.fullmatch('[01]{'+str(spec['bits'])+'}',expr):expr='0b'+expr
            value=parse_number(expr)
            if spec.get('bits'):
                if value<0 or value>=2**spec['bits'] or value.denominator!=1:raise Unclear('Give a nonnegative bit pattern within the stated word width; use 0b or x for binary/hex.')
            if unit:
                target=spec.get('unit')
                if target in ('bytes','bits','KiB'):
                    factors={'bytes':Fraction(1),'byte':Fraction(1),'B':Fraction(1),'bits':Fraction(1,8),'bit':Fraction(1,8),'KiB':Fraction(1024)}
                    if unit not in factors:raise Unclear('Use explicit bits, bytes, or KiB. KB is ambiguous here.')
                    value=value*factors[unit]/factors[target]
                elif target=='locations' and unit in ('locations','location'):pass
                else:raise Unclear('That unit does not match the quantity requested. Please clarify it.')
            accepted=value==Fraction(spec['value'])
        return verdict('correct' if accepted else 'incorrect',
            'Your final answer checks out.' if accepted else 'Your final answer does not yet satisfy this exercise. Show an intermediate step so we can locate a supported error.')
    except Unclear as exc:
        return verdict('needs_clarification',str(exc),clarification='Could you restate the final answer in the requested format?')
