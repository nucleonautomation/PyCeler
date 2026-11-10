cdef object _Scalar_Parallel_Tree(object Node, tuple Names):
    if isinstance(Node, ast.Name) and Node.id in Names:
        return ("arg", Names.index(Node.id))
    if isinstance(Node, ast.Constant) and type(Node.value) is int:
        return ("constant", Node.value)
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.USub):
        return ("negative", _Scalar_Parallel_Tree(Node.operand, Names))
    if isinstance(Node, ast.BinOp):
        Operators = {ast.Add: "add", ast.Sub: "subtract", ast.Mult: "multiply", ast.Mod: "modulo", ast.FloorDiv: "floor"}
        Operator = Operators.get(type(Node.op))
        if Operator is not None:
            return (Operator, _Scalar_Parallel_Tree(Node.left, Names), _Scalar_Parallel_Tree(Node.right, Names))
    raise _Unsupported_Scalar()

cdef object _Scalar_Parallel_Plan(object Function, dict Plan):
    Body = Function.body[1:] if ast.get_docstring(Function, clean=False) is not None else Function.body
    if len(Body) != 3 or not isinstance(Body[0], ast.Assign) or len(Body[0].targets) != 1 or not isinstance(Body[0].targets[0], ast.Name):
        return None
    Initial = Body[0].value
    Total = Body[0].targets[0].id
    Loop = Body[1]
    if not isinstance(Initial, ast.Constant) or type(Initial.value) is not int or not 0 <= Initial.value <= 256:
        return None
    if not isinstance(Loop, ast.For) or not isinstance(Loop.target, ast.Name) or Loop.orelse or len(Loop.body) != 1:
        return None
    Statement = Loop.body[0]
    Index = Loop.target.id
    Names = Plan["Names"]
    if Total in Names or Index in Names or Index == Total or not _Name(Body[2].value, Total):
        return None
    if not isinstance(Statement, ast.AugAssign) or not _Name(Statement.target, Total) or not isinstance(Statement.op, ast.Add):
        return None
    Call = Loop.iter
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or not 1 <= len(Call.args) <= 3:
        return None
    try:
        Begin = ("constant", 0) if len(Call.args) == 1 else _Scalar_Parallel_Tree(Call.args[0], Names)
        Stop = _Scalar_Parallel_Tree(Call.args[0 if len(Call.args) == 1 else 1], Names)
        Step = ast.literal_eval(Call.args[2]) if len(Call.args) == 3 else 1
        Term = _Scalar_Parallel_Tree(Statement.value, (*Names, Index))
    except (_Unsupported_Scalar, ValueError, TypeError):
        return None
    if type(Step) is not int or not Step or abs(Step) > 2**31 - 1:
        return None
    return dict(Begin=Begin, Stop=Stop, Step=Step, Term=Term, Initial=Initial.value)

cdef str _Scalar_Parallel_Expression(tuple Node, list Names):
    if Node[0] == "arg":
        return Names[Node[1]]
    if Node[0] == "constant":
        return f"(<_Pyceler_Int>{Node[1]})"
    if Node[0] == "negative":
        if Node[1] == ("constant", 2**63):
            return "_Pyceler_Min"
        return "(-" + _Scalar_Parallel_Expression(Node[1], Names) + ")"
    Left, Right = (_Scalar_Parallel_Expression(Child, Names) for Child in Node[1:])
    Operators = {"add": "+", "subtract": "-", "multiply": "*"}
    if Node[0] in Operators:
        return f"({Left} {Operators[Node[0]]} {Right})"
    Helper = "_Pyceler_Reduction_Modulo" if Node[0] == "modulo" else "_Pyceler_Reduction_Floor"
    return f"{Helper}({Left}, {Right})"

