import ast
import copy
from .Common_Values import _Real_Inputs, _Live_Region_Outputs
from .Common_Scopes import _Function_Scopes, _Bind_Region_Scope
from .Fast_Math import _Fast_Call_Contracts, _Fast_Expression, _Fast_Test, _Fast_Unsupported, _Fast_Imports
from .Numeric_Contracts import _Builtin_Call
from .Common_Analysis import _Reads_Before_Definition, _Region_Loop_Partition, _Independent_Outer_Storage, _Contained_Scalar_Edits, _Binding_Targets
from .Numeric_Identity import _Identity
from .Common_Calls import _Call_Facts
from .Iterator_Regions import _Iterator_Plan
# Build shared numeric-region IR while checking scalar flow, effects, storage and observable bindings.
def _Cell(Node):
    Indices = []
    while isinstance(Node, ast.Subscript):
        Indices.insert(0, Node.slice)
        Node = Node.value
    return (Node.id, Indices) if isinstance(Node, ast.Name) and Indices else None

def _Fresh(Node, Known, Depth):
    if isinstance(Node, ast.Name):
        return Known.get(Node.id, -1)
    if isinstance(Node, ast.Constant) and type(Node.value) in (int, bool) and -5 <= Node.value <= 256:
        return 10000
    if isinstance(Node, ast.IfExp):
        return min(_Fresh(Node.body, Known, Depth), _Fresh(Node.orelse, Known, Depth))
    if isinstance(Node, ast.Call):
        return Depth
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.UAdd):
        return _Fresh(Node.operand, Known, Depth)
    if isinstance(Node, ast.BinOp) or isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.USub):
        return Depth if any(isinstance(Part, (ast.Name, ast.Subscript, ast.Call)) for Part in ast.walk(Node)) else -1
    return -1

def _Expression(Node, Context, Calls):
    return _Fast_Expression(Node, Context, Context["Bindings"], [], Calls)
# Range operands need integer semantics; float-valued indices require explicit guarded conversion.
def _Range(Node, Context, Calls):
    if not isinstance(Node, ast.Call) or not isinstance(Node.func, ast.Name) or Node.func.id != "range" or Node.keywords or not 1 <= len(Node.args) <= 3:
        raise _Fast_Unsupported()
    Values = [_Expression(Argument, Context, Calls) for Argument in Node.args]
    if any(Kind != 'integer' and not (Context.get('Array_Region') and Kind == 'float') for Value, Kind in Values):
        raise _Fast_Unsupported()
    Values = [(('array_index', Value) if Kind != 'integer' else Value, 'integer') for Value, Kind in Values]
    return (("literal", 0.0), Values[0][0], ("literal", 1.0)) if len(Values) == 1 else (Values[0][0], Values[1][0], Values[2][0] if len(Values) == 3 else ("literal", 1.0))

def _Live_Inputs(Statements, Defined, Inputs):
    for Node in Statements:
        if isinstance(Node, ast.Assign):
            Values = [Node.value, *(Target for Target in Node.targets if not isinstance(Target, ast.Name))]
        elif isinstance(Node, ast.AugAssign):
            Values = [Node.target, Node.value]
        elif isinstance(Node, ast.For):
            Values = [Node.iter]
        elif isinstance(Node, (ast.If, ast.While)):
            Values = [Node.test]
        else:
            Values = []
        for Value in Values:
            Inputs.update(Part.id for Part in ast.walk(Value) if isinstance(Part, ast.Name) and Part.id not in Defined)
        if isinstance(Node, ast.If):
            Left, Right = Defined.copy(), Defined.copy()
            _Live_Inputs(Node.body, Left, Inputs)
            _Live_Inputs(Node.orelse, Right, Inputs)
            Defined.update(Left & Right)
        elif isinstance(Node, (ast.For, ast.While)):
            Local = Defined | ({Node.target.id} if isinstance(Node, ast.For) and isinstance(Node.target, ast.Name) else set())
            _Live_Inputs(Node.body, Local, Inputs)
        elif isinstance(Node, (ast.Assign, ast.AugAssign)):
            Targets = Node.targets if isinstance(Node, ast.Assign) else [Node.target]
            Defined.update(Target.id for Target in Targets if isinstance(Target, ast.Name))

