from dataclasses import replace as _Rank_Replace

cdef object _Rank_Integer(object Node):
    Sign = 1
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, (ast.USub, ast.UAdd)):
        Sign = -1 if isinstance(Node.op, ast.USub) else 1
        Node = Node.operand
    if isinstance(Node, ast.Constant) and type(Node.value) is int:
        return Sign * Node.value
    return None

cdef list _Rank_Parts(object Node):
    Parts, Pending = [], [Node]
    while Pending:
        Current = Pending.pop()
        Parts.append(Current)
        for Child in ast.iter_child_nodes(Current):
            if not isinstance(Child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                Pending.append(Child)
    return Parts

cdef bint _Rank_Binds_Range(object Node):
    for Part in _Rank_Parts(Node):
        if isinstance(Part, ast.Name) and isinstance(Part.ctx, (ast.Store, ast.Del)) and Part.id == "range":
            return True
        if isinstance(Part, (ast.Import, ast.ImportFrom)) and any((Alias.asname or Alias.name.split(".")[0]) == "range" for Alias in Part.names):
            return True
        if isinstance(Part, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and Part.name == "range":
            return True
        if isinstance(Part, ast.ExceptHandler) and Part.name == "range":
            return True
    return False

cdef object _Rank_Iterations(object Node, list Parts, bint Range_Bound):
    if Range_Bound or not isinstance(Node, ast.For):
        return None
    Call = Node.iter
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or not 1 <= len(Call.args) <= 3:
        return None
    Values = [_Rank_Integer(Argument) for Argument in Call.args]
    if any(Value is None for Value in Values):
        return None
    Start, Stop, Step = (0, Values[0], 1) if len(Values) == 1 else (Values[0], Values[1], Values[2] if len(Values) == 3 else 1)
    if Step == 0:
        return None
    Count = max(0, (Stop - Start + Step - 1) // Step) if Step > 0 else max(0, (Start - Stop - Step - 1) // -Step)
    if Count and any(isinstance(Part, (ast.Break, ast.Return, ast.Raise, ast.Yield, ast.YieldFrom)) for Part in Parts):
        return None
    return Count

cdef void _Rank_Loops(object Node, int Depth, dict Loops, bint Range_Bound=False) except *:
    if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
        Depth = 0
        if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            Arguments = Node.args
            Names = [Item.arg for Item in Arguments.posonlyargs + Arguments.args + Arguments.kwonlyargs]
            if Arguments.vararg is not None:
                Names.append(Arguments.vararg.arg)
            if Arguments.kwarg is not None:
                Names.append(Arguments.kwarg.arg)
            Range_Bound = Range_Bound or "range" in Names
            Range_Bound |= _Rank_Binds_Range(Node)
    if isinstance(Node, (ast.For, ast.AsyncFor, ast.While)):
        Depth += 1
        Loops[Node.lineno] = (Node, Depth, Range_Bound)
    for Child in ast.iter_child_nodes(Node):
        _Rank_Loops(Child, Depth, Loops, Range_Bound)

cdef tuple _Rank_Constraints(object Finding):
    if Finding.Constraints:
        return Finding.Constraints
    if Finding.Classification == "Potential_Independent_Write" or "Guarded" in Finding.Change:
        return ("Validated input types and layout", "Proven bounds, arithmetic and writable storage", "Safe alias relationships", "Preserved exceptions and mutations")
    if Finding.Classification == "Loop_Carried_Dependency":
        return ("Preserve cross-iteration order", "Independent parallel execution is not qualified")
    if Finding.Classification == "Ordered_IO_Loop":
        return ("Preserve external call order and exception boundaries",)
    if Finding.Classification.startswith("Cython") or Finding.Classification == "Existing_OpenMP_Loop":
        return ("Preserve native declarations, directives and Cython semantics", "Native transformation requires a separate proof")
    return ("Unproven operations or dependencies remain unchanged",)

cdef dict _Rank_Transformations(object Edits):
    Transformations = {}
    if Edits is None:
        return Transformations
    for Line, Edit in Edits.items():
        Plan = Edit[3]
        if Plan is not None:
            Changes = tuple(Plan.get("Transformations", ()))
            Transformations.setdefault(Line, Changes)
            for Loop in Plan.get("Loops", ()):
                Transformations.setdefault(Loop.lineno, Changes)
    return Transformations

cdef list _Rank_Findings(list Findings, object Tree, object Edits=None):
    Loops = {}
    Native_Roots = {"numpy", "np", "cv2", "scipy"}
    Native_Names = set()
    if Tree is not None:
        Range_Bound = False
        for Statement in Tree.body:
            if isinstance(Statement, ast.Import):
                for Alias in Statement.names:
                    if Alias.name.split(".")[0] in ("numpy", "cv2", "scipy"):
                        Native_Roots.add(Alias.asname or Alias.name.split(".")[0])
            elif isinstance(Statement, ast.ImportFrom) and (Statement.module or "").split(".")[0] in ("numpy", "cv2", "scipy"):
                Native_Names.update(Alias.asname or Alias.name for Alias in Statement.names)
            if isinstance(Statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                Range_Bound |= Statement.name == "range"
            else:
                Range_Bound |= _Rank_Binds_Range(Statement)
        _Rank_Loops(Tree, 0, Loops, Range_Bound)
    Ranked = []
    Transformation_Map = _Rank_Transformations(Edits)
    for Finding in Findings:
        Constraints = _Rank_Constraints(Finding)
        Transformations = Finding.Transformations or Transformation_Map.get(Finding.Line, ())
        Entry = Loops.get(Finding.Line) if Tree is not None else None
        if Entry is None:
            Diagnostic = Finding.Classification in ("Cython_Static_Unsupported", "Cython_Context_Required")
            Score = 0.0 if Diagnostic else round(0.25 * (1 + len(Finding.Indexed_Reads) + len(Finding.Indexed_Writes)), 3)
            Reason = "Native Cython cost and iteration count are unknown; this conservative inspection score is not an estimated speedup."
            if Diagnostic:
                Reason = "Static analysis was inconclusive; no optimization benefit is estimated."
            Ranked.append(_Rank_Replace(Finding, Cost_Score=Score, Estimated_Iterations=None, Cost_Reason=Reason,
                                        Constraints=Constraints, Transformations=Transformations))
            continue
        Node, Depth, Range_Bound = Entry
        Parts = _Rank_Parts(Node)
        Iterations = _Rank_Iterations(Node, Parts, Range_Bound)
        Arithmetic = sum(isinstance(Part, (ast.BinOp, ast.UnaryOp, ast.AugAssign)) for Part in Parts)
        Accesses = sum(isinstance(Part, ast.Subscript) for Part in Parts)
        Branches = sum(isinstance(Part, (ast.If, ast.IfExp, ast.Compare)) for Part in Parts)
        Calls = [Part for Part in Parts if isinstance(Part, ast.Call)]
        Native = 0
        for Call in Calls:
            Function = Call.func
            if isinstance(Function, ast.Name) and Function.id in Native_Names:
                Native += 1
                continue
            if not isinstance(Function, ast.Attribute):
                continue
            while isinstance(Function, ast.Attribute):
                Function = Function.value
            if isinstance(Function, ast.Name) and Function.id in Native_Roots:
                Native += 1
        Work = 1.0 + 2 * Arithmetic + 3 * Accesses + Branches + max(0, len(Calls) - Native - 1)
        Factor = 4.0 if Iterations is None else math.log2(min(Iterations, 1000000000000) + 1)
        Score = Work * Factor * (1 + 0.5 * (Depth - 1))
        if Native:
            Score /= 1 + 3 * Native
        Estimate = "unknown iteration count" if Iterations is None else f"{Iterations} iterations per entry assuming built-in range"
        Reason = (f"Static heuristic: {Estimate}; nesting depth {Depth}; {Arithmetic} arithmetic operations, "
                  f"{Accesses} indexed accesses and {Branches} branches/comparisons in the loop subtree. ")
        if Native:
            Reason += f"Discounted {Native} possible native-library calls; bindings and native runtime share require profiling. "
        Reason += "The score ranks inspection priority, not correctness eligibility or measured speedup."
        Ranked.append(_Rank_Replace(Finding, Cost_Score=round(Score, 3), Estimated_Iterations=Iterations, Nesting_Depth=Depth,
                                    Cost_Reason=Reason, Constraints=Constraints, Transformations=Transformations))
    return Ranked
