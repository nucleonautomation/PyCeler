import ast
import copy
# Normalize supported range/enumerate/zip forms without consuming arbitrary iterators speculatively.
def _Iterator_Normalize(Outer):
    if not isinstance(Outer, ast.For) or Outer.orelse or not isinstance(Outer.target, (ast.Tuple, ast.List)) or not isinstance(Outer.iter, ast.Call):
        return None
    Call = Outer.iter
    if not isinstance(Call.func, ast.Name) or Call.func.id not in ('enumerate', 'zip'):
        return None
    if not all(isinstance(Target, ast.Name) for Target in Outer.target.elts):
        return None
    Targets = tuple(Target.id for Target in Outer.target.elts)
    if len(set(Targets)) != len(Targets):
        return None
    Written = {Part.id for Statement in Outer.body for Part in ast.walk(Statement) if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Store)}
    Kind = Call.func.id
    if Kind == 'enumerate':
        if len(Targets) != 2 or not 1 <= len(Call.args) <= 2 or not isinstance(Call.args[0], ast.Name):
            return None
        if len(Call.keywords) > 1 or any(Value.arg != 'start' for Value in Call.keywords) or len(Call.args) == 2 and Call.keywords:
            return None
        Start = Call.args[1] if len(Call.args) == 2 else Call.keywords[0].value if Call.keywords else ast.Constant(0)
        Literal = Start.operand if isinstance(Start, ast.UnaryOp) and isinstance(Start.op, (ast.UAdd, ast.USub)) else Start
        if not (isinstance(Start, ast.Name) or isinstance(Literal, ast.Constant) and type(Literal.value) is int):
            return None
        Sources = (Call.args[0].id,)
        Protected = set(Sources) | ({Start.id} if isinstance(Start, ast.Name) else set())
        if Protected & (Written | set(Targets)):
            return None
        Position = Targets[0]
        Start_Text = ast.unparse(Start)
        Range = f'range({Start_Text}, ({Start_Text}) + len({Sources[0]}))'
        Bindings = [f'{Targets[1]} = {Sources[0]}[{Position} - ({Start_Text})]']
        Internal = ()
    else:
        if not Call.args or len(Call.args) != len(Targets) or not all(isinstance(Value, ast.Name) for Value in Call.args):
            return None
        if len(Call.keywords) > 1 or any(Value.arg != 'strict' for Value in Call.keywords):
            return None
        if Call.keywords and not (isinstance(Call.keywords[0].value, ast.Constant) and type(Call.keywords[0].value.value) is bool):
            return None
        Sources = tuple(Value.id for Value in Call.args)
        if set(Sources) & (Written | set(Targets)):
            return None
        Used = {Part.id for Part in ast.walk(Outer) if isinstance(Part, ast.Name)}
        Position = f'_Pyceler_Iterator_Position_{Outer.lineno}'
        while Position in Used:
            Position += '_X'
        Limit = f'len({Sources[0]})'
        for Source in Sources[1:]:
            Limit = f'({Limit} if {Limit} < len({Source}) else len({Source}))'
        Range = 'range(' + Limit + ')'
        Bindings = [f'{Target} = {Source}[{Position}]' for Target, Source in zip(Targets, Sources)]
        Internal = (Position,)
        Start_Text = '0'
    Normal = copy.deepcopy(Outer)
    Normal.target = ast.copy_location(ast.Name(id=Position, ctx=ast.Store()), Outer.target)
    Normal.iter = ast.copy_location(ast.parse(Range, mode='eval').body, Outer.iter)
    Prefix = ast.parse('\n'.join(Bindings)).body
    for Statement in Prefix:
        for Part in ast.walk(Statement):
            ast.copy_location(Part, Outer.target)
    Normal.body = Prefix + Normal.body
    Contract = dict(Kind=Kind, Sources=Sources, Targets=Targets, Position=Position, Start=Start_Text, Internal=Internal, Original=Outer)
    return ast.fix_missing_locations(Normal), Contract

def _Iterator_Plan(Planner, Function, Outer, Available, Module, *Args, **Keywords):  # Normalization feeds existing planners; iterator construction still requires runtime guards.
    Converted = None if Module else _Iterator_Normalize(Outer)
    if Converted is None:
        return Planner(Function, Outer, Available, Module, *Args, **Keywords)
    Normal, Contract = Converted
    Plan = Planner(Function, Normal, Available, Module, *Args, Internal=Contract['Internal'], Normalized=True, **Keywords)
    if Plan is None or any(Plan['Buffers'].get(Name, (0, 0))[1] != 1 for Name in Contract['Sources']):
        return None
    if Plan.get('Random') or any(isinstance(Part, (ast.Break, ast.Continue)) for Part in ast.walk(Outer)):
        return None
    Plan['Iterator'] = Contract
    Plan['Probe'].body[0] = copy.deepcopy(Outer)
    Plan['Transformations'] += ('Guarded ' + Contract['Kind'] + ' indexing',)
    return Plan