def _Probe_Inputs(Parts, Inputs, Carry):
    Roles = {Name: "zero" if Name in Carry else "size" for Name in Inputs}
    Stops, Starts, Steps, Coordinates = set(), set(), set(), set()
    for Node in Parts:
        if isinstance(Node, ast.Subscript):
            Coordinates.update(Part.id for Part in ast.walk(Node.slice) if isinstance(Part, ast.Name))
        if isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id == "range":
            if Node.args:
                Stops.update(Part.id for Part in ast.walk(Node.args[0 if len(Node.args) == 1 else 1]) if isinstance(Part, ast.Name))
            if len(Node.args) > 1:
                Starts.update(Part.id for Part in ast.walk(Node.args[0]) if isinstance(Part, ast.Name))
            if len(Node.args) > 2:
                Steps.update(Part.id for Part in ast.walk(Node.args[2]) if isinstance(Part, ast.Name))
    for Name in Roles:
        if Name in Steps - Stops:
            Roles[Name] = "step"
        elif Name in (Starts | Coordinates) - Stops:
            Roles[Name] = "zero"
    return Roles

def _Store_Name(Name, Kind, Context):
    if Name in Context["Buffers"] or Name in Context["Bindings"] or Name in {"range", "len"}:
        raise _Fast_Unsupported()
    if Name in Context["Local_Types"] and Context["Local_Types"][Name] != Kind:
        raise _Fast_Unsupported()
    Context["Local_Types"][Name] = Kind
    if Name not in Context["Local_Slots"]:
        Context["Local_Slots"].append(Name)
    return Context["Local_Slots"].index(Name)
