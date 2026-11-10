class _Unsupported_Map(Exception):
    pass

cdef object _Axis_Source(object Bound, int Axis, tuple Indices, dict Aliases):
    if isinstance(Bound, ast.Name) and Bound.id in Aliases:
        Source, Dimension = Aliases[Bound.id]
        return Source if Dimension == Axis else None
    if isinstance(Bound, ast.Subscript) and isinstance(Bound.value, ast.Attribute):
        Shape = Bound.value
        if Shape.attr == "shape" and isinstance(Shape.value, ast.Name) and _Integer(Bound.slice, Axis):
            return Shape.value.id
    if isinstance(Bound, ast.Call) and _Name(Bound.func, "len") and not Bound.keywords and len(Bound.args) == 1:
        Value = Bound.args[0]
        if Axis == 0 and isinstance(Value, ast.Name):
            return Value.id
        if Axis:
            return _Map_Cell(Value, Indices)
    return None

cdef dict _Shape_Locals(list Prelude, tuple Names, int Dimensions):
    Aliases = {}
    for Statement in Prelude:
        if not isinstance(Statement, ast.Assign) or len(Statement.targets) != 1:
            raise _Unsupported_Map()
        Target = Statement.targets[0]
        Value = Statement.value
        if isinstance(Target, (ast.Tuple, ast.List)) and len(Target.elts) == Dimensions and isinstance(Value, ast.Attribute) and Value.attr == "shape":
            Source = Value.value
            Bindings = list(zip(Target.elts, range(Dimensions)))
        elif isinstance(Target, ast.Name) and isinstance(Value, ast.Subscript) and isinstance(Value.value, ast.Attribute) and Value.value.attr == "shape":
            if not isinstance(Value.slice, ast.Constant) or type(Value.slice.value) is not int or not 0 <= Value.slice.value < Dimensions:
                raise _Unsupported_Map()
            Source = Value.value.value
            Bindings = [(Target, Value.slice.value)]
        elif isinstance(Target, ast.Name) and isinstance(Value, ast.Call) and _Name(Value.func, "len") and len(Value.args) == 1 and not Value.keywords:
            Source = Value.args[0]
            Bindings = [(Target, 0)]
        else:
            raise _Unsupported_Map()
        if not isinstance(Source, ast.Name) or Source.id not in Names:
            raise _Unsupported_Map()
        for Variable, Axis in Bindings:
            if not isinstance(Variable, ast.Name) or Variable.id in Names or Variable.id in Aliases or Variable.id in ("len", "range"):
                raise _Unsupported_Map()
            Aliases[Variable.id] = (Source.id, Axis)
    return Aliases

cdef tuple _Counted_Level(list Statements):
    Loop = Statements[-1]
    if Loop.orelse:
        raise _Unsupported_Map()
    if isinstance(Loop, ast.For):
        Call = Loop.iter
        if not isinstance(Loop.target, ast.Name) or not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords:
            raise _Unsupported_Map()
        if len(Call.args) == 1:
            Bound = Call.args[0]
        elif len(Call.args) in (2, 3) and _Integer(Call.args[0], 0) and (len(Call.args) == 2 or _Integer(Call.args[2], 1)):
            Bound = Call.args[1]
        else:
            raise _Unsupported_Map()
        return Statements[:-1], Loop.target.id, Bound, Loop.body
    Test = Loop.test
    if len(Statements) < 2 or not isinstance(Test, ast.Compare) or not isinstance(Test.left, ast.Name) or len(Test.ops) != 1 or not isinstance(Test.ops[0], ast.Lt):
        raise _Unsupported_Map("A counted array while loop requires a zero-based index and a strict upper bound.")
    Index = Test.left.id
    Init = Statements[-2]
    if not isinstance(Init, ast.Assign) or len(Init.targets) != 1 or not _Name(Init.targets[0], Index) or not _Integer(Init.value, 0):
        raise _Unsupported_Map("The while index must start at zero on every entry.")
    Step = Loop.body[-1]
    if isinstance(Step, ast.AugAssign) and _Name(Step.target, Index) and isinstance(Step.op, ast.Add) and _Integer(Step.value, 1):
        return Statements[:-2], Index, Test.comparators[0], Loop.body[:-1]
    if isinstance(Step, ast.Assign) and len(Step.targets) == 1 and _Name(Step.targets[0], Index) and isinstance(Step.value, ast.BinOp):
        if _Name(Step.value.left, Index) and isinstance(Step.value.op, ast.Add) and _Integer(Step.value.right, 1):
            return Statements[:-2], Index, Test.comparators[0], Loop.body[:-1]
    raise _Unsupported_Map("The while index must advance by exactly one after the element operation.")

