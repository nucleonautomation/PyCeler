class _Unsupported_Structure(Exception):
    pass

cdef int _Structural_Node(dict Plan, tuple Recipe, list Actions):
    Number = len(Plan["Nodes"])
    Plan["Nodes"].append(Recipe)
    Actions.append(("value", Number))
    return Number

cdef int _Structural_Expression(object Node, dict Plan, dict Locals, tuple Indices, list Actions):
    if isinstance(Node, ast.Name) and Node.id in Locals:
        return Locals[Node.id]
    if isinstance(Node, ast.Name) and Node.id in Plan["Names"]:
        Plan["Scalars"].add(Node.id)
        return _Structural_Node(Plan, ("scalar", Plan["Names"].index(Node.id)), Actions)
    if isinstance(Node, ast.Constant) and type(Node.value) is int and abs(Node.value) <= 16777216:
        return _Structural_Node(Plan, ("literal", Node.value), Actions)
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.USub) and isinstance(Node.operand, ast.Constant) and type(Node.operand.value) is int:
        if abs(Node.operand.value) <= 16777216:
            return _Structural_Node(Plan, ("literal", -Node.operand.value), Actions)
    Cell = _Map_Cell(Node, Indices)
    if Cell in Plan["All_Names"]:
        Slot = Plan["All_Names"].index(Cell)
        Plan["Arrays"].add(Cell)
        Plan["Reads"].add(Slot)
        Version = Plan["Versions"].get(Slot, 0)
        if Cell == Plan.get("Temporary") and Version == 0:
            raise _Unsupported_Structure("Temporary storage is read before a complete write.")
        return _Structural_Node(Plan, ("array", Slot, Version), Actions)
    if isinstance(Node, ast.BinOp) and isinstance(Node.op, (ast.Add, ast.Sub, ast.Mult)):
        Left = _Structural_Expression(Node.left, Plan, Locals, Indices, Actions)
        Right = _Structural_Expression(Node.right, Plan, Locals, Indices, Actions)
        Plan["Arithmetic"] = True
        return _Structural_Node(Plan, ({ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}[type(Node.op)], Left, Right), Actions)
    if isinstance(Node, ast.Call) and _Name(Node.func, "abs") and len(Node.args) == 1 and not Node.keywords and "abs" not in Plan["Names"]:
        Value = _Structural_Expression(Node.args[0], Plan, Locals, Indices, Actions)
        Plan["Arithmetic"] = True
        Plan["Abs"] = True
        return _Structural_Node(Plan, ("abs", Value), Actions)
    raise _Unsupported_Structure("Structural specialization requires exact indexed numeric expressions using +, - and *.")

cdef tuple _Structural_Nest(object Loop):
    Levels = []
    Body = [Loop]
    while len(Body) == 1 and isinstance(Body[0], ast.For):
        Node = Body[0]
        if Node.orelse or not isinstance(Node.target, ast.Name) or not isinstance(Node.iter, ast.Call) or not _Name(Node.iter.func, "range") or Node.iter.keywords:
            raise _Unsupported_Structure("Expected a rectangular built-in range traversal.")
        Args = Node.iter.args
        if len(Args) == 1:
            Bound = Args[0]
        elif len(Args) in (2, 3) and _Integer(Args[0], 0) and (len(Args) == 2 or _Integer(Args[2], 1)):
            Bound = Args[1]
        else:
            raise _Unsupported_Structure("Structural loop bounds require zero start and unit step.")
        Levels.append((Node, Node.target.id, Bound))
        Body = Node.body
    if not 1 <= len(Levels) <= 2 or not Body:
        raise _Unsupported_Structure("Structural maps currently require one or two rectangular dimensions.")
    return Levels, Body

