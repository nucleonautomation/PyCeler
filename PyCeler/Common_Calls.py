import ast
import copy
# Summarize supported pure helpers and substitute arguments without changing evaluation order.
def _Call_Facts(Tree):
    from .Math_Registry import _Math_Calls
    return dict(Helpers=_Helper_Summaries(Tree), Math={(Record['Line'], Record['Column']): Record for Record in _Math_Calls(Tree)})
# Bind positional and keyword arguments in their source evaluation order.
def _Call_Arguments(Call, Parameters, Positional_Only=0):
    if len(Call.args) > len(Parameters) or any(isinstance(Value, ast.Starred) for Value in Call.args):
        return None
    Values = list(Call.args)
    Slots = {Name: Index for Index, Name in enumerate(Parameters[:len(Values)])}
    for Keyword in Call.keywords:
        if Keyword.arg not in Parameters[Positional_Only:] or Keyword.arg in Slots:
            return None
        Slots[Keyword.arg] = len(Values)
        Values.append(Keyword.value)
    if len(Slots) != len(Parameters):
        return None
    return tuple(Values), tuple(Slots[Name] for Name in Parameters)

def _Helper_Summaries(Tree):
    Counts, Bindings, Imports = {}, {}, []
    for Node in Tree.body:
        if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            Counts[Node.name] = Counts.get(Node.name, 0) + 1
        if isinstance(Node, ast.Import):
            for Alias in Node.names:
                if Alias.name == 'math':
                    Bindings[Alias.asname or Alias.name] = None
                    Imports.append('import math as ' + (Alias.asname or Alias.name))
        elif isinstance(Node, ast.ImportFrom) and Node.module == 'math' and not Node.level:
            for Alias in Node.names:
                if Alias.name != '*':
                    Bindings[Alias.asname or Alias.name] = Alias.name
                    Imports.append('from math import ' + Alias.name + ' as ' + (Alias.asname or Alias.name))
    Result = {}
    for Node in Tree.body:
        if not isinstance(Node, ast.FunctionDef) or Counts[Node.name] != 1 or Node.decorator_list or getattr(Node, 'type_params', ()):
            continue
        Arguments = Node.args
        if Arguments.vararg or Arguments.kwarg or Arguments.kwonlyargs or Arguments.defaults:
            continue
        Body = Node.body
        if Body and isinstance(Body[0], ast.Expr) and isinstance(Body[0].value, ast.Constant) and type(Body[0].value.value) is str:
            Body = Body[1:]
        if not Body or not isinstance(Body[-1], ast.Return) or Body[-1].value is None:
            continue
        Assignments = []
        for Statement in Body[:-1]:
            if isinstance(Statement, ast.Assign) and len(Statement.targets) == 1 and isinstance(Statement.targets[0], ast.Name):
                Assignments.append((Statement.targets[0].id, Statement.value))
            elif isinstance(Statement, ast.AugAssign) and isinstance(Statement.target, ast.Name):
                Read = ast.copy_location(ast.Name(id=Statement.target.id, ctx=ast.Load()), Statement.target)
                Assignments.append((Statement.target.id, ast.copy_location(ast.BinOp(left=Read, op=copy.deepcopy(Statement.op), right=Statement.value), Statement)))
            else:
                break
        if len(Assignments) != len(Body) - 1:
            continue
        if any(isinstance(Part, (ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr, ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)) for Statement in Body for Part in ast.walk(Statement)):
            continue
        Definition = copy.deepcopy(Node)
        Definition.returns = None
        Definition.type_comment = None
        for Argument in (*Definition.args.posonlyargs, *Definition.args.args):
            Argument.annotation = None
            Argument.type_comment = None
        Result[Node.name] = dict(Parameters=tuple(Part.arg for Part in (*Arguments.posonlyargs, *Arguments.args)), Positional_Only=len(Arguments.posonlyargs), Assignments=tuple(Assignments), Expression=Body[-1].value, Source=ast.unparse(Definition), Bindings=Bindings.copy(), Imports=tuple(Imports))
    return Result

def _Helper_Substitute(Node, Token, Values):
    if not isinstance(Node, tuple):
        return Node
    if Node and Node[0] == 'helper_parameter' and Node[1] == Token:
        return Values[Node[2]]
    return tuple(_Helper_Substitute(Part, Token, Values) for Part in Node)

def _Helper_Fresh(Node, Kind):
    Operation = Node[0]
    if Operation == 'helper':
        return _Helper_Fresh(Node[3], Kind)
    if Operation == 'conditional':
        return _Helper_Fresh(Node[2], Kind) and _Helper_Fresh(Node[3], Kind)
    if Operation == 'absolute':
        return Kind == 'float'
    return Operation in ('arithmetic', 'checked_integer', 'integer_negative', 'negative', 'python_power', 'call')

