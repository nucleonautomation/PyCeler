import ast
import copy
import io
import struct
import tokenize
from .Math_Registry import _Math_Calls, _Math_Inspector, _Registry_Version
from .Fast_Math import _Fast_Math_Plan, _Fast_Math_Kernel

def _Math_Literal(Node):
    if isinstance(Node, ast.Constant):
        return type(Node.value) in (int, float, complex, bool, str, bytes, type(None), type(Ellipsis))
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, (ast.UAdd, ast.USub)) and isinstance(Node.operand, ast.Constant):
        return type(Node.operand.value) in (int, float, complex)
    return isinstance(Node, ast.Tuple) and all(_Math_Literal(Element) for Element in Node.elts)

def _Math_Bound(Call, Names):
    if not isinstance(Call, ast.Call) or not isinstance(Call.func, ast.Name) or Call.func.id != "range" or Call.keywords:
        return None
    if len(Call.args) == 1:
        Bound = Call.args[0]
    elif len(Call.args) in (2, 3) and isinstance(Call.args[0], ast.Constant) and type(Call.args[0].value) is int and Call.args[0].value == 0:
        if len(Call.args) == 3 and (not isinstance(Call.args[2], ast.Constant) or type(Call.args[2].value) is not int or Call.args[2].value != 1):
            return None
        Bound = Call.args[1]
    else:
        return None
    if isinstance(Bound, ast.Call) and isinstance(Bound.func, ast.Name) and Bound.func.id == "len" and len(Bound.args) == 1 and not Bound.keywords:
        Value = Bound.args[0]
        if isinstance(Value, ast.Name) and Value.id in Names:
            return Value.id, 0
    if isinstance(Bound, ast.Subscript) and isinstance(Bound.value, ast.Attribute) and Bound.value.attr == "shape" and isinstance(Bound.value.value, ast.Name):
        if Bound.value.value.id in Names and isinstance(Bound.slice, ast.Constant) and type(Bound.slice.value) is int and Bound.slice.value >= 0:
            return Bound.value.value.id, Bound.slice.value
    return None

def _Math_Expression(Node, Known, Globals, Calls, Arrays, Names, Indices):
    if _Math_Literal(Node):
        return True
    if isinstance(Node, ast.Name):
        return Node.id in Known or Node.id in Globals and Globals[Node.id] is not None and Globals[Node.id]["Status"] == "Imported"
    if isinstance(Node, ast.Attribute):
        return Node.attr in {"real", "imag"} and _Math_Expression(Node.value, Known, Globals, Calls, Arrays, Names, Indices) or isinstance(Node.value, ast.Name) and Node.value.id in Globals and Globals[Node.value.id] is not None and Globals[Node.value.id]["Status"] == "Imported"
    if isinstance(Node, ast.Subscript):
        if isinstance(Node.value, ast.Name) and Node.value.id in Names:
            Positions = Node.slice.elts if isinstance(Node.slice, ast.Tuple) else (Node.slice,)
            if not Positions or len(Positions) > len(Indices) or not all(isinstance(Position, ast.Name) and Position.id in Indices for Position in Positions):
                return False
            Arrays.add(Node.value.id)
            return True
        return _Math_Literal(Node.slice) and _Math_Expression(Node.value, Known, Globals, Calls, Arrays, Names, Indices)
    if isinstance(Node, ast.Call):
        Call = Calls.get((Node.lineno, Node.col_offset))
        if Call is None or Call["Status"] != "Recognized":
            return False
        return all(_Math_Expression(Argument.value if isinstance(Argument, ast.Starred) else Argument, Known, Globals, Calls, Arrays, Names, Indices) for Argument in Node.args) and all(Keyword.arg is not None and _Math_Expression(Keyword.value, Known, Globals, Calls, Arrays, Names, Indices) for Keyword in Node.keywords)
    if isinstance(Node, ast.BinOp):
        if _Math_Literal(Node.left) and _Math_Literal(Node.right):
            return False
        return isinstance(Node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift)) and _Math_Expression(Node.left, Known, Globals, Calls, Arrays, Names, Indices) and _Math_Expression(Node.right, Known, Globals, Calls, Arrays, Names, Indices)
    if isinstance(Node, ast.UnaryOp):
        return isinstance(Node.op, (ast.UAdd, ast.USub, ast.Not, ast.Invert)) and _Math_Expression(Node.operand, Known, Globals, Calls, Arrays, Names, Indices)
    if isinstance(Node, (ast.Tuple, ast.List)):
        return all(_Math_Expression(Element, Known, Globals, Calls, Arrays, Names, Indices) for Element in Node.elts)
    if isinstance(Node, ast.Compare):
        return all(not isinstance(Operator, (ast.Is, ast.IsNot, ast.In, ast.NotIn)) for Operator in Node.ops) and all(_Math_Expression(Value, Known, Globals, Calls, Arrays, Names, Indices) for Value in (Node.left, *Node.comparators))
    if isinstance(Node, ast.BoolOp):
        return all(_Math_Expression(Value, Known, Globals, Calls, Arrays, Names, Indices) for Value in Node.values)
    if isinstance(Node, ast.IfExp):
        return all(_Math_Expression(Value, Known, Globals, Calls, Arrays, Names, Indices) for Value in (Node.test, Node.body, Node.orelse))
    return False

