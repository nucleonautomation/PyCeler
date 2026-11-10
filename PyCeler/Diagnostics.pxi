from dataclasses import replace as _Diagnostic_Replace
from .Loop_Detector import _Loop_Diagnostic

cdef object _Diagnostic(object Node, str Code, str Message, str Suggestion, str Severity="unsupported"):
    return _Loop_Diagnostic(Code=Code, Line=Node.lineno, Column=Node.col_offset + 1, End_Line=Node.end_lineno,
                            End_Column=Node.end_col_offset + 1, Severity=Severity, Message=Message, Suggestion=Suggestion)

cdef void _Diagnostic_Scopes(object Node, object Function, dict Loops, dict Parents) except *:
    if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        Function = Node
    elif isinstance(Node, ast.ClassDef):
        Function = None
    if isinstance(Node, (ast.For, ast.AsyncFor, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        Loops[Node.lineno] = (Node, Function)
    for Child in ast.iter_child_nodes(Node):
        Parents[Child] = Node
        _Diagnostic_Scopes(Child, Function, Loops, Parents)

cdef object _Diagnostic_Interval(object Node, dict Values):
    if isinstance(Node, ast.Constant) and type(Node.value) is int:
        return Node.value, Node.value
    if isinstance(Node, ast.Name):
        return Values.get(Node.id)
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, (ast.UAdd, ast.USub)):
        Value = _Diagnostic_Interval(Node.operand, Values)
        return None if Value is None else Value if isinstance(Node.op, ast.UAdd) else (-Value[1], -Value[0])
    if not isinstance(Node, ast.BinOp):
        return None
    Left, Right = _Diagnostic_Interval(Node.left, Values), _Diagnostic_Interval(Node.right, Values)
    if Left is None or Right is None:
        return None
    if isinstance(Node.op, ast.Add):
        return Left[0] + Right[0], Left[1] + Right[1]
    if isinstance(Node.op, ast.Sub):
        return Left[0] - Right[1], Left[1] - Right[0]
    if isinstance(Node.op, ast.Mult):
        Products = [A * B for A in Left for B in Right]
        return min(Products), max(Products)
    if isinstance(Node.op, ast.Mod) and Right[0] == Right[1] and Right[0]:
        Divisor = Right[0]
        return (0, Divisor - 1) if Divisor > 0 else (Divisor + 1, 0)
    if isinstance(Node.op, ast.FloorDiv) and (Right[0] > 0 or Right[1] < 0):
        Quotients = [A // B for A in Left for B in Right]
        return min(Quotients), max(Quotients)
    return None

cdef dict _Diagnostic_Values(object Loop, dict Parents):
    Values = {}
    Current = Loop
    Levels = []
    while Current in Parents:
        Parent = Parents[Current]
        if isinstance(Parent, (ast.Module, ast.FunctionDef)) or hasattr(Parent, "body"):
            Statements = getattr(Parent, "body", ())
            if isinstance(Statements, list) and Current in Statements:
                Levels.append(Statements[:Statements.index(Current)])
        if isinstance(Parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        Current = Parent
    for Statements in reversed(Levels):
        for Statement in Statements:
            if isinstance(Statement, ast.Assign) and len(Statement.targets) == 1 and isinstance(Statement.targets[0], ast.Name):
                Name = Statement.targets[0].id
                Value = _Diagnostic_Interval(Statement.value, Values)
                if Value is not None:
                    Values[Name] = Value
                else:
                    Values.pop(Name, None)
            else:
                for Part in ast.walk(Statement):
                    if isinstance(Part, ast.Name) and isinstance(Part.ctx, (ast.Store, ast.Del)):
                        Values.pop(Part.id, None)
    return Values

cdef list _Diagnostic_Overflow(object Loop, dict Parents):
    if not isinstance(Loop, ast.For) or not isinstance(Loop.target, ast.Name):
        return []
    Call = Loop.iter
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or not 1 <= len(Call.args) <= 3:
        return []
    Values = _Diagnostic_Values(Loop, Parents)
    Bounds = [_Diagnostic_Interval(Argument, Values) for Argument in Call.args]
    if any(Value is None or Value[0] != Value[1] for Value in Bounds):
        return []
    Bounds = [Value[0] for Value in Bounds]
    Start, Stop, Step = (0, Bounds[0], 1) if len(Bounds) == 1 else (Bounds[0], Bounds[1], Bounds[2] if len(Bounds) == 3 else 1)
    if Step == 0:
        return []
    Count = max(0, (Stop - Start + Step - 1) // Step) if Step > 0 else max(0, (Start - Stop - Step - 1) // -Step)
    if not Count:
        return []
    End = Start + (Count - 1) * Step
    Values[Loop.target.id] = min(Start, End), max(Start, End)
    for Node in ast.walk(Loop):
        Value = None
        if isinstance(Node, ast.BinOp):
            Value = _Diagnostic_Interval(Node, Values)
        elif isinstance(Node, ast.AugAssign) and isinstance(Node.target, ast.Name) and isinstance(Node.op, (ast.Add, ast.Sub)):
            Initial, Term = Values.get(Node.target.id), _Diagnostic_Interval(Node.value, Values)
            if Initial is not None and Term is not None:
                if isinstance(Node.op, ast.Sub):
                    Term = -Term[1], -Term[0]
                Value = Initial[0] + Count * Term[0], Initial[1] + Count * Term[1]
        if Value is not None and (Value[0] < -(2**63) or Value[1] > 2**63 - 1):
            return [_Diagnostic(Node, "integer_range_may_overflow", "Static integer bounds may exceed signed 64-bit arithmetic; checked native execution can fall back to Python.",
                                "Keep arbitrary-precision fallback and inspect representative inputs; this bound is conservative, not a measured runtime outcome.", "warning")]
    return []

cdef list _Diagnostic_Blockers(object Loop, object Function, object Finding):
    if isinstance(Loop, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        return [_Diagnostic(Loop, "unproven_comprehension", Finding.Reason,
                            "Keep Python evaluation until iterable consumption, filtering, scope, identity and exception behavior are proven equivalent.")]
    Parts = _Rank_Parts(Loop)
    Scalar = not Finding.Indexed_Reads and not Finding.Indexed_Writes
    Diagnostics = []
    if Function is None:
        Diagnostics.append(_Diagnostic(Loop, "unproven_module_region", "Module-level scalar state is observable and mutable by signal handlers; native span extraction cannot preserve those updates.",
                                       "Keep module execution in Python or move numeric work into a function with local state and a verified native plan."))
    if Scalar and Function is not None:
        if Function.decorator_list:
            Diagnostics.append(_Diagnostic(Function, "decorated_function", "Whole-function scalar specialization cannot establish the behavior of this decorated function.",
                                           "Keep the decorator behavior or isolate a numeric helper whose semantics can be verified."))
        if not Function.body or not isinstance(Function.body[-1], ast.Return) or Function.body[-1].value is None:
            Diagnostics.append(_Diagnostic(Function, "no_scalar_return_or_region", "Whole-function scalar specialization has no numeric return and no safe scalar region was established.",
                                           "Inspect region blockers; the public function may keep its original return behavior when a numeric region can be isolated."))
    for Part in Parts:
        if isinstance(Part, ast.Call):
            if isinstance(Part.func, ast.Name) and Part.func.id in ("range", "len"):
                continue
            Name = ast.unparse(Part.func)[:100]
            Diagnostics.append(_Diagnostic(Part, "unproven_call_boundary", f"Call {Name} is inside a loop without a proven native/callback boundary.",
                                           "Preserve call order and exceptions; isolate numeric work or use a supported callback boundary."))
        elif Scalar and isinstance(Part, (ast.BinOp, ast.AugAssign)):
            if isinstance(Part.op, ast.Div):
                Diagnostics.append(_Diagnostic(Part, "unproven_true_division", "This true-division expression is outside a proven scalar floating-point region.",
                                               "Use a supported numeric reduction shape; integer-to-float conversion, rounding and accumulation order must be preserved."))
                continue
            try:
                _Scalar_Operation(Part.op)
            except _Unsupported_Scalar:
                Operator = type(Part.op).__name__
                Diagnostics.append(_Diagnostic(Part, "unsupported_scalar_operator", f"Scalar operator {Operator} has no verified native lowering for this loop.",
                                               "Keep the Python operation until a guarded lowering with equivalent results and exceptions is available."))
        elif Scalar and isinstance(Part, (ast.Try, ast.With, ast.AsyncWith, ast.Yield, ast.YieldFrom, ast.Await, ast.Global, ast.Nonlocal)):
            Diagnostics.append(_Diagnostic(Part, "unproven_control_or_scope", f"{type(Part).__name__} requires control-flow or scope guarantees unavailable for this scalar region.",
                                           "Preserve the original control flow and isolate a side-effect-free numeric region."))
    return Diagnostics

cdef void _Apply_Diagnostics(object Tree, list Findings, dict Edits) except *:
    Loops, Parents = {}, {}
    _Diagnostic_Scopes(Tree, None, Loops, Parents)
    for Index, Finding in enumerate(Findings):
        Entry = Loops.get(Finding.Line)
        if Entry is None:
            continue
        Loop, Function = Entry
        Diagnostics = _Diagnostic_Blockers(Loop, Function, Finding) if Finding.Change == "Keep original loop" else []
        if not Finding.Indexed_Reads and not Finding.Indexed_Writes:
            Diagnostics.extend(_Diagnostic_Overflow(Loop, Parents))
        Unique = {}
        for Item in Diagnostics:
            Unique.setdefault((Item["Code"], Item["Line"], Item["Column"]), Item)
        Diagnostics = sorted(Unique.values(), key=lambda Item: (Item["Line"], Item["Column"], Item["Code"]))
        Reason = Finding.Reason
        Blockers = [Item["Message"] for Item in Diagnostics if Item["Severity"] == "unsupported"]
        if Blockers and Finding.Classification == "Unknown" and not Finding.Indexed_Reads and not Finding.Indexed_Writes:
            Reason = " ".join(dict.fromkeys(Blockers))
        Findings[Index] = _Diagnostic_Replace(Finding, Reason=Reason, Diagnostics=tuple(Diagnostics))