def _Helper_Operations(Node):
    if not isinstance(Node, tuple):
        return set()
    Result = {Node[0]} if Node and isinstance(Node[0], str) else set()
    for Part in Node:
        Result.update(_Helper_Operations(Part))
    return Result

def _Helper_Depends(Node, Token):
    if not isinstance(Node, tuple):
        return False
    if Node and Node[0] == 'helper_parameter' and Node[1] == Token:
        return True
    return any(_Helper_Depends(Part, Token) for Part in Node)
# Only helpers with proven summaries may cross the native call boundary.
def _Helper_Expression(Node, Plan, Bindings, Inputs, Calls, Expression, Unsupported):
    Name = Node.func.id
    Active = Plan.get('Helper_Stack', ())
    if Name in Active:
        raise Unsupported()
    Summary = Plan['Helpers'][Name]
    Bound = _Call_Arguments(Node, Summary['Parameters'], Summary['Positional_Only'])
    if Bound is None:
        raise Unsupported()
    Arguments, Slots = Bound
    Values = [Expression(Argument, Plan, Bindings, Inputs, Calls) for Argument in Arguments]
    Counter = Plan['Helper_Counter']
    Token = Counter[0]
    Counter[0] += 1
    Root = '_Pyceler_Helper_Function_' + Name if Active else Name
    Plan['Helper_Roots'][Root] = Name
    if Active:
        Plan['Helper_Globals'][Root] = Name
    Plan['Helper_Used'].add(Name)
    Parameters = {Parameter: (('helper_parameter', Token, Slot), Values[Slot][1]) for Parameter, Slot in zip(Summary['Parameters'], Slots)}
    Local_Names = set(Parameters) | {Target for Target, Value in Summary.get('Assignments', ())}
    Local_Bindings = {Root: Binding for Root, Binding in Summary['Bindings'].items() if Root not in Local_Names}
    Local = dict(Plan, Helper_Parameters=Parameters, Helper_Stack=(*Active, Name), Helpers={Key: Value for Key, Value in Plan['Helpers'].items() if Key not in Local_Names}, Local_Types={}, Local_Slots=[], Buffers={}, Builtins=(), Random={}, Names=(), Output='', Bindings=Local_Bindings)
    Local_Calls = set()
    Assignments = []
    for Target, Source in Summary.get('Assignments', ()):
        Value, Kind = Expression(Source, Local, Local_Bindings, Inputs, Local_Calls)
        Assignment_Token = Counter[0]
        Counter[0] += 1
        Parameters[Target] = (('helper_parameter', Assignment_Token, 0), Kind)
        Assignments.append((Assignment_Token, Value))
    Value, Kind = Expression(Summary['Expression'], Local, Local_Bindings, Inputs, Local_Calls)
    Fresh_Value = Value
    for Assignment_Token, Assignment_Value in reversed(Assignments):
        Fresh_Value = _Helper_Substitute(Fresh_Value, Assignment_Token, (Assignment_Value,))
    if not _Helper_Fresh(Fresh_Value, Kind) or not _Helper_Depends(Fresh_Value, Token):
        raise Unsupported()
    for Assignment_Token, Assignment_Value in reversed(Assignments):
        Value = ('helper', Assignment_Token, (Assignment_Value,), Value)
    Plan['Helper_Operations'].update(_Helper_Operations(Value))
    for Root, Function, Module in Local_Calls:
        if Root.startswith('_Pyceler_Helper_Math_'):
            Calls.add((Root, Function, Module))
        else:
            Private = '_Pyceler_Helper_Math_' + Root
            Plan['Helper_Globals'][Private] = Root
            Calls.add((Private, Function, Module))
    return ('helper', Token, tuple(Value for Value, Kind in Values), Value), Kind

def _Helper_Emit(Node, Lines, Variables, Functions, Prefix, Emit, Tag, Tagged=False):
    Values = []
    for Argument in Node[2]:
        Value = Emit(Argument, Lines, Variables, Functions, Prefix)
        Name = 'T' + str(len(Variables))
        Variables.append(Name)
        Lines.append('    ' + Name + ' = ' + Value)
        Values.append(('native_value', Name, Tag(Argument, Value)))
    Body = _Helper_Substitute(Node[3], Node[1], Values)
    Value = Emit(Body, Lines, Variables, Functions, Prefix)
    return (Value, Tag(Body, Value)) if Tagged else Value