cdef object _Map_Cell(object Node, tuple Indices):
    if not isinstance(Node, ast.Subscript) or not isinstance(Node.value, ast.Name):
        return None
    Positions = Node.slice.elts if isinstance(Node.slice, ast.Tuple) else [Node.slice]
    if len(Positions) == len(Indices) and all(_Name(Position, Index) for Position, Index in zip(Positions, Indices)):
        return Node.value.id
    return None

cdef tuple _Map_Expression(object Node, dict Plan):
    Names = Plan["Names"]
    Cell = _Map_Cell(Node, Plan["Indices"])
    if Cell in Names:
        Plan["Arrays"].add(Cell)
        Slot = Names.index(Cell)
        Plan["Reads"].add(Slot)
        return f"V{Slot}[Index]", ("array", Slot)
    if isinstance(Node, ast.Name) and Node.id in Names:
        Plan["Scalars"].add(Node.id)
        Slot = Names.index(Node.id)
        return f"(<_Pyceler_Value>V{Slot})", ("scalar", Slot)
    Literal = Node
    Negative = isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.USub)
    if Negative:
        Literal = Node.operand
    if isinstance(Literal, ast.Constant) and type(Literal.value) is int and abs(Literal.value) <= 16777216:
        Value = -Literal.value if Negative else Literal.value
        Plan["Integer_Literals"].add(Value)
        return f"(<_Pyceler_Value>({Value}))", ("literal", Value)
    if isinstance(Literal, ast.Constant) and type(Literal.value) is float and math.isfinite(Literal.value):
        Value = -Literal.value if Negative else Literal.value
        Plan["Float_Literals"].append(Value)
        return f"(<_Pyceler_Value>({Value!r}))", ("literal", Value)
    if isinstance(Node, ast.BinOp) and isinstance(Node.op, (ast.Add, ast.Sub, ast.Mult)):
        Left, Left_Range = _Map_Expression(Node.left, Plan)
        Right, Right_Range = _Map_Expression(Node.right, Plan)
        Operator = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}[type(Node.op)]
        Bound = (Operator, Left_Range, Right_Range)
        Plan["Arithmetic"].append(Bound)
        return f"({Left} {Operator} {Right})", Bound
    if isinstance(Node, ast.Subscript):
        raise _Unsupported_Map(f"Indexed read {ast.unparse(Node)} is outside the current output position; bounds and independence require a separate proof.")
    raise _Unsupported_Map("The expression uses an operation outside the supported element-wise grammar.")

cdef str _Map_Condition(object Node, dict Plan):
    Operators = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
    if not isinstance(Node, ast.Compare) or len(Node.ops) != 1 or type(Node.ops[0]) not in Operators:
        raise _Unsupported_Map()
    Plan["Comparison"] = True
    Left = _Map_Expression(Node.left, Plan)[0]
    Right = _Map_Expression(Node.comparators[0], Plan)[0]
    return f"{Left} {Operators[type(Node.ops[0])]} {Right}"

cdef str _Map_Assignment(object Node, dict Plan):
    if isinstance(Node, ast.Assign) and len(Node.targets) == 1:
        Target = Node.targets[0]
        Value = Node.value
    elif isinstance(Node, ast.AugAssign) and isinstance(Node.op, (ast.Add, ast.Sub, ast.Mult)):
        Target = Node.target
        Value = ast.BinOp(left=Target, op=Node.op, right=Node.value)
    else:
        raise _Unsupported_Map()
    if _Map_Cell(Target, Plan["Indices"]) != Plan["Output"]:
        raise _Unsupported_Map(f"Write to {ast.unparse(Target)} does not match the returned array at the current indices; iteration independence is unproven.")
    if isinstance(Value, ast.IfExp):
        Test = _Map_Condition(Value.test, Plan)
        Yes = _Map_Expression(Value.body, Plan)[0]
        No = _Map_Expression(Value.orelse, Plan)[0]
        Result = f"({Yes} if {Test} else {No})"
    else:
        Result = _Map_Expression(Value, Plan)[0]
    return f"V{Plan['Names'].index(Plan['Output'])}[Index] = {Result}"