def _Math_Statements(Statements, Known, Globals, Calls, Arrays, Names, Indices, Output, Locals):
    for Statement in Statements:
        if isinstance(Statement, ast.If):
            if not _Math_Expression(Statement.test, Known, Globals, Calls, Arrays, Names, Indices):
                return False
            Yes, No = set(Known), set(Known)
            if not _Math_Statements(Statement.body, Yes, Globals, Calls, Arrays, Names, Indices, Output, Locals) or not _Math_Statements(Statement.orelse, No, Globals, Calls, Arrays, Names, Indices, Output, Locals):
                return False
            Known.update(Yes & No)
            continue
        if isinstance(Statement, (ast.Continue, ast.Pass)):
            continue
        if not isinstance(Statement, (ast.Assign, ast.AugAssign)) or isinstance(Statement, ast.Assign) and len(Statement.targets) != 1:
            return False
        Target = Statement.targets[0] if isinstance(Statement, ast.Assign) else Statement.target
        if not _Math_Expression(Statement.value, Known, Globals, Calls, Arrays, Names, Indices):
            return False
        if isinstance(Target, ast.Name):
            if Target.id in Names or Target.id in Indices or Target.id in Globals or isinstance(Statement, ast.AugAssign) and Target.id not in Known:
                return False
            Known.add(Target.id)
            Locals.add(Target.id)
        elif isinstance(Target, ast.Subscript) and isinstance(Target.value, ast.Name) and Target.value.id == Output:
            Positions = Target.slice.elts if isinstance(Target.slice, ast.Tuple) else (Target.slice,)
            if tuple(Position.id if isinstance(Position, ast.Name) else None for Position in Positions) != Indices:
                return False
        else:
            return False
    return True

