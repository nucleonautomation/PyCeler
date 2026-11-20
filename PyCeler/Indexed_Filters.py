import ast
from .Runtime_Resources import _Resource

# Recognize ordered squared-distance predicates over fixed columns of an indexed table.
def _Cell(Node):
    if not isinstance(Node, ast.Subscript) or not isinstance(Node.value, ast.Name) or not isinstance(Node.slice, ast.Tuple) or len(Node.slice.elts) != 2:
        return None
    Row, Column = Node.slice.elts
    if isinstance(Row, ast.Name) and isinstance(Column, ast.Constant) and type(Column.value) is int and 0 <= Column.value < 256:
        return Node.value.id, Row.id, Column.value

def _Square_Sum(Node):
    if isinstance(Node, ast.BinOp) and isinstance(Node.op, ast.Add):
        Left, Right = _Square_Sum(Node.left), _Square_Sum(Node.right)
        return ('(' + Left[0] + ' + ' + Right[0] + ')', Left[1] + Right[1]) if Left and Right else None
    if isinstance(Node, ast.BinOp) and isinstance(Node.op, ast.Mult) and isinstance(Node.left, ast.Name) and isinstance(Node.right, ast.Name) and Node.left.id == Node.right.id:
        return ('{' + Node.left.id + '}', [Node.left.id])

def _Filter_Plan(Loop, Function, Scope):
    if not isinstance(Loop.target, ast.Name) or not isinstance(Loop.iter, ast.Name) or Loop.orelse or len(Loop.body) < 3:
        return None
    Target, Source = Loop.target.id, Loop.iter.id
    Body, Final = Loop.body[:-2], Loop.body[-1]
    Skip = Body[0] if isinstance(Body[0], ast.If) else None
    if Skip:
        Body = Body[1:]
    Differences = {}
    Table = Anchor = None
    for Statement in Body:
        if not isinstance(Statement, ast.Assign) or len(Statement.targets) != 1 or not isinstance(Statement.targets[0], ast.Name):
            return None
        Value = Statement.value
        if not isinstance(Value, ast.BinOp) or not isinstance(Value.op, ast.Sub):
            return None
        Left, Right = _Cell(Value.left), _Cell(Value.right)
        if not Left or not Right or Left[0] != Right[0] or Left[2] != Right[2] or Right[1] != Target or Left[1] == Target:
            return None
        if Table is not None and (Table, Anchor) != Left[:2]:
            return None
        Table, Anchor = Left[:2]
        Differences[Statement.targets[0].id] = Left[2]
    if not 1 <= len(Differences) == len(Body) <= 16:
        return None
    if Skip and (ast.unparse(Skip.test) not in (Target + ' == ' + Anchor, Anchor + ' == ' + Target) or Skip.orelse or len(Skip.body) != 1 or not isinstance(Skip.body[0], ast.Continue)):
        return None
    Total = Loop.body[-2]
    if not isinstance(Total, ast.Assign) or len(Total.targets) != 1 or not isinstance(Total.targets[0], ast.Name):
        return None
    Squares = _Square_Sum(Total.value)
    if not Squares or sorted(Squares[1]) != sorted(Differences):
        return None
    if not isinstance(Final, ast.If) or Final.orelse or len(Final.body) != 1 or not isinstance(Final.body[0], ast.Expr):
        return None
    Test, Append = Final.test, Final.body[0].value
    if not isinstance(Test, ast.Compare) or len(Test.ops) != 1 or not isinstance(Test.ops[0], (ast.Lt, ast.LtE)) or not isinstance(Test.left, ast.Name) or Test.left.id != Total.targets[0].id:
        return None
    Limit = Test.comparators[0]
    Squared = isinstance(Limit, ast.BinOp) and isinstance(Limit.op, ast.Pow) and isinstance(Limit.right, ast.Constant) and type(Limit.right.value) is int and Limit.right.value == 2
    Limit = Limit.left if Squared else Limit
    if not isinstance(Limit, ast.Name) or not isinstance(Append, ast.Call) or Append.keywords or len(Append.args) != 1 or not isinstance(Append.args[0], ast.Name) or Append.args[0].id != Target:
        return None
    if not isinstance(Append.func, ast.Attribute) or Append.func.attr != 'append' or not isinstance(Append.func.value, ast.Name):
        return None
    Names = (Source, Table, Anchor, Limit.id, Append.func.value.id)
    Private = [Target, *Differences, Total.targets[0].id]
    if len(set((*Names, *Private))) != len(Names) + len(Private):
        return None
    # Fast execution omits temporary Python bindings. Reject observable locals and preexisting owners.
    Outside = set(ast.walk(Function)) - set(ast.walk(Loop))
    if any(isinstance(Node, ast.Name) and Node.id in Private or isinstance(Node, ast.arg) and Node.arg in Private for Node in Outside):
        return None
    Probe = ast.parse('def Probe(' + ', '.join(Names) + '):\n    pass').body[0]
    Probe.body = [Loop, ast.Return(value=ast.Name(id=Names[-1], ctx=ast.Load()))]
    Expression = Squares[0].format(**{Name: 'Square_' + str(Index) for Index, Name in enumerate(Differences)})
    return dict(Kind='indexed_filter', Region=True, Scope=Scope, Probe=Probe, Names=Names, Loops=[Loop], Columns=tuple(Differences.values()), Expression=Expression, Skip=bool(Skip), Squared=Squared, Inclusive=isinstance(Test.ops[0], ast.LtE), Transformations=('Ordered indexed float64 distance filter',))