cdef object _Structural_Plan(object Function, bint Elide_Temporaries):
    if not isinstance(Function, ast.FunctionDef) or Function.decorator_list or getattr(Function, "type_params", ()):
        return None
    Args = Function.args
    if Args.kwonlyargs or Args.vararg or Args.kwarg:
        return None
    Names = tuple(Arg.arg for Arg in Args.posonlyargs + Args.args)
    Body = Function.body[1:] if ast.get_docstring(Function, clean=False) is not None else Function.body
    if not Body:
        return None
    Returns_None = not isinstance(Body[-1], ast.Return) or Body[-1].value is None or isinstance(Body[-1].value, ast.Constant) and Body[-1].value.value is None
    if Returns_None:
        Statements = Body[:-1] if isinstance(Body[-1], ast.Return) else Body
        Output = next((Part.value.id for Statement in Statements for Part in ast.walk(Statement)
                       if isinstance(Part, ast.Subscript) and isinstance(Part.ctx, ast.Store) and isinstance(Part.value, ast.Name) and Part.value.id in Names), None)
        if Output is None:
            return None
        Body = [*Statements, ast.Return(value=ast.Name(id=Output, ctx=ast.Load()))]
    if len(Body) < 2 or not isinstance(Body[-1], ast.Return) or not isinstance(Body[-1].value, ast.Name) or Body[-1].value.id not in Names:
        return None
    Output = Body[-1].value.id
    if Body[0].lineno == Function.lineno or (ast.get_docstring(Function, clean=False) is not None and Body[0].lineno == Function.body[0].end_lineno):
        return None
    if set(Names) & {"range", "len"} or any(isinstance(Node, (ast.Try, ast.With, ast.Lambda, ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom, ast.Await)) for Node in ast.walk(Function)):
        return None
    Shape_Locals, Temporary, Allocation, Loops = {}, None, None, []
    Prelude = []
    for Statement in Body[:-1]:
        if isinstance(Statement, ast.For):
            Loops.append(Statement)
        elif Loops:
            return None
        elif isinstance(Statement, ast.Assign) and len(Statement.targets) == 1:
            Target, Value = Statement.targets[0], Statement.value
            if isinstance(Target, ast.Name) and isinstance(Value, ast.Call) and isinstance(Value.func, ast.Attribute) and Value.func.attr == "empty_like":
                if not Elide_Temporaries or Temporary is not None or Target.id in (*Names, "range", "len", "abs") or not isinstance(Value.func.value, ast.Name) or len(Value.args) != 1 or Value.keywords or not isinstance(Value.args[0], ast.Name) or Value.args[0].id not in Names:
                    return None
                Temporary, Allocation = Target.id, (Value.func.value.id, Names.index(Value.args[0].id))
            else:
                Prelude.append(Statement)
        else:
            return None
    if not Loops:
        return None
    Plan = dict(Kind="structural", Names=Names, All_Names=Names + ((Temporary,) if Temporary else ()), Output=Output,
                Arrays={Output}, Scalars=set(), Reads=set(), Outputs=set(), Versions={}, Nodes=[], Blocks=[], Loops=[], Arithmetic=False,
                Start=Body[0].lineno, End=Body[-2].end_lineno, Returns_None=Returns_None, Transformations=[], Dimension_Args={},
                Temporary=Temporary, Allocation=Allocation, Local_Count=0, Abs=False)
    Dimensions = None
    try:
        for Outer in Loops:
            Levels, Statements = _Structural_Nest(Outer)
            if Dimensions is None:
                Dimensions = len(Levels)
                Shape_Locals = _Shape_Locals(Prelude, Names, Dimensions)
                if "abs" in Shape_Locals or Temporary in Shape_Locals:
                    return None
                Plan["Arrays"].update(Source for Source, Axis in Shape_Locals.values())
            elif Dimensions != len(Levels):
                return None
            Counters = tuple(Name for Node, Name, Bound in Levels)
            if len(set(Counters)) != Dimensions or set(Counters) & (set(Names) | set(Shape_Locals) | {Temporary, "len", "range", "abs"}):
                return None
            Stores = [Part for Statement in Statements for Part in ast.walk(Statement) if isinstance(Part, ast.Subscript) and isinstance(Part.ctx, ast.Store)]
            if not Stores:
                return None
            First = Stores[0].slice
            Coordinates = First.elts if isinstance(First, ast.Tuple) else [First]
            if len(Coordinates) != Dimensions or any(not isinstance(Part, ast.Name) for Part in Coordinates):
                return None
            Indices = tuple(Part.id for Part in Coordinates)
            if set(Indices) != set(Counters):
                return None
            Axes = tuple(Indices.index(Name) for Name in Counters)
            for Level_Index, (Node, Counter, Bound) in enumerate(Levels):
                Axis = Indices.index(Counter)
                Prior = set(Counters[:Level_Index])
                if any(isinstance(Part, ast.Name) and Part.id in Counters and Part.id not in Prior for Part in ast.walk(Bound)):
                    return None
                Source = _Axis_Source(Bound, Axis, Indices[:Axis], Shape_Locals)
                if Source in Names:
                    Plan["Arrays"].add(Source)
                elif isinstance(Bound, ast.Name) and Bound.id in Names and Bound.id not in Plan["Arrays"]:
                    if Bound.id in Plan["Dimension_Args"] and Plan["Dimension_Args"][Bound.id] != Axis:
                        return None
                    Plan["Dimension_Args"][Bound.id] = Axis
                else:
                    return None
            Actions, Locals = [], {}
            for Statement in Statements:
                if not isinstance(Statement, ast.Assign) or len(Statement.targets) != 1:
                    return None
                Target = Statement.targets[0]
                Value = _Structural_Expression(Statement.value, Plan, Locals, Indices, Actions)
                if isinstance(Target, ast.Name):
                    if Target.id in set(Names) | set(Counters) | set(Shape_Locals) | {Temporary, "range", "len", "abs"}:
                        return None
                    Locals[Target.id] = Value
                    Plan["Local_Count"] += 1
                else:
                    Cell = _Map_Cell(Target, Indices)
                    if Cell not in Plan["All_Names"]:
                        return None
                    Slot = Plan["All_Names"].index(Cell)
                    Plan["Arrays"].add(Cell)
                    Plan["Outputs"].add(Cell)
                    Version = Plan["Versions"].get(Slot, 0) + 1
                    Plan["Versions"][Slot] = Version
                    Actions.append(("write", Slot, Value, Version))
            Plan["Blocks"].append((Axes, Actions))
            Plan["Loops"].extend(Node for Node, Counter, Bound in Levels)
        if Plan["Arrays"] & Plan["Scalars"] or (Plan["Arrays"] | Plan["Scalars"] | set(Plan["Dimension_Args"])) != set(Plan["All_Names"]):
            return None
        if Output not in Plan["Outputs"] or (Temporary and Temporary not in Plan["Outputs"]):
            return None
        if Temporary and Allocation[0] in Names:
            return None
        if Temporary and any(isinstance(Node, ast.Name) and Node.id == Allocation[0] and isinstance(Node.ctx, ast.Store) for Node in ast.walk(Function)):
            return None
        if len(Plan["Nodes"]) > 128 or len(Plan["Blocks"]) > 8:
            return None
        Plan["Indices"] = tuple(range(Dimensions))
        Plan["Dimensions"] = Dimensions
        Plan["Kernel_Names"] = Names
        Plan["Outputs"] = tuple(sorted(Plan["Outputs"]))
        if len(Loops) > 1:
            Plan["Transformations"].append("loop_fusion")
        if any(Axes != tuple(range(Dimensions)) for Axes, Actions in Plan["Blocks"]):
            Plan["Transformations"].append("loop_interchange")
        if Temporary:
            Plan["Transformations"].append("temporary_elimination")
        Seen, Invariant, Repeated = {}, set(), False
        for Number, Recipe in enumerate(Plan["Nodes"]):
            Key = Recipe if Recipe[0] not in ("+", "-", "*") else (Recipe[0], Seen.get(Recipe[1], Recipe[1]), Seen.get(Recipe[2], Recipe[2]))
            if Recipe[0] == "abs":
                Key = ("abs", Seen.get(Recipe[1], Recipe[1]))
            if Key in Seen:
                Repeated = True
                Seen[Number] = Seen[Key]
            else:
                Seen[Key] = Number
                Seen[Number] = Number
            if Recipe[0] in ("scalar", "literal") or Recipe[0] in ("+", "-", "*") and Recipe[1] in Invariant and Recipe[2] in Invariant or Recipe[0] == "abs" and Recipe[1] in Invariant:
                Invariant.add(Number)
        if Repeated:
            Plan["Transformations"].append("common_subexpressions")
        if any(Plan["Nodes"][Number][0] in ("+", "-", "*", "abs") for Number in Invariant):
            Plan["Transformations"].append("loop_invariants")
        Plan["Invariant"] = tuple(sorted(Invariant))
        if not Plan["Transformations"] and not Plan["Local_Count"]:
            return None
        return Plan
    except (_Unsupported_Structure, _Unsupported_Map):
        return None

