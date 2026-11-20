import ast
import copy
from .Fast_Math import _Fast_Statements, _Fast_Unsupported
# Recognize nested list-grid operations and prove indexing and object-freshness requirements.
def _Offset(Node, Index):
    if isinstance(Node, ast.Name) and Node.id == Index:
        return 0
    if isinstance(Node, ast.BinOp) and isinstance(Node.op, (ast.Add, ast.Sub)) and isinstance(Node.left, ast.Name) and Node.left.id == Index:
        try:
            Value = ast.literal_eval(Node.right)
        except (ValueError, TypeError):
            return None
        if type(Value) is int and abs(Value) <= 64:
            return Value if isinstance(Node.op, ast.Add) else -Value
    return None

def _Cell(Node, Indices):
    if not isinstance(Node, ast.Subscript) or not isinstance(Node.value, ast.Subscript) or not isinstance(Node.value.value, ast.Name):
        return None
    Row, Column = _Offset(Node.value.slice, Indices[0]), _Offset(Node.slice, Indices[1])
    return (Node.value.value.id, Row, Column) if Row is not None and Column is not None else None

def _Bound(Node):
    if isinstance(Node, ast.Constant):
        return type(Node.value) is int and abs(Node.value) <= 2**31
    if isinstance(Node, ast.Name):
        return Node.id not in ("range", "len")
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, (ast.UAdd, ast.USub)):
        return _Bound(Node.operand)
    if isinstance(Node, ast.BinOp) and isinstance(Node.op, (ast.Add, ast.Sub)):
        return _Bound(Node.left) and _Bound(Node.right)
    if isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id == "len" and len(Node.args) == 1 and not Node.keywords:
        Value = Node.args[0]
        return isinstance(Value, ast.Name) or isinstance(Value, ast.Subscript) and isinstance(Value.value, ast.Name) and isinstance(Value.slice, ast.Constant) and type(Value.slice.value) is int and Value.slice.value == 0
    return False
# Range operands need integer semantics; float-valued indices require explicit guarded conversion.
def _Range(Node):
    return isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id == "range" and not Node.keywords and 1 <= len(Node.args) <= 2 and all(_Bound(Argument) for Argument in Node.args)

class _Reads(ast.NodeTransformer):
    def __init__(self, Indices, Reads):
        self._Indices, self._Reads = Indices, Reads

    def visit_Subscript(self, Node):
        Cell = _Cell(Node, self._Indices)
        if Cell is None or not isinstance(Node.ctx, ast.Load):
            raise _Fast_Unsupported()
        if Cell not in self._Reads:
            self._Reads.append(Cell)
        return ast.copy_location(ast.Name(id="_Pyceler_Grid_Read_" + str(self._Reads.index(Cell)), ctx=ast.Load()), Node)

def _Fresh(Node, Known):
    if isinstance(Node, ast.Name):
        return Node.id in Known
    if isinstance(Node, ast.IfExp):
        return _Fresh(Node.body, Known) and _Fresh(Node.orelse, Known)
    if isinstance(Node, ast.BinOp) or isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.USub):
        return any(isinstance(Part, (ast.Name, ast.Subscript)) for Part in ast.walk(Node))
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.UAdd):
        return _Fresh(Node.operand, Known)
    return False

def _Assignments(Statements, Defined, Fresh):
    for Node in Statements:
        if isinstance(Node, ast.If):
            Left, Right = Defined.copy(), Defined.copy()
            Left_Fresh, Right_Fresh = Fresh.copy(), Fresh.copy()
            _Assignments(Node.body, Left, Left_Fresh)
            _Assignments(Node.orelse, Right, Right_Fresh)
            Defined.update(Left & Right)
            Fresh.clear()
            Fresh.update(Left_Fresh & Right_Fresh)
        elif isinstance(Node, ast.Assign) and len(Node.targets) == 1 and isinstance(Node.targets[0], ast.Name):
            Name = Node.targets[0].id
            Defined.add(Name)
            if _Fresh(Node.value, Fresh):
                Fresh.add(Name)
            else:
                Fresh.discard(Name)
        else:
            raise _Fast_Unsupported()