def _Filter_Plans(Scopes, Edits):
    Plans = {}
    for Function, Scope, Captures, Locals, Globals in Scopes:
        if not isinstance(Function, ast.FunctionDef) or Function.decorator_list:
            continue
        Parts = tuple(ast.walk(Function))
        if any(isinstance(Node, (ast.Global, ast.Nonlocal, ast.ClassDef, ast.AsyncFunctionDef, ast.Lambda, ast.Yield, ast.YieldFrom, ast.Try, ast.TryStar)) or isinstance(Node, ast.FunctionDef) and Node is not Function or isinstance(Node, ast.Name) and Node.id in {'locals', 'vars', 'exec', 'eval', 'dir', '_getframe', 'currentframe'} or isinstance(Node, ast.Attribute) and Node.attr in {'_getframe', 'currentframe', 'f_locals'} for Node in Parts):
            continue
        for Loop in (Node for Node in Parts if isinstance(Node, ast.For)):
            if any(Loop.lineno <= Edit[1].end_lineno and Loop.end_lineno >= Edit[1].lineno for Edit in Edits.values()):
                continue
            Plan = _Filter_Plan(Loop, Function, Scope)
            if Plan:
                Plans[Loop.lineno] = (Plan['Names'], Loop, Function, Plan)
    return Plans

def _Filter_Kernel(Plan, Line, Measured):
    Prefix = '_Pyceler_Filter_' + str(Line) + '_'
    Columns = Plan['Columns']
    Arithmetic = []
    for Index, Column in enumerate(Columns):
        Arithmetic.extend([f'if not FILTER_PREFIXLoad(&View, Fixed, {Column}, &Left) or not FILTER_PREFIXLoad(&View, Row, {Column}, &Right):', '    return False', 'Delta = Left - Right', f'Square_{Index} = Delta * Delta'])
    Arithmetic.append('if ' + Plan['Expression'] + (' <= ' if Plan['Inclusive'] else ' < ') + 'Limit:')
    Arithmetic.append('    Matches.append(Item)')
    Text = _Resource('Indexed_Filter_Runtime.pxi.in')
    Text = Text.replace('FILTER_SQUARES', ', '.join('Square_' + str(Index) for Index in range(len(Columns))))
    Text = Text.replace('FILTER_ARITHMETIC', '\n            '.join(Arithmetic)).replace('FILTER_COLUMN', str(max(Columns)))
    Text = Text.replace('FILTER_SQUARED', str(Plan['Squared'])).replace('FILTER_SKIP', str(Plan['Skip']))
    Text = Text.replace('FILTER_POLICY', 'if _Pyceler_Choose((len(Items),), True, Policy) == 0:\n        return False' if Measured else 'pass')
    return Text.replace('FILTER_PREFIX', Prefix)

def _Filter_Source(Plan, Loop, Line, Prefix, Measured):
    Args = ', '.join(Plan['Names'])
    Policy = Prefix + 'Table_' + str(Line) if Measured else 'None'
    Done = Prefix + 'Filtered_' + str(Line)
    # Missing bindings may be valid for empty/short-circuited loops. Replay in the original order.
    Lines = ['try:', f'    {Done} = {Prefix}Filter_{Line}_Try({Args}, {Policy})', f'except {Prefix}Python_Builtins.NameError:', f'    {Done} = False', f'if not {Done}:', f"    {Prefix}Dispatch_Event('Execution', 'python_fallback', 0)"]
    return '\n'.join([*Lines, *('    ' + Row for Row in ast.unparse(Loop).splitlines())])