def _Math_Map_Plans(Tree, Text=None):
    Calls = {(Call["Line"], Call["Column"]): Call for Call in _Math_Calls(Tree)}
    Inspector = _Math_Inspector(Tree, None, None)
    Inspector._Prepare()
    Globals = Inspector._Globals
    Plans = {}
    for Function in Tree.body:
        if not isinstance(Function, ast.FunctionDef) or Function.decorator_list or getattr(Function, "type_params", ()):
            continue
        Body = Function.body[1:] if ast.get_docstring(Function, clean=False) is not None else Function.body
        Args = Function.args
        Names = tuple(Argument.arg for Argument in Args.posonlyargs + Args.args)
        if Args.vararg or Args.kwarg or Args.kwonlyargs or len(Body) != 2 or not isinstance(Body[0], ast.For) or not isinstance(Body[1], ast.Return) or not isinstance(Body[1].value, ast.Name):
            continue
        Output = Body[1].value.id
        if Output not in Names or any(Name in {"range", "len"} for Name in Names) or Body[0].lineno == Function.lineno:
            continue
        Loops, Indices, Arrays, Bounds = [], [], {Output}, []
        Statements = Body[:-1]
        while len(Statements) == 1 and isinstance(Statements[0], ast.For):
            Loop = Statements[0]
            Bound = _Math_Bound(Loop.iter, Names)
            if Loop.orelse or Bound is None or not isinstance(Loop.target, ast.Name) or Loop.target.id in Names or Loop.target.id in Indices or Loop.target.id in {"range", "len"}:
                break
            Loops.append(Loop)
            Indices.append(Loop.target.id)
            Arrays.add(Bound[0])
            Bounds.append(Bound)
            Statements = Loop.body
        if not Loops or any(Axis >= len(Loops) for Name, Axis in Bounds):
            continue
        Relevant = [Call for Call in Calls.values() if Function.lineno <= Call["Line"] <= Function.end_lineno and Call["Module"] in {"math", "cmath", "numpy", "builtins"}]
        if not Relevant or any(Call["Status"] != "Recognized" for Call in Relevant):
            continue
        Locals = set()
        if not _Math_Statements(Statements, set(Names) | set(Indices), Globals, Calls, Arrays, Names, tuple(Indices), Output, Locals):
            continue
        Global_Names = {Node.id for Node in ast.walk(Loops[0]) if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Load)} - set(Names) - set(Indices) - Locals - {"range", "len"}
        if any("_Pyceler_" in Name or Name not in Globals or Globals[Name] is None or Globals[Name]["Status"] != "Imported" for Name in Global_Names):
            continue
        Imports = []
        for Name in sorted(Global_Names):
            Binding = Globals[Name]
            if Binding["Name"] is None:
                Imports.append("import " + Binding["Module"] + " as " + Name)
            else:
                Imports.append("from " + Binding["Module"] + " import " + Binding["Name"] + " as " + Name)
        Plan = dict(Kind="math_map", Names=Names, Output=Output, Arrays=Arrays, Scalars=set(Names) - Arrays, Indices=tuple(Indices), Loops=Loops,
                    Start=Body[0].lineno, Function=Function, Body=Body, Locals=tuple(sorted(Locals)), Bounds=tuple(Bounds),
                    Math_Imports=tuple(Imports), Math_Functions=tuple(sorted({Call["Qualified_Name"] for Call in Relevant})),
                    Registry_Version=_Registry_Version, Numerical_Contract="Ordered original Python objects and library calls; compiled serial iteration with GIL, live bindings and original ndarray assignment semantics")
        Plan["Fast_Math"] = _Fast_Math_Plan(Plan)
        Plans[Loops[0].lineno] = (Names, Loops[0], Function, Plan)
    return Plans

class _Math_Rewrite(ast.NodeTransformer):
    def __init__(self, Locals, Line):
        self._Locals = {Name: f"_Pyceler_Math_Value_{Line}_{Index}" for Index, Name in enumerate(Locals)}
        self._Line = Line
        self._Constants = []

    def _Literal(self, Node):
        Value = ast.literal_eval(Node)
        Key = type(Value).__name__, repr(Value)
        Keys = [(type(Item).__name__, repr(Item)) for Item in self._Constants]
        if Key not in Keys:
            self._Constants.append(Value)
        return ast.copy_location(ast.Name(id=f"_Pyceler_Math_Literal_{self._Line}_{Keys.index(Key) if Key in Keys else len(Keys)}", ctx=ast.Load()), Node)

    def visit_Constant(self, Node):
        return self._Literal(Node)

    def visit_UnaryOp(self, Node):
        return self._Literal(Node) if _Math_Literal(Node) else self.generic_visit(Node)

    def visit_Tuple(self, Node):
        return self._Literal(Node) if isinstance(Node.ctx, ast.Load) and _Math_Literal(Node) else self.generic_visit(Node)

    def visit_For(self, Node):
        Node = self.generic_visit(Node)
        Tick = ast.AugAssign(target=ast.Name(id="_Pyceler_Math_Ticks", ctx=ast.Store()), op=ast.Add(), value=ast.Constant(value=1))
        Check = ast.Expr(value=ast.Call(func=ast.Name(id=f"_Pyceler_Math_Checkpoint_{self._Line}", ctx=ast.Load()), args=[ast.Name(id="_Pyceler_Math_Ticks", ctx=ast.Load())], keywords=[]))
        Node.body[:0] = [ast.copy_location(Tick, Node), ast.copy_location(Check, Node)]
        return Node

    def visit_Name(self, Node):
        if Node.id in self._Locals:
            return ast.copy_location(ast.Name(id=self._Locals[Node.id], ctx=Node.ctx), Node)
        if isinstance(Node.ctx, ast.Load) and Node.id not in self._Locals:
            return ast.copy_location(ast.Call(func=ast.Name(id=f"_Pyceler_Math_Name_{self._Line}", ctx=ast.Load()),
                                             args=[ast.Name(id="_Pyceler_Math_Globals", ctx=ast.Load()), ast.Name(id="_Pyceler_Math_Builtins", ctx=ast.Load()), ast.Constant(value=Node.id)], keywords=[]), Node)
        return Node