# Track scalar kinds and assignment flow across branches before emitting any native statements.
def _Program(Statements, Context, Calls, Fresh, Depth):
    Result = []
    for Node in Statements:
        if isinstance(Node, (ast.Assign, ast.AugAssign)):
            if isinstance(Node, ast.Assign):
                if len(Node.targets) != 1:
                    raise _Fast_Unsupported()
                Target, Expression = Node.targets[0], Node.value
            else:
                Target = Node.target
                Read = copy.deepcopy(Target)
                Read.ctx = ast.Load()
                Expression = ast.BinOp(left=Read, op=Node.op, right=Node.value)
            Value, Kind = _Expression(Expression, Context, Calls)
            if Kind not in ("float", "integer", "boolean"):
                raise _Fast_Unsupported()
            Freshness = Depth if Context.get('Array_Region') and isinstance(Expression, ast.Subscript) else _Fresh(Expression, Fresh, Depth)
            if isinstance(Target, ast.Name):
                if Target.id in Context["Carry"] and Freshness < Depth and not Context.get('Dynamic_Identity'):
                    raise _Fast_Unsupported()
                Slot = _Store_Name(Target.id, Kind, Context)
                Fresh[Target.id] = Freshness
                if Freshness >= Depth:
                    Context['Possibly_Fresh'].add(Target.id)
                elif isinstance(Expression, ast.Name) and Expression.id in Context['Possibly_Fresh']:
                    Context['Possibly_Fresh'].add(Target.id)
                Result.append(("store", Slot, Value, _Identity(Value, Kind, Expression)))
            else:
                Cell = _Cell(Target)
                Deferred = isinstance(Expression, ast.Name) and Expression.id in Context['Possibly_Fresh'] and not Context.get('Array_Region')
                if Cell is None or Cell[0] not in Context["Buffers"] or Freshness < Depth and not Deferred and not Context.get('Array_Region'):
                    raise _Fast_Unsupported()
                if Deferred and Freshness < Depth:
                    Context['Dynamic_Identity'] = True
                Name, Indices = Cell
                Slot, Dimensions, Previous = Context["Buffers"][Name]
                if len(Indices) != Dimensions or Name in Context["Read_Buffers"] and Kind != Previous:
                    raise _Fast_Unsupported()
                if Name in Context["Writes"] and Context["Writes"][Name] != Kind:
                    raise _Fast_Unsupported()
                Coordinates = [_Expression(Index, Context, Calls) for Index in Indices]
                if any(Type != 'integer' and not (Context.get('Array_Region') and Type == 'float') for Value, Type in Coordinates):
                    raise _Fast_Unsupported()
                Context["Buffers"][Name] = Slot, Dimensions, Kind
                Context["Writes"][Name] = Kind
                Result.append(("write", Slot, tuple(('array_index', Part) if Type != 'integer' else Part for Part, Type in Coordinates), Value, _Identity(Value, Kind, Expression)))
        elif isinstance(Node, ast.If):
            Test = _Fast_Test(Node.test, Context, Context["Bindings"], [], Calls)
            Branches, Flows, Freshness = [], [], []
            for Branch in (Node.body, Node.orelse):
                Local = dict(Context, Local_Types=dict(Context["Local_Types"]))
                Known = Fresh.copy()
                Branches.append(_Program(Branch, Local, Calls, Known, Depth))
                Flows.append(Local["Local_Types"])
                Freshness.append(Known)
            Context["Local_Types"] = {Name: Kind for Name, Kind in Flows[0].items() if Flows[1].get(Name) == Kind}
            Fresh.clear()
            Fresh.update({Name: min(Value, Freshness[1].get(Name, -1)) for Name, Value in Freshness[0].items()})
            Result.append(("if", Test, *Branches))
        elif isinstance(Node, (ast.For, ast.While)):
            if Node.orelse:
                raise _Fast_Unsupported()
            Local = dict(Context, Local_Types=dict(Context["Local_Types"]))
            Known = Fresh.copy()
            if isinstance(Node, ast.For):
                if not isinstance(Node.target, ast.Name):
                    raise _Fast_Unsupported()
                Begin, End, Step = _Range(Node.iter, Context, Calls)
                Slot = _Store_Name(Node.target.id, "integer", Local)
                Known[Node.target.id] = Depth + 1
                Header = "for", Slot, Begin, End, Step
            else:
                Header = "while", _Fast_Test(Node.test, Context, Context["Bindings"], [], Calls)
            Body = _Program(Node.body, Local, Calls, Known, Depth + 1)
            if any(Local["Local_Types"].get(Name) != Kind for Name, Kind in Context["Local_Types"].items()):
                raise _Fast_Unsupported()
            Fresh.update({Name: min(Value, Known.get(Name, -1)) for Name, Value in Fresh.items()})
            Result.append((*Header, Body))
        elif Depth and isinstance(Node, (ast.Continue, ast.Break)):
            if Depth == 1 and isinstance(Node, ast.Break):
                raise _Fast_Unsupported()
            Result.append(("continue" if isinstance(Node, ast.Continue) else "break",))
        elif isinstance(Node, ast.Pass):
            Result.append(("pass",))
        else:
            raise _Fast_Unsupported()
    return tuple(Result)