cdef str _Scalar_Parallel_Kernel(dict Plan, int Line, str Serial, bint Parallel):
    Reduction = Plan["Parallel_Reduction"]
    Slots = [Plan["Slots"][Name] for Name in Plan["Names"]]
    Args = ", ".join(Slots)
    Typed = ["_Pyceler_Int " + Slot for Slot in Slots]
    Term = f"_Pyceler_Reduction_Term_{Line}"
    Run = f"_Pyceler_Reduction_Run_{Line}"
    Sequential = f"_Pyceler_Reduction_Serial_{Line}"
    Helper = f"_Pyceler_Scalar_{Line}"
    Expression = _Scalar_Parallel_Expression(Reduction["Term"], [*Slots, "Index"])
    Call = f"{Term}({', '.join([*Slots, 'Begin + Position * (<_Pyceler_Int>' + str(Reduction['Step']) + ')'])})"
    Signature = ', '.join([*Typed, '_Pyceler_Int Begin', 'Py_ssize_t Count'])
    Lines = [f"cdef inline _Pyceler_Int {Term}({', '.join([*Typed, '_Pyceler_Int Index'])}) noexcept nogil:",
             "    return " + Expression, "", f"cdef object {Sequential}({Signature}):",
             "    cdef Py_ssize_t Position, Start = 0, End", "    cdef _Pyceler_Int Result = 0",
             "    global _Pyceler_Reduction_Serial_Calls, _Pyceler_Reduction_Last_Team, _Pyceler_Reduction_Last_Mode",
             "    _Pyceler_Reduction_Serial_Calls += 1", "    _Pyceler_Reduction_Last_Team = 1", "    _Pyceler_Reduction_Last_Mode = 'serial'",
             "    while Start < Count:", "        End = Start + 1048576 if Count - Start > 1048576 else Count",
             "        with nogil:", "            for Position in range(Start, End):", f"                Result += {Call}",
             "        Start = End", "        _Pyceler_Signals()", f"    return Result + (<_Pyceler_Int>{Reduction['Initial']})"]
    if Parallel:
        Lines.extend(["", f"cdef object {Run}({Signature}):",
                      "    cdef Py_ssize_t Position, Start = 0, End", "    cdef _Pyceler_Int Result = 0", "    cdef int Team[1]", "    Team[0] = 1",
                      "    global _Pyceler_Reduction_Calls, _Pyceler_Reduction_Last_Team, _Pyceler_Reduction_Last_Mode",
                      "    _Pyceler_Reduction_Calls += 1", "    _Pyceler_Reduction_Last_Mode = 'parallel'",
                      "    while Start < Count:", "        End = Start + 1048576 if Count - Start > 1048576 else Count",
                      "        for Position in _Pyceler_Prange(Start, End, nogil=True, schedule='static'):",
                      "            if Position == Start:", "                Team[0] = _Pyceler_Reduction_Team()", f"            Result += {Call}",
                      "        _Pyceler_Reduction_Last_Team = Team[0]", "        Start = End", "        _Pyceler_Signals()",
                      f"    return Result + (<_Pyceler_Int>{Reduction['Initial']})"])
    Parameters = ['object ' + Slot for Slot in Slots] + ['object Baseline'] + (['bint Allow_Threads'] if Parallel else [])
    Lines.extend(["", f"cdef object {Helper}({', '.join(Parameters)}):", "    cdef object Proof",
                  "    global _Pyceler_Reduction_Last_Mode, _Pyceler_Reduction_Fallback_Reason, _Pyceler_Reduction_Last_Team",
                  "    _Pyceler_Reduction_Last_Mode = 'python'", "    _Pyceler_Reduction_Last_Team = 0",
                  "    _Pyceler_Reduction_Fallback_Reason = None", "    if not _Pyceler_Bindings(Baseline):",
                  "        _Pyceler_Reduction_Fallback_Reason = 'bindings'", f"        return Baseline({Args})",
                  f"    Proof = _Pyceler_Reduction_Allowed(({Args},), {Reduction!r})", "    if Proof is None:",
                  "        _Pyceler_Reduction_Fallback_Reason = 'integer_bounds_or_type'", f"        return Baseline({Args})",
                  "    if Proof[1] == 0:", "        _Pyceler_Reduction_Fallback_Reason = 'empty_range'", f"        return Baseline({Args})"])
    if Parallel:
        Lines.extend(["    from threading import current_thread, main_thread",
                      "    if Allow_Threads and current_thread() is main_thread() and not _Pyceler_In_Parallel():",
                      f"        return {Run}({Args}, Proof[0], Proof[1])"])
    Lines.append(f"    return {Sequential}({Args}, Proof[0], Proof[1])")
    return "\n".join(Lines)