def _List_Grid_Plan(Function, Outer, Available, Module):
    if not isinstance(Outer, ast.For) or Outer.orelse or len(Outer.body) != 1 or not isinstance(Outer.body[0], ast.For):
        return None
    Inner = Outer.body[0]
    if Inner.orelse or not all(isinstance(Loop.target, ast.Name) and _Range(Loop.iter) for Loop in (Outer, Inner)):
        return None
    Indices = Outer.target.id, Inner.target.id
    if len(set(Indices)) != 2 or set(Indices) & {"range", "len"}:
        return None
    Last = Inner.body[-1]
    if not isinstance(Last, ast.Assign) or len(Last.targets) != 1:
        return None
    Output = _Cell(Last.targets[0], Indices)
    if Output is None or Output[1:] != (0, 0):
        return None
    Bound_Names = {Node.id for Loop in (Outer, Inner) for Node in ast.walk(Loop.iter) if isinstance(Node, ast.Name)} - {"range", "len"}
    if Bound_Names & set(Indices):
        return None
    Parts = list(ast.walk(Inner))
    if any(isinstance(Node, (ast.NamedExpr, ast.Lambda, ast.Await)) or isinstance(Node, ast.Name) and Node.id.startswith("_Pyceler_") for Node in Parts):
        return None
    Defined, Fresh, Reads = set(), set(), []
    Body = copy.deepcopy(Inner.body)
    Body[-1].targets = [ast.Name(id="_Pyceler_Grid_Result", ctx=ast.Store())]
    try:
        _Assignments(Inner.body[:-1], Defined, Fresh)
        if not _Fresh(Last.value, Fresh) or Defined & (Bound_Names | set(Indices) | {"range", "len", Output[0]}):
            return None
        Transformed = [_Reads(Indices, Reads).visit(Statement) for Statement in Body]
        Inputs = ["_Pyceler_Grid_Read_" + str(Position) for Position in range(len(Reads))]
        Context = dict(Local_Types={Name: "float" for Name in Inputs}, Local_Slots=Inputs.copy(), Names=(), Indices=Indices, Output="", Result_Name="")
        Context["Local_Types"].update({Name: "integer" for Name in Indices})
        Context["Local_Slots"].extend(Indices)
        Program = _Fast_Statements(Transformed, Context, {}, [], set())
    except _Fast_Unsupported:
        return None
    Grids = tuple(dict.fromkeys([Read[0] for Read in Reads] + [Output[0]]))
    Controls = tuple(sorted(Bound_Names - set(Grids)))
    if not Reads or len(Grids) > 8 or Output[0] in {Read[0] for Read in Reads} or (Defined | set(Indices)) & set(Grids):
        return None
    Names = (*Grids, *Controls)
    Written = tuple(dict.fromkeys([Node.id for Statement in Inner.body[:-1] for Node in ast.walk(Statement) if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Store)]))
    if not set(Written) <= Defined or any(Context["Local_Types"].get(Name) != "float" for Name in (*Written, "_Pyceler_Grid_Result")):
        return None
    Protected = tuple(Name for Name in (*Indices, *Written) if Name in Available)
    if not Module:
        if not set(Names) <= Available:
            return None
        Inside = set(ast.walk(Outer))
        Prior = {Node.id for Node in ast.walk(Function) if Node not in Inside and isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Store)}
        if (set(Indices) | set(Written)) & (Prior - Available):
            return None
    Probe = ast.parse("def _Pyceler_Probe(" + ", ".join(Names) + "):\n    pass").body[0]
    Probe.body = [copy.deepcopy(Outer), ast.parse("return " + Output[0]).body[0]]
    return dict(Kind="list_grid", Region=True, Module=Module, Scope="<module>" if Module else Function.name, Names=Names, Grids=Grids, Controls=Controls,
                Arrays=set(Grids), Output=Output[0], Indices=Indices, Written=Written, Output_Guards=Protected, Reads=tuple(Reads), Program=Program,
                Slots=Context["Local_Slots"], Loops=[Outer, Inner], Statements=Inner.body, Ranges=tuple(ast.unparse(Loop.iter) for Loop in (Outer, Inner)),
                Probe=ast.fix_missing_locations(Probe), Transformations=("Rectangular list-grid extraction", "Buffered native neighborhood arithmetic", "Original list identity and ordered final state"))

def _List_Grid_Plans(Tree, Edits):
    Plans = {}
    Occupied = [(Edit[1].lineno, Edit[1].end_lineno) for Edit in Edits.values()]
    def Visit(Function, Statements, Available, Module):
        Bound = Available.copy()
        for Node in Statements:
            if isinstance(Node, ast.For) and not any(Node.lineno <= End and Node.end_lineno >= Start for Start, End in Occupied):
                Plan = _List_Grid_Plan(Function, Node, Bound, Module)
                if Plan is not None:
                    Plans[Node.lineno] = (Plan["Names"], Node, Function, Plan)
                    Occupied.append((Node.lineno, Node.end_lineno))
                    continue
            if isinstance(Node, ast.Assign):
                Bound.update(Part.id for Target in Node.targets for Part in ast.walk(Target) if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Store))
            elif isinstance(Node, ast.If):
                Left = Visit(Function, Node.body, Bound, Module)
                Right = Visit(Function, Node.orelse, Bound, Module)
                Bound.update(Left & Right)
            elif isinstance(Node, (ast.For, ast.While)):
                Local = Bound | ({Node.target.id} if isinstance(Node, ast.For) and isinstance(Node.target, ast.Name) else set())
                Visit(Function, Node.body, Local, Module)
                Visit(Function, Node.orelse, Bound, Module)
        return Bound
    Visit(Tree, Tree.body, set(), True)
    for Function in Tree.body:
        if not isinstance(Function, ast.FunctionDef) or Function.decorator_list or getattr(Function, "type_params", ()):
            continue
        Parts = list(ast.walk(Function))
        if any(isinstance(Node, (ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom, ast.Try, ast.Delete, ast.Lambda, ast.ClassDef)) or isinstance(Node, ast.FunctionDef) and Node is not Function or isinstance(Node, ast.Name) and Node.id in {"locals", "globals", "vars", "eval", "exec", "_getframe", "currentframe"} for Node in Parts):
            continue
        Names = {Argument.arg for Argument in Function.args.posonlyargs + Function.args.args + Function.args.kwonlyargs}
        Visit(Function, Function.body, Names, False)
    return Plans