cdef object _Map_Plan(object Function, object Outer):
    if not isinstance(Function, ast.FunctionDef) or Function.decorator_list or getattr(Function, "type_params", ()):
        return None
    Docstring = ast.get_docstring(Function, clean=False) is not None
    Body = Function.body[1:] if Docstring else Function.body
    if len(Body) < 2 or Body[-2] is not Outer or not isinstance(Body[-1], ast.Return) or not isinstance(Body[-1].value, ast.Name):
        return None
    Args = Function.args
    Names = tuple(Arg.arg for Arg in Args.posonlyargs + Args.args)
    Output = Body[-1].value.id
    if Output not in Names or Args.vararg or Args.kwarg or Args.kwonlyargs:
        return None
    if Body[0].lineno == Function.lineno or (Docstring and Body[0].lineno == Function.body[0].end_lineno):
        return None
    Statements = Body[:-1]
    Loops, Bounds, Counters = [], [], []
    try:
        while Statements and isinstance(Statements[-1], (ast.For, ast.While)):
            Loops.append(Statements[-1])
            Prelude, Counter, Bound, Statements = _Counted_Level(Statements)
            if len(Loops) == 1:
                Shape_Statements = Prelude
            elif Prelude:
                return None
            Counters.append(Counter)
            Bounds.append(Bound)
        if not Loops or len(Statements) != 1:
            return None
        Aliases = _Shape_Locals(Shape_Statements, Names, len(Loops))
    except _Unsupported_Map as Error:
        return str(Error) or None
    Indices = tuple(Counters)
    if len(set(Indices)) != len(Indices) or set(Indices).intersection(Names + tuple(Aliases)) or {"range", "len"}.intersection(Names + Indices):
        return None
    Arrays = {Output}
    Arrays.update(Source for Source, Dimension in Aliases.values())
    for Axis, Bound in enumerate(Bounds):
        Source = _Axis_Source(Bound, Axis, Indices[:Axis], Aliases)
        if Source not in Names:
            return None
        Arrays.add(Source)
    Statement = Statements[0]
    Plan = dict(Names=Names, Indices=Indices, Output=Output, Arrays=Arrays, Scalars=set(), Reads=set(), Comparison=False,
                Arithmetic=[], Float_Literals=[], Integer_Literals=set(), Start=Body[0].lineno, Loops=Loops, Element=Statement)
    try:
        if isinstance(Statement, ast.If):
            if len(Statement.body) != 1 or len(Statement.orelse) > 1:
                return None
            Lines = ["if " + _Map_Condition(Statement.test, Plan) + ":", "    " + _Map_Assignment(Statement.body[0], Plan)]
            if Statement.orelse:
                Lines.extend(["else:", "    " + _Map_Assignment(Statement.orelse[0], Plan)])
        else:
            Lines = [_Map_Assignment(Statement, Plan)]
    except _Unsupported_Map as Error:
        return str(Error) or None
    if Arrays & Plan["Scalars"] or Arrays | Plan["Scalars"] != set(Names):
        return None
    Plan["Lines"] = Lines
    if len(Indices) == 1 and len(Names) == 2 and isinstance(Statement, ast.Assign) and isinstance(Statement.value, ast.Subscript) and isinstance(Statement.value.value, ast.Name):
        Source = Statement.value.value.id
        if (Source != Output and Source in Names and _Element(Statement.value, Source, Indices[0]) and not Aliases
                and isinstance(Loops[0], ast.For) and _Bounds(Loops[0].iter) == (Output, 0)):
            Plan["Byte_Copy"] = (Names.index(Source), Names.index(Output))
    return Plan