def _Math_Literal_Key(Value):
    if type(Value) is float:
        return "float", struct.unpack(">Q", struct.pack(">d", Value))[0]
    if type(Value) is complex:
        return "complex", _Math_Literal_Key(Value.real)[1], _Math_Literal_Key(Value.imag)[1]
    if type(Value) is tuple:
        return "tuple", tuple(_Math_Literal_Key(Item) for Item in Value)
    return "value", Value

def _Math_Literal_Source(Value):
    return repr(_Math_Literal_Key(Value))

def _Math_Constant_Node(Value):
    if type(Value) is tuple:
        return ast.Tuple(elts=[_Math_Constant_Node(Item) for Item in Value], ctx=ast.Load())
    return ast.Constant(value=Value)

def _Math_Map_Constant_Source(Plan):
    Rewrite = _Math_Rewrite(Plan["Names"] + Plan["Indices"] + Plan["Locals"], 0)
    for Statement in Plan["Body"]:
        Rewrite.visit(copy.deepcopy(Statement))
    return ast.unparse(ast.fix_missing_locations(_Math_Constant_Node(tuple(Rewrite._Constants))))

class _Module_Anchor_Rewrite(ast.NodeTransformer):
    def visit_ImportFrom(self, Node):
        return ast.copy_location(ast.Pass(), Node) if any(Alias.name == "*" for Alias in Node.names) else Node

def _Module_Constant_Anchor(Node, Line, Prefix="_Pyceler_"):
    Loop = _Module_Anchor_Rewrite().visit(copy.deepcopy(Node))
    Loop.orelse = []
    Function = ast.parse(f"def {Prefix}Module_Constants_{Line}():\n    pass").body[0]
    Function.body = [Loop]
    return ast.unparse(ast.fix_missing_locations(Function))

def _Native_Prefix(Source, Prefix):
    if Prefix == "_Pyceler_":
        return Source
    Lines = Source.splitlines(keepends=True)
    Offsets = [0]
    for Line in Lines:
        Offsets.append(Offsets[-1] + len(Line))
    Changes = []
    for Token in tokenize.generate_tokens(io.StringIO(Source).readline):
        Value = Token.string
        Replace = Token.type == tokenize.NAME and Value.startswith("_Pyceler_")
        if Token.type == tokenize.STRING and "_Pyceler_" in Value:
            Position = Token.start[0] - 2
            while Position >= 0:
                Previous = Lines[Position]
                if Previous.strip() and len(Previous) - len(Previous.lstrip()) < Token.start[1]:
                    Replace = Previous.strip() == "cdef extern from *:"
                    break
                Position -= 1
        if Replace:
            Changes.append((Offsets[Token.start[0] - 1] + Token.start[1], Offsets[Token.end[0] - 1] + Token.end[1], Value.replace("_Pyceler_", Prefix)))
    for Start, End, Value in reversed(Changes):
        Source = Source[:Start] + Value + Source[End:]
    return Source