def _Numeric_Region_Plan(Function, Outer, Available, Module, Cell_Kind="float", Array=False, Helpers=None, Call_Bindings=None, Internal=(), Normalized=False):
    if not isinstance(Outer, ast.For) or not isinstance(Outer.target, ast.Name) or Outer.orelse:
        return None
    Parts = list(ast.walk(Outer))
    if any(isinstance(Node, ast.Name) and Node.id.startswith("_Pyceler_") and Node.id not in Internal for Node in Parts):
        return None
    if any(isinstance(Node, ast.Constant) and type(Node.value) is int and abs(Node.value) > 2**50 for Node in Parts):
        return None
    Inner = {Node.value for Node in Parts if isinstance(Node, ast.Subscript)}
    Length_Arguments = {Node.args[0] for Node in Parts if isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id == "len" and len(Node.args) == 1}
    Buffers, Read_Buffers, Bindings = {}, set(), {}
    Builtins, Random = set(), {}
    Helpers = {} if Helpers is None else Helpers
    Helper_Names = set()
    for Node in Parts:
        if isinstance(Node, ast.Subscript) and Node not in Inner and Node not in Length_Arguments:
            Cell = _Cell(Node)
            if Cell is None:
                return None
            Name, Coordinates = Cell
            if Name in Buffers and Buffers[Name][1] != len(Coordinates):
                return None
            Buffers.setdefault(Name, (len(Buffers), len(Coordinates), Cell_Kind))
            if isinstance(Node.ctx, ast.Load) or any(isinstance(Statement, ast.AugAssign) and Statement.target is Node for Statement in Parts):
                Read_Buffers.add(Name)
        elif isinstance(Node, ast.Call):
            Target = Node.func
            if isinstance(Target, ast.Name) and Target.id in Helpers:
                Helper_Names.add(Target.id)
                continue
            if isinstance(Target, ast.Name) and Target.id in {"range", "len"}:
                continue
            if _Builtin_Call(Node):
                if Target.id in Available:
                    return None
                Builtins.add(Target.id)
                continue
            if Array and isinstance(Target, ast.Name) and Target.id in {'int', 'float', 'min', 'max'}:
                Builtins.add(Target.id)
                continue
            if Array and isinstance(Target, ast.Attribute) and isinstance(Target.value, ast.Name) and Target.attr == 'random' and not Node.args and not Node.keywords:
                Random[(Node.lineno, Node.col_offset)] = Target.value.id
                continue
            if isinstance(Target, ast.Attribute) and isinstance(Target.value, ast.Name):
                Root, Name, Binding = Target.value.id, Target.attr, None
            elif isinstance(Target, ast.Name):
                Root, Name, Binding = Target.id, Target.id, Target.id
                Record = (Call_Bindings or {}).get((getattr(Node, 'lineno', 0), getattr(Node, 'col_offset', 0)))
                if Record is not None and Record['Module'] == 'math' and Record['Status'] == 'Recognized':
                    Name = Binding = Record['Name']
            else:
                return None
            Contract = _Fast_Call_Contracts.get(Name)
            if Contract is None or Contract["Return"] != "float" or Root in Bindings and Bindings[Root] != Binding:
                return None
            Bindings[Root] = Binding
    Shape_Only = {}
    for Argument in Length_Arguments:
        Dimensions = 1
        while isinstance(Argument, ast.Subscript):
            Dimensions += 1
            Argument = Argument.value
        if isinstance(Argument, ast.Name) and Argument.id not in Buffers:
            Shape_Only[Argument.id] = max(Dimensions, Shape_Only.get(Argument.id, 0))
    for Name, Dimensions in sorted(Shape_Only.items()):
        Buffers[Name] = len(Buffers), Dimensions, Cell_Kind
    if not Buffers:
        return None
    Written = tuple(dict.fromkeys(Node.id for Node in Parts if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Store)))
    if set(Written) & (set(Buffers) | set(Bindings) | Helper_Names | {"range", "len"}):
        return None
    Loaded = _Reads_Before_Definition([Outer])[0]
    Inputs = tuple(sorted(Loaded - set(Buffers) - set(Bindings) - Helper_Names - Builtins - set(Random.values()) - {"range", "len"}))
    Carry = tuple(Name for Name in Written if Name in Inputs)
    Integers = {Node.target.id for Node in Parts if isinstance(Node, ast.For) and isinstance(Node.target, ast.Name)}
    Integers.update(Node.target.id for Node in ast.walk(Function) if isinstance(Node, ast.For) and isinstance(Node.target, ast.Name) and isinstance(Node.iter, ast.Call) and isinstance(Node.iter.func, ast.Name) and Node.iter.func.id == "range")
    Integers.update(Node.targets[0].id for Node in Parts if isinstance(Node, ast.Assign) and len(Node.targets) == 1 and isinstance(Node.targets[0], ast.Name) and isinstance(Node.value, ast.Constant) and type(Node.value.value) is int)
    Integers.update(Target.id for Node in ast.walk(Function) if isinstance(Node, ast.Assign) and isinstance(Node.value, ast.Constant) and type(Node.value.value) is int for Target in Node.targets if isinstance(Target, ast.Name) and Target.id in Inputs)
    if isinstance(Function, ast.FunctionDef):
        Integers.update(Argument.arg for Argument in Function.args.posonlyargs + Function.args.args + Function.args.kwonlyargs if isinstance(Argument.annotation, ast.Name) and Argument.annotation.id == "int")
    for Node in Parts:
        if isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id == "range":
            Integers.update(Part.id for Argument in Node.args for Part in ast.walk(Argument) if isinstance(Part, ast.Name) and Part.id in Inputs)
        if isinstance(Node, ast.Compare):
            Values = [Node.left, *Node.comparators]
            if any(isinstance(Value, ast.Name) and Value.id in Integers for Value in Values):
                Integers.update(Value.id for Value in Values if isinstance(Value, ast.Name) and Value.id in Inputs)
        if isinstance(Node, ast.Subscript):
            Integers.update(Part.id for Part in ast.walk(Node.slice) if isinstance(Part, ast.Name) and Part.id in Inputs)
    Types = {Name: "integer" if Name in Integers else "float" for Name in Inputs}
    Copies = any(isinstance(Node, ast.Assign) and isinstance(Node.value, ast.Name) for Node in Parts)
    Context = dict(Numeric_Region=True, Array_Region=Array, Builtins=Builtins, Random=Random, Local_Types=Types.copy(), Local_Slots=list(Inputs), Buffers=Buffers, Read_Buffers=Read_Buffers, Bindings=Bindings, Writes={}, Names=(), Indices=(), Output="", Result_Name="", Carry=Carry, Possibly_Fresh=set(), Dynamic_Identity=not Array and (Copies or bool(Builtins)))
    Context.update(Helpers=Helpers, Helper_Counter=[0], Helper_Roots={}, Helper_Globals={}, Helper_Used=set(), Helper_Operations=set())
    Calls, Fresh = set(), {Outer.target.id: 1}
    try:
        _Range(Outer.iter, Context, Calls)
        _Store_Name(Outer.target.id, "integer", Context)
        Program = _Program(Outer.body, Context, Calls, Fresh, 1)
    except _Fast_Unsupported:
        return None
    if not (Context["Writes"] or Carry):  # A region needs an observable result to justify extraction.
        return None
    Direct = [Node.value.id for Node in Parts if isinstance(Node, ast.Assign) and len(Node.targets) == 1 and isinstance(Node.targets[0], ast.Subscript) and isinstance(Node.value, ast.Name)]
    if len(Direct) != len(set(Direct)) and not Context['Dynamic_Identity']:
        return None
    Names = (*Buffers, *Inputs)
    Protected = tuple(Name for Name in Written if Name in Available)
    if not Module:
        if not set(Names) <= Available:
            return None
        Inside = {Node for Node in ast.walk(Function) if hasattr(Node, 'lineno') and Outer.lineno <= Node.lineno <= Outer.end_lineno} if Array or Normalized else set(Parts)
        Prior = {Node.id for Node in ast.walk(Function) if Node not in Inside and isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Store) and Node.lineno < Outer.lineno}
        Later_Reads = {Node.id for Node in ast.walk(Function) if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Load) and (Node.lineno, Node.col_offset) >= (Outer.end_lineno, Outer.end_col_offset)}  # Reused dead temporaries must not block a later independent reduction.
        if (set(Written) - {Outer.target.id}) & (Prior - Available) & Later_Reads:  # Retain the conservative boundary when a prior binding is still observed afterward.
            return None
    Probe = ast.parse("def _Pyceler_Probe(" + ", ".join(Names) + "):\n    pass").body[0]
    Probe.body = [copy.deepcopy(Outer), ast.parse("return (" + ", ".join((*Context["Writes"], *Carry)) + ",)").body[0]]
    Math = dict(Functions=tuple(sorted({Name for Root, Name, Module in Calls})), Bindings=tuple(sorted(Calls)), Backend_Requirements=tuple(sorted({_Fast_Call_Contracts[Name]["Backend"] for Root, Name, Module in Calls if _Fast_Call_Contracts[Name]["Backend"]})))
    Math['Global_Roots'] = {Root: Context['Helper_Globals'][Root] for Root, Name, Module in Calls if Root in Context['Helper_Globals']}
    Imports = tuple("import math as " + Root if Binding is None else "from math import " + Binding + " as " + Root for Root, Binding in Bindings.items())
    Imports = tuple(dict.fromkeys((*Imports, *(Import for Name in sorted(Context['Helper_Used']) for Import in Helpers[Name]['Imports']))))
    Plan = dict(Kind="numeric_region", Region=True, Module=Module, Scope="<module>" if Module else Function.name, Names=Names, Inputs=Inputs, Input_Types=Types, Probe_Inputs=_Probe_Inputs(Parts, Inputs, Carry), Buffers=Buffers, Read_Buffers=tuple(sorted(Read_Buffers)), Read_Kind=Cell_Kind, Writes=Context["Writes"], Written=Written, Carry=Carry, Output_Guards=Protected, Slots=Context["Local_Slots"], Program=Program, Dynamic_Identity=Context['Dynamic_Identity'], Index=Outer.target.id, Loops=[Node for Node in Parts if isinstance(Node, (ast.For, ast.While))], Statements=Outer.body, Range=ast.unparse(Outer.iter), Math=Math, Math_Imports=Imports, Builtins=tuple(sorted(Builtins)), Random=Random, Local_Bindings=tuple(Root for Root in (*Bindings, *set(Random.values())) if not Module and Root in Available), Probe=ast.fix_missing_locations(Probe), Transformations=("Buffered numeric list regions", "Typed nested control flow", "Ordered reductions and original final state"))
    Plan['Real_Inputs'] = _Real_Inputs(Outer, Inputs, Read_Buffers if Cell_Kind == 'float' else (), Carry, tuple(Root + '.' + Name if Module else Root for Root, Name, Module in Calls))
    Plan['Shape_Only'] = tuple(sorted(Shape_Only))
    Plan['Live_Outputs'] = _Live_Region_Outputs(Function, Outer, Written, Module)
    Plan.update(Helper_Roots=Context['Helper_Roots'], Helper_Globals=Context['Helper_Globals'], Helper_Sources=tuple((Name, Helpers[Name]['Source']) for Name in sorted(Context['Helper_Used'])), Helper_Operations=tuple(sorted(Context['Helper_Operations'])))
    Plan['Local_Bindings'] += tuple(Name for Name in Helper_Names if not Module and Name in Available)
    Plan["Parallel"] = 'python_power' not in Context['Helper_Operations'] and not any(isinstance(Node, ast.Pow) for Node in Parts) and _Independent_Outer_Storage(Plan)
    return Plan
