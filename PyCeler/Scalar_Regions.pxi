cdef object _Scalar_Progress(object Node, str Index):
    if not isinstance(Node, ast.If) or Node.orelse:
        return None
    Test = Node.test.values[0] if isinstance(Node.test, ast.BoolOp) and isinstance(Node.test.op, ast.And) else Node.test
    if not isinstance(Test, ast.Compare) or len(Test.ops) != 1 or not isinstance(Test.ops[0], ast.Eq) or not _Integer(Test.comparators[0], 0):
        return None
    Left = Test.left
    if not isinstance(Left, ast.BinOp) or not isinstance(Left.op, ast.Mod) or not _Name(Left.left, Index):
        return None
    if not isinstance(Left.right, ast.Constant) or type(Left.right.value) is not int or Left.right.value <= 0:
        return None
    return Left.right.value

cdef void _Scalar_Region_Inputs(list Statements, set Defined, list Inputs) except *:
    for Node in Statements:
        Values = [Node.value] if isinstance(Node, (ast.Assign, ast.AugAssign)) else [Node.test] if isinstance(Node, ast.If) else [Node]
        if isinstance(Node, ast.AugAssign) and isinstance(Node.target, ast.Name) and Node.target.id not in Defined and Node.target.id not in Inputs:
            Inputs.append(Node.target.id)
        for Value in Values:
            for Part in ast.walk(Value):
                if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Load) and Part.id not in Defined and Part.id not in Inputs:
                    Inputs.append(Part.id)
        if isinstance(Node, ast.Assign):
            for Target in Node.targets:
                Defined.update(_Assigned(Target))
        elif isinstance(Node, ast.AugAssign):
            Defined.update(_Assigned(Node.target))
        elif isinstance(Node, ast.If):
            Yes, No = Defined.copy(), Defined.copy()
            _Scalar_Region_Inputs(Node.body, Yes, Inputs)
            _Scalar_Region_Inputs(Node.orelse, No, Inputs)
            Defined.update(Yes & No)

cdef object _Scalar_Region_Plan(object Function, object Loop, set Available, str Scope):
    if not isinstance(Loop, ast.For) or not isinstance(Loop.target, ast.Name) or Loop.orelse:
        return None
    Call = Loop.iter
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or not 1 <= len(Call.args) <= 3:
        return None
    Step = 1
    if len(Call.args) == 3:
        Literal = Call.args[2]
        Negative = isinstance(Literal, ast.UnaryOp) and isinstance(Literal.op, ast.USub)
        Literal = Literal.operand if Negative else Literal
        if not isinstance(Literal, ast.Constant) or type(Literal.value) is not int or not 1 <= Literal.value <= 2**31 - 1:
            return None
        Step = -Literal.value if Negative else Literal.value
    Index = Loop.target.id
    if Index == "range":
        return None
    Statements = list(Loop.body)
    Period = _Scalar_Progress(Statements[-1], Index)
    Reporting = Statements.pop() if Period is not None else None
    if not Statements:
        return None
    Parts = [Part for Statement in Statements for Part in ast.walk(Statement)]
    if any(isinstance(Part, (ast.For, ast.While, ast.Call, ast.Return, ast.Break, ast.Continue, ast.Raise, ast.Try, ast.With,
                              ast.Yield, ast.YieldFrom, ast.NamedExpr, ast.Subscript, ast.Attribute)) for Part in Parts):
        return None
    if any(isinstance(Part, ast.Assign) and not _Scalar_Fresh(Part.value) or isinstance(Part, ast.AugAssign) and isinstance(Part.op, ast.Mod) for Part in Parts):
        return None
    if any(isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Store) and Part.id == Index for Part in Parts):
        return None
    Inputs = []
    Defined = {Index}
    _Scalar_Region_Inputs(Statements, Defined, Inputs)
    if not set(Inputs) <= Available or "range" in Inputs:
        return None
    Outputs = tuple(dict.fromkeys([Part.id for Part in Parts if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Store)] + [Index]))
    if not set(Outputs) <= Defined:
        return None
    Written = {Statement.target.id for Statement in Statements if isinstance(Statement, ast.AugAssign) and isinstance(Statement.target, ast.Name)}
    Written.update(Statement.targets[0].id for Statement in Statements if isinstance(Statement, ast.Assign) and len(Statement.targets) == 1 and
                   isinstance(Statement.targets[0], ast.Name) and isinstance(Statement.value, ast.BinOp))
    if set(Outputs) - {Index} - Written:
        return None
    Used = set(Inputs) | set(Outputs)
    Stop, Begin = "_Pyceler_Stop", "_Pyceler_Begin"
    while Stop in Used:
        Stop += "_X"
    while Begin in Used:
        Begin += "_X"
    Names = (Stop, Begin, *Inputs)
    Plan = dict(Kind="scalar_region", Names=Names, Inputs=tuple(Inputs), Outputs=Outputs, Index=Index, Slots={}, Temporaries=[],
                Lines=[], Loops=[Loop], Start=Loop.lineno, Region=True, Scope=Scope, Period=Period, Step=Step, Reporting=Reporting,
                Statements=Statements, Size_Arguments=(0,), Transformations=("Scalar region extraction", "Ordered progress boundaries") if Reporting is not None else ("Scalar region extraction",))
    for Name in (*Names, *Outputs):
        _Scalar_Slot(Name, Plan)
    Bound = set(Inputs) | {Index}
    try:
        _Scalar_Block(Statements, Bound, Plan, "                ", True)
    except _Unsupported_Scalar:
        if len(Statements) != 1 or not isinstance(Statements[0], ast.AugAssign) or not isinstance(Statements[0].op, ast.Add):
            return None
        Statement = Statements[0]
        if not isinstance(Statement.target, ast.Name) or Statement.target.id not in Inputs:
            return None
        Total = Statement.target.id
        if any(_Name(Part, Total) for Part in ast.walk(Statement.value)):
            return None
        Plan["Floating"] = {Total}
        try:
            Value, Type = _Scalar_Division_Expr(Statement.value, set(Inputs) | {Index}, Plan)
        except _Unsupported_Scalar:
            return None
        if Type != "float":
            return None
        Target = _Scalar_Slot(Total, Plan)
        Plan["Lines"] = [f"                {Target} = _Pyceler_Float_Add({Target}, {Value})"]
    Definition = ast.parse(f"def _Pyceler_Probe({', '.join(Names)}):\n    pass").body[0]
    Candidate = copy.deepcopy(Loop)
    Candidate.iter = ast.parse(f"range({Begin}, {Stop}, {Step})", mode="eval").body
    Candidate.body = copy.deepcopy(Statements)
    Definition.body = [ast.parse(f"{Index} = {Begin}").body[0], Candidate, ast.parse("return (" + ", ".join(Outputs) + ",)").body[0]]
    Plan["Probe"] = ast.fix_missing_locations(Definition)
    return Plan