cdef void _Structural_Plans(object Tree, list Findings, dict Edits, bint Parallel, bint Elide_Temporaries) except *:
    Positions = {Finding.Line: Index for Index, Finding in enumerate(Findings)}
    Function_Edits = {}
    for Line, Edit in Edits.items():
        Function_Edits.setdefault(Edit[2], []).append(Line)
    for Function in Tree.body:
        Plan = _Structural_Plan(Function, Elide_Temporaries)
        if Plan is None:
            continue
        Lines = {Node.lineno for Node in Plan["Loops"]}
        for Line in Function_Edits.get(Function, ()):
            del Edits[Line]
        Outer = Plan["Loops"][0]
        Span = copy.copy(Outer)
        Span.end_lineno = Plan["End"]
        Edits[Outer.lineno] = (Plan["Names"], Span, Function, Plan)
        for Line in Lines:
            Index = Positions[Line]
            Finding = Findings[Index]
            Findings[Index] = replace(Finding, Classification="Structural_Numeric_Map",
                Change="Guarded structural " + ("serial/OpenMP" if Parallel else "serial") + " candidates",
                Reason="Shared numeric plan: " + ", ".join(Plan["Transformations"] or ["typed_locals"]) +
                       ". Exact shape, disjoint storage and intermediate integer ranges are checked before writes.")