# Extract outer regions first; inner candidates remain available when enclosing work is unsupported.
def _Numeric_Region_Plans(Tree, Edits, Scopes=None, Calls=None):
    Plans = {}
    Calls = _Call_Facts(Tree) if Calls is None else Calls
    Helpers = Calls['Helpers']
    Scope, Captures, Locals, Globals = '<module>', frozenset(), frozenset(), {}
    Occupied = [(Edit[1].lineno, Edit[1].end_lineno) for Edit in Edits.values()]
    Maps = {Edit[1].lineno: Edit[3] for Edit in Edits.values() if Edit[3] is not None and Edit[3].get('Kind') in (None, 'math_map', 'array_region') and not Edit[3].get('Clear')}
    def Visit(Function, Statements, Available, Module):
        Bound = Available.copy()
        for Node in Statements:
            Existing = Maps.get(getattr(Node, 'lineno', None))
            Contained = _Contained_Scalar_Edits(Node, Edits)
            if isinstance(Node, ast.For) and not _Region_Loop_Partition(Node) and (Existing is not None or not any(Node.lineno <= End and Node.end_lineno >= Start and (Start, End) not in Contained.values() for Start, End in Occupied)):
                Plan = _Iterator_Plan(_Numeric_Region_Plan, Function, Node, Bound, Module, Helpers=Helpers, Call_Bindings=Calls['Math'])
                Integer_Plan = _Iterator_Plan(_Numeric_Region_Plan, Function, Node, Bound, Module, "integer", Helpers=Helpers, Call_Bindings=Calls['Math'])
                if Plan is None:
                    Plan = Integer_Plan
                elif Integer_Plan is not None and Plan["Read_Buffers"]:
                    Plan["Alternate"] = Integer_Plan
                if Plan is not None:
                    if not _Bind_Region_Scope(Plan, Scope, Captures, Locals, Globals, Bound):
                        continue
                    if Existing is not None:
                        Imports = _Fast_Imports(Existing) if Existing.get('Kind') == 'math_map' else None
                        if Imports is not None and not all(Root in Imports and Imports[Root] == (None if Imported_Module else Name) for Root, Name, Imported_Module in Plan['Math']['Bindings']):
                            continue
                        if set(Plan['Names']) == set(Existing['Names']):
                            Plan['Selection_Key'] = 'list_integer' if Plan['Read_Kind'] == 'integer' else 'list_float'
                            if 'Alternate' in Plan:
                                Plan['Alternate']['Selection_Key'] = 'list_integer'
                            Existing['List_Alternative'] = Plan
                        continue
                    Plans[Node.lineno] = (Plan["Names"], Node, Function, Plan)
                    for Previous in Contained:
                        Edits.pop(Previous)
                    Occupied.append((Node.lineno, Node.end_lineno))
                    continue
            if isinstance(Node, ast.Assign):
                Bound.update(Part.id for Target in Node.targets for Part in ast.walk(Target) if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Store))
            elif isinstance(Node, (ast.Import, ast.ImportFrom)):
                Bound.update(Alias.asname or Alias.name.split(".")[0] for Alias in Node.names if Alias.name != "*")
            elif isinstance(Node, ast.If):
                Left = Visit(Function, Node.body, Bound, Module)
                Right = Visit(Function, Node.orelse, Bound, Module)
                Bound.update(Left & Right)
            elif isinstance(Node, (ast.For, ast.While)):
                Local = Bound | (_Binding_Targets(Node.target) if isinstance(Node, ast.For) else set())
                Visit(Function, Node.body, Local, Module)
                Visit(Function, Node.orelse, Bound, Module)
        return Bound
    Visit(Tree, Tree.body, set(), True)
    for Function, Scope, Captures, Locals, Globals in _Function_Scopes(Tree) if Scopes is None else Scopes:
        if not isinstance(Function, ast.FunctionDef) or Function.decorator_list or getattr(Function, "type_params", ()):
            continue
        Parts = list(ast.walk(Function))
        if any(isinstance(Node, (ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom, ast.Try, ast.Delete, ast.Lambda, ast.ClassDef)) or isinstance(Node, ast.FunctionDef) and Node is not Function or isinstance(Node, ast.Name) and Node.id in {"locals", "globals", "vars", "eval", "exec", "_getframe", "currentframe"} for Node in Parts):
            continue
        Names = {Argument.arg for Argument in Function.args.posonlyargs + Function.args.args + Function.args.kwonlyargs}
        Visit(Function, Function.body, Names | set(Captures), False)
    return Plans