def _Module_Constant_Kernel(Line):
    Prefix = f"_Pyceler_Module_Constants_{Line}_"
    return "\n".join([f"from libc.stdint cimport uint64_t as {Prefix}UInt64", f"from libc.string cimport memcpy as {Prefix}Copy_Bits",
                     f"cdef {Prefix}UInt64 {Prefix}Bits(object Value) except *:", "    cdef double Number = Value", f"    cdef {Prefix}UInt64 Pattern",
                     "    if sizeof(Number) != sizeof(Pattern):", "        raise TypeError('Unsupported native floating representation')",
                     f"    {Prefix}Copy_Bits(&Pattern, &Number, sizeof(Pattern))", "    return Pattern",
                     f"cdef object {Prefix}Key(object Value):", "    import builtins as B", "    cdef object Kind = B.type(Value)",
                     "    if Value is None or Value is Ellipsis or Kind in (B.bool, B.int, B.str, B.bytes):", "        return Kind, Value",
                     "    if Kind is B.float:", f"        return Kind, {Prefix}Bits(Value)", "    if Kind is B.complex:", f"        return Kind, {Prefix}Bits(Value.real), {Prefix}Bits(Value.imag)",
                     "    if Kind is B.tuple:", f"        return Kind, B.tuple({Prefix}Key(Item) for Item in Value)",
                     "    if Kind is B.frozenset:", f"        return Kind, B.frozenset({Prefix}Key(Item) for Item in Value)", "    return None",
                     f"cdef dict {Prefix}Pool(object Code):", "    import builtins as B", "    cdef object Code_Type = B.type(Code)",
                     "    cdef list Pending = [Code]", "    cdef dict Pool = {}", "    cdef object Value, Key",
                     "    while Pending:", "        Value = Pending.pop()", "        if B.type(Value) is Code_Type:", "            Pending.extend(Value.co_consts)", "            continue",
                     f"        Key = {Prefix}Key(Value)", "        if Key is not None and Key not in Pool:", "            Pool[Key] = Value",
                     "        if B.type(Value) in (B.tuple, B.frozenset):", "            Pending.extend(Value)", "    return Pool",
                     f"cdef object {Prefix}Value(object Value, dict Pool, object Code_Type):", "    import builtins as B", "    cdef object Key, Kind = B.type(Value)",
                     "    if Kind is Code_Type:", f"        return {Prefix}Code(Value, Pool)", f"    Key = {Prefix}Key(Value)",
                     "    if Key is not None and Key in Pool:", "        return Pool[Key]", "    if Kind is B.tuple:",
                     f"        return B.tuple({Prefix}Value(Item, Pool, Code_Type) for Item in Value)", "    if Kind is B.frozenset:",
                     f"        return B.frozenset({Prefix}Value(Item, Pool, Code_Type) for Item in Value)", "    return Value",
                     f"cdef object {Prefix}Code(object Code, dict Pool):", "    import builtins as B", "    cdef object Code_Type = B.type(Code)",
                     f"    return Code.replace(co_consts=B.tuple({Prefix}Value(Value, Pool, Code_Type) for Value in Code.co_consts))"]) + "\n"

