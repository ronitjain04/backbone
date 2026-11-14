"""An eight-instruction, I/O-free LC-3 subset with universal bit-vector checking."""
import re
from .checking import verdict


def check_program(spec, text):
    lines=[line.split(';',1)[0].strip() for line in text.splitlines()]
    lines=[line for line in lines if line]
    if not lines or len(lines)>spec['max_steps']:
        return verdict('needs_clarification',f'Use between 1 and {spec["max_steps"]} straight-line instructions.')
    instructions=[]
    for line in lines:
        parts=[p for p in re.split(r'[\s,]+',line.upper()) if p]
        if len(parts)==3 and parts[0]=='NOT' and all(re.fullmatch('R[0-7]',p) for p in parts[1:]):
            instructions.append(('NOT',int(parts[1][1]),int(parts[2][1]),None));continue
        if len(parts)!=4 or parts[0] not in ('ADD','AND','NOT') or not re.fullmatch('R[0-7]',parts[1]) or not re.fullmatch('R[0-7]',parts[2]):
            return verdict('needs_clarification','I can check only ADD, AND, NOT with R0–R7 and documented immediates. Remove labels, directives, and I/O.')
        op,dest,source,arg=parts
        if op=='NOT':
            # NOT has two register operands, handled below by adding a placeholder during parsing.
            return verdict('needs_clarification','NOT takes a destination and one source register.')
        if not re.fullmatch(r'R[0-7]|#-?\d+',arg):return verdict('needs_clarification','Use a register or a decimal immediate such as #-5.')
        if arg.startswith('#') and not -16<=int(arg[1:])<=15:return verdict('needs_clarification','ADD/AND immediates must fit signed imm5 (-16 to 15).')
        instructions.append((op,int(dest[1]),int(source[1]),arg))
    try:
        from z3 import BitVec, BitVecVal, Solver, sat, unsat
        initial=[BitVec(f'initial_R{i}',16) for i in range(8)];regs=list(initial)
        for op,dest,source,arg in instructions:
            if op=='NOT':
                regs[dest]=~regs[source];continue
            right=regs[int(arg[1])] if arg.startswith('R') else BitVecVal(int(arg[1:]),16)
            regs[dest]=regs[source]+right if op=='ADD' else regs[source]&right
        solver=Solver();solver.set(timeout=1000);solver.add(regs[spec['register']]!=BitVecVal(spec['value'],16));result=solver.check()
        if result==unsat:return verdict('correct','This snippet produces the requested value for every initial register state.')
        if result==sat:
            model=solver.model();counterexample={f'R{i}':model.eval(r,model_completion=True).as_long() for i,r in enumerate(initial)}
            return verdict('incorrect','This snippet does not produce the requested result for every initial register state. Consider whether old register contents affect it.',counterexample=counterexample)
        return verdict('needs_clarification','I could not prove this snippet within the checking limit. Could you simplify it?')
    except ImportError:return verdict('unavailable','The symbolic code checker is unavailable. Your code is saved.')