cdef void _Scalar_Region_Block(object Function, list Statements, set Available, str Scope, dict Edits, dict Updates, set Shared) except *:
    Bound = Available.copy()
    for Node in Statements:
        if isinstance(Node, ast.For) and Node.lineno not in Edits and Node.lineno not in Shared and Node.end_lineno not in Shared:
            Plan = _Scalar_Region_Plan(Function, Node, Bound, Scope)
            if Plan is not None:
                Edits[Node.lineno] = (Plan["Names"], Node, Function, Plan)
                Updates[Node.lineno] = Plan
        if isinstance(Node, ast.Assign):
            for Target in Node.targets:
                Bound.update(_Assigned(Target))
        elif isinstance(Node, ast.AnnAssign) and Node.value is not None:
            Bound.update(_Assigned(Node.target))
        elif isinstance(Node, ast.If):
            _Scalar_Region_Block(Function, Node.body, Bound, Scope, Edits, Updates, Shared)
            _Scalar_Region_Block(Function, Node.orelse, Bound, Scope, Edits, Updates, Shared)

cdef void _Find_Scalar_Regions(object Tree, list Findings, dict Edits) except *:
    Existing = {Edit[2] for Edit in Edits.values() if Edit[3] is None or not Edit[3].get("Region", False)}
    Updates = {}
    Functions = []
    for Top in Tree.body:
        for Function in (Top.body if isinstance(Top, ast.ClassDef) else [Top]):
            if isinstance(Function, ast.FunctionDef) and Function not in Existing and not Function.decorator_list and not getattr(Function, "type_params", ()):
                Args = Function.args
                Names = {Arg.arg for Arg in Args.posonlyargs + Args.args + Args.kwonlyargs}
                Functions.append((Function, f"{Top.name}.{Function.name}" if isinstance(Top, ast.ClassDef) else Function.name, Names))
    for Function, Scope, Available in Functions:
        Parts = _Rank_Parts(Function)
        if isinstance(Function, ast.FunctionDef) and ("range" in Available or _Rank_Binds_Range(Function)):
            continue
        if any(isinstance(Part, (ast.Global, ast.Nonlocal, ast.Delete, ast.Lambda, ast.Yield, ast.YieldFrom, ast.Try)) or
               isinstance(Part, ast.Name) and Part.id in {"globals", "locals", "vars", "eval", "exec", "_getframe", "currentframe"} for Part in Parts):
            continue
        if isinstance(Function, ast.FunctionDef) and any(isinstance(Part, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and Part is not Function for Part in ast.walk(Function)):
            continue
        Counts = {}
        for Part in Parts:
            if isinstance(Part, ast.stmt):
                Counts[Part.lineno] = Counts.get(Part.lineno, 0) + 1
        Shared = {Line for Line, Count in Counts.items() if Count > 1}
        if isinstance(Function, ast.Module):
            Function.name = "_Pyceler_Module"
        _Scalar_Region_Block(Function, Function.body, Available, Scope, Edits, Updates, Shared)
    for Position, Finding in enumerate(Findings):
        Plan = Updates.get(Finding.Line)
        if Plan is not None:
            Reason = "Only pure numeric spans are measured; surrounding Python calls and progress boundaries remain in source order. Checked arithmetic falls back before a span commits."
            Findings[Position] = replace(Finding, Classification="Scalar_Numeric_Region", Change="Extract guarded serial numeric region", Reason=Reason,
                                         Transformations=Plan["Transformations"], Constraints=("Exact built-in range with a supported literal stride", "Checked scalar arithmetic", "Inline fallback preserves partial updates"))