def _Math_Map_Kernel(Plan, Line, Parallel=False):
    Names = Plan["Names"]
    Locals = Names + Plan["Indices"] + Plan["Locals"]
    Rewrite = _Math_Rewrite(Locals, Line)
    Parameters = tuple(Rewrite._Locals[Name] for Name in Names)
    Rewritten = [ast.fix_missing_locations(Rewrite.visit(copy.deepcopy(Statement))) for Statement in Plan["Body"]]
    Fast = Plan.get("Fast_Math")
    Iterator = ast.unparse(Rewritten[0].iter) if Fast else None
    if Fast:
        Rewritten[0].iter = ast.Name(id="_Pyceler_Math_Iterator", ctx=ast.Load())
    Body = [ast.unparse(Statement) for Statement in Rewritten]
    Prefix = f"_Pyceler_Math_{Line}"
    Source = [f"from libc.stdint cimport uint64_t as {Prefix}_UInt64", f"from libc.string cimport memcpy as {Prefix}_Copy_Bits",
              f"cdef {Prefix}_UInt64 {Prefix}_Bits_Value(object Value) except *:", "    cdef double Number = Value", f"    cdef {Prefix}_UInt64 Pattern",
              "    if sizeof(Number) != sizeof(Pattern):", "        raise TypeError('Unsupported native floating representation')",
              f"    {Prefix}_Copy_Bits(&Pattern, &Number, sizeof(Pattern))", "    return Pattern",
              "cdef extern from \"Python.h\":", f"    int _Pyceler_Math_Signals_{Line} \"PyErr_CheckSignals\"() except -1",
              f"cdef void _Pyceler_Math_Checkpoint_{Line}(unsigned int Count) except *:", f"    _Pyceler_Math_Signals_{Line}()",
              "    if Count & 1023 == 0:", "        _Pyceler_Scheduler_Yield()",
              f"cdef object _Pyceler_Math_Name_{Line}(dict Namespace, dict Builtins, str Name):",
              "    if Name in Namespace:", "        return Namespace[Name]", "    if Name in Builtins:", "        return Builtins[Name]",
              "    raise NameError(\"name '\" + Name + \"' is not defined\", name=Name)",
              f"cdef bint {Prefix}_Same_Literal(object Value, object Expected) except -1:",
              "    import builtins as _Pyceler_Math_B", "    cdef object Kind = _Pyceler_Math_B.type(Value)", "    cdef Py_ssize_t Position",
              "    if Kind is not _Pyceler_Math_B.type(Expected):", "        return False",
              "    if Kind is _Pyceler_Math_B.float:", f"        return {Prefix}_Bits_Value(Value) == {Prefix}_Bits_Value(Expected)",
              "    if Kind is _Pyceler_Math_B.complex:", f"        return {Prefix}_Bits_Value(Value.real) == {Prefix}_Bits_Value(Expected.real) and {Prefix}_Bits_Value(Value.imag) == {Prefix}_Bits_Value(Expected.imag)",
              "    if Kind is _Pyceler_Math_B.tuple:", "        if _Pyceler_Math_B.len(Value) != _Pyceler_Math_B.len(Expected):", "            return False",
              "        for Position in range(_Pyceler_Math_B.len(Value)):", f"            if not {Prefix}_Same_Literal(Value[Position], Expected[Position]):", "                return False",
              "        return True", "    return Value == Expected",
              f"cdef bint {Prefix}_Literal_Key_Matches(object Value, tuple Key) except -1:", "    import builtins as _Pyceler_Math_B",
              "    cdef object Kind = _Pyceler_Math_B.type(Value)", "    cdef Py_ssize_t Position",
              "    if Key[0] == 'float':", f"        return Kind is _Pyceler_Math_B.float and {Prefix}_Bits_Value(Value) == <{Prefix}_UInt64>Key[1]",
              "    if Key[0] == 'complex':", f"        return Kind is _Pyceler_Math_B.complex and {Prefix}_Bits_Value(Value.real) == <{Prefix}_UInt64>Key[1] and {Prefix}_Bits_Value(Value.imag) == <{Prefix}_UInt64>Key[2]",
              "    if Key[0] == 'tuple':", "        if Kind is not _Pyceler_Math_B.tuple or _Pyceler_Math_B.len(Value) != _Pyceler_Math_B.len(Key[1]):", "            return False",
              "        for Position in range(_Pyceler_Math_B.len(Value)):", f"            if not {Prefix}_Literal_Key_Matches(Value[Position], Key[1][Position]):", "                return False",
              "        return True", "    return Kind is _Pyceler_Math_B.type(Key[1]) and Value == Key[1]",
              f"cdef object {Prefix}_Literal(tuple Constants, object Expected, object Missing, bint Encoded):",
              "    cdef object Value, Found", "    for Value in Constants:",
              f"        if ({Prefix}_Literal_Key_Matches(Value, Expected) if Encoded else {Prefix}_Same_Literal(Value, Expected)):", "            return Value",
              "        if type(Value) is tuple:", f"            Found = {Prefix}_Literal(Value, Expected, Missing, Encoded)",
              "            if Found is not Missing:", "                return Found",
              "    if Encoded:", "        if Expected[0] != 'value':", "            return Missing", "        Expected = Expected[1]",
              "    if Expected is None or type(Expected) is bool or Expected is Ellipsis or type(Expected) is int and -5 <= Expected <= 256:",
              "        return Expected", "    return Missing",
              f"cdef object {Prefix}_Canonical(object Value, tuple Pool):",
              "    cdef object Missing = object()", f"    cdef object Found = {Prefix}_Literal(Pool, Value, Missing, False)",
              "    cdef list Values = []", "    cdef object Item",
              "    if Found is not Missing:", "        return Found", "    if type(Value) is tuple:",
              "        for Item in Value:", f"            Values.append({Prefix}_Canonical(Item, Pool))", "        return tuple(Values)",
              "    return Value", f"cdef object _Pyceler_Math_Baseline_{Line}(object Baseline, tuple Pool):",
              "    cdef list Values = []", "    cdef object Value", "    for Value in Baseline.__code__.co_consts:",
              f"        Values.append({Prefix}_Canonical(Value, Pool))", "    Baseline.__code__ = Baseline.__code__.replace(co_consts=tuple(Values))", "    return Baseline",
              f"cdef object _Pyceler_Math_Map_{Line}({', '.join('object ' + Name for Name in Parameters)}, object Baseline, bint Allow_Threads, int Thread_Count):",
              "    import sys as _Pyceler_Math_Sys", "    import builtins as _Pyceler_Math_B",
              "    cdef dict _Pyceler_Math_Globals = Baseline.__globals__", "    cdef dict _Pyceler_Math_Builtins = Baseline.__builtins__",
              "    cdef object _Pyceler_Math_Numpy = _Pyceler_Math_Sys.modules.get('numpy')",
              "    cdef object _Pyceler_Math_Missing = _Pyceler_Math_B.object()", "    cdef unsigned int _Pyceler_Math_Ticks = 0"]
    if Fast:
        Source.extend(["    cdef object _Pyceler_Math_Iterator", "    cdef Py_ssize_t _Pyceler_Math_Done"])
    for Name in Plan["Indices"] + Plan["Locals"]:
        Source.append("    cdef object " + Rewrite._Locals[Name])
    for Index, Value in enumerate(Rewrite._Constants):
        Source.append(f"    cdef object _Pyceler_Math_Literal_{Line}_{Index}")
    Arguments = ", ".join(Parameters)
    Source.extend(["    if _Pyceler_Math_Numpy is None:", f"        return Baseline({Arguments})"])
    for Name in sorted(Plan["Arrays"]):
        Slot = Rewrite._Locals[Name]
        Source.extend([f"    if _Pyceler_Math_B.type({Slot}) is not _Pyceler_Math_Numpy.ndarray or {Slot}.dtype.kind not in ('b', 'i', 'u', 'f', 'c') or {Slot}.dtype.metadata is not None:", f"        return Baseline({Arguments})"])
    Source.extend([f"    if {Rewrite._Locals[Plan['Output']]}.ndim != {len(Plan['Indices'])}:", f"        return Baseline({Arguments})"])
    for Name in sorted(Plan["Scalars"]):
        Source.extend([f"    if _Pyceler_Math_B.type({Rewrite._Locals[Name]}) not in (_Pyceler_Math_B.int, _Pyceler_Math_B.float, _Pyceler_Math_B.complex, _Pyceler_Math_B.bool):", f"        return Baseline({Arguments})"])
    for Index, Value in enumerate(Rewrite._Constants):
        Source.extend([f"    _Pyceler_Math_Literal_{Line}_{Index} = {Prefix}_Literal(Baseline.__code__.co_consts, {_Math_Literal_Source(Value)}, _Pyceler_Math_Missing, True)",
                       f"    if _Pyceler_Math_Literal_{Line}_{Index} is _Pyceler_Math_Missing:", f"        return Baseline({Arguments})"])
    if Fast:
        Source.extend(["    _Pyceler_Math_Iterator = " + Iterator,
                       f"    _Pyceler_Math_Done = _Pyceler_Fast_Math_{Line}(({Arguments}{',' if len(Parameters) == 1 else ''}), Baseline, _Pyceler_Math_Iterator, Allow_Threads, Thread_Count)",
                       "    if _Pyceler_Math_Done:", "        if _Pyceler_Math_Done == _Pyceler_Math_B.len(_Pyceler_Math_Iterator):",
                       "            return " + Rewrite._Locals[Plan["Output"]], "        _Pyceler_Math_Iterator = _Pyceler_Math_Iterator[_Pyceler_Math_Done:]"])
    Source.append("    _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)")
    Source.extend("    " + Value for Statement in Body for Value in Statement.splitlines())
    return (_Fast_Math_Kernel(Fast, Line, Parallel) if Fast else "") + "\n".join(Source) + "\n"
