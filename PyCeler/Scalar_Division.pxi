cdef tuple _Scalar_Division_Expr(object Node, set Bound, dict Plan):
    if isinstance(Node, ast.Name) and Node.id in Bound:
        return _Scalar_Slot(Node.id, Plan), "float" if Node.id in Plan.get("Floating", ()) else "int"
    if isinstance(Node, ast.Constant) and type(Node.value) is float and math.isfinite(Node.value):
        return repr(Node.value), "float"
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.USub):
        if isinstance(Node.operand, ast.Constant) and type(Node.operand.value) is int and Node.operand.value == 2**63:
            return "_Pyceler_Min", "int"
        Value, Kind = _Scalar_Division_Expr(Node.operand, Bound, Plan)
        return ("_Pyceler_Float_Negate(" + Value + ")" if Kind == "float" else "_Pyceler_Subtract(0, " + Value + ")"), Kind
    if isinstance(Node, ast.BinOp):
        Left, Left_Kind = _Scalar_Division_Expr(Node.left, Bound, Plan)
        Right, Right_Kind = _Scalar_Division_Expr(Node.right, Bound, Plan)
        Floating = "float" in (Left_Kind, Right_Kind)
        if isinstance(Node.op, ast.Div):
            Helper = "_Pyceler_Float_Divide" if Floating else "_Pyceler_True_Divide"
            return Helper + "(" + Left + ", " + Right + ")", "float"
        if not Floating:
            return _Scalar_Operation(Node.op) + "(" + Left + ", " + Right + ")", "int"
        Helpers = {ast.Add: "Add", ast.Sub: "Subtract", ast.Mult: "Multiply"}
        Helper = Helpers.get(type(Node.op))
        if Helper is None:
            raise _Unsupported_Scalar()
        return "_Pyceler_Float_" + Helper + "(" + Left + ", " + Right + ")", "float"
    return _Scalar_Expr(Node, Bound, Plan), "int"

cdef object _Scalar_Division_Plan(object Function):
    if not isinstance(Function, ast.FunctionDef) or Function.decorator_list or getattr(Function, "type_params", ()):
        return None
    Args = Function.args
    Names = tuple(Arg.arg for Arg in Args.posonlyargs + Args.args)
    if Args.kwonlyargs or Args.vararg or Args.kwarg or "range" in Names:
        return None
    Body = Function.body[1:] if ast.get_docstring(Function, clean=False) is not None else Function.body
    if len(Body) != 3 or not isinstance(Body[0], ast.Assign) or len(Body[0].targets) != 1 or not isinstance(Body[0].targets[0], ast.Name):
        return None
    Initialize, Loop, Result = Body
    Total = Initialize.targets[0].id
    if Total in Names or not isinstance(Result, ast.Return) or not _Name(Result.value, Total):
        return None
    if not isinstance(Loop, ast.For) or not isinstance(Loop.target, ast.Name) or Loop.orelse or len(Loop.body) != 1:
        return None
    Update = Loop.body[0]
    if not isinstance(Update, ast.AugAssign) or not _Name(Update.target, Total) or not isinstance(Update.op, ast.Add):
        return None
    Call = Loop.iter
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or not 1 <= len(Call.args) <= 3:
        return None
    if len({Total, Loop.target.id, "range"}) != 3 or Loop.target.id in Names:
        return None
    if Initialize.lineno <= Function.lineno or any(Left.end_lineno >= Right.lineno for Left, Right in zip(Body, Body[1:])):
        return None
    if Initialize is not Function.body[0] and Initialize.lineno <= Function.body[0].end_lineno:
        return None
    Plan = dict(Kind="scalar", Division=True, Names=Names, Start=Initialize.lineno, Slots={}, Temporaries=[], Lines=[], Loops=[Loop], Size_Function=Function)
    for Name in Names:
        _Scalar_Slot(Name, Plan)
    try:
        Initial = ast.literal_eval(Initialize.value)
        if type(Initial) not in (int, float) or not math.isfinite(Initial) or type(Initial) is int and abs(Initial) > 2**53:
            return None
        Begin = "0" if len(Call.args) == 1 else _Scalar_Expr(Call.args[0], set(Names), Plan)
        End = _Scalar_Expr(Call.args[0 if len(Call.args) == 1 else 1], set(Names), Plan)
        Step = 1 if len(Call.args) < 3 else ast.literal_eval(Call.args[2])
        if type(Step) is not int or not 1 <= abs(Step) <= 2**31 - 1:
            return None
        Expression, Kind = _Scalar_Division_Expr(Update.value, set(Names) | {Loop.target.id}, Plan)
        if Kind != "float":
            return None
    except (_Unsupported_Scalar, ValueError, TypeError, OverflowError, SyntaxError):
        return None
    Plan.update(Begin=Begin, End=End, Step=Step, Initial=repr(float(Initial)), Expression=Expression, Counter=_Scalar_Slot(Loop.target.id, Plan))
    return Plan

cdef str _Scalar_Division_Kernel(dict Plan, int Line):
    Args = [Plan["Slots"][Name] for Name in Plan["Names"]]
    Locals = list(Plan["Slots"].values())[len(Args):]
    Native = f"_Pyceler_Int_Loop_{Line}"
    Parameters = [*("_Pyceler_Int " + Var for Var in Args), "bint* Changed"]
    Compare = "<" if Plan["Step"] > 0 else ">"
    Lines = [f"cdef double {Native}({', '.join(Parameters)}) except? -1 nogil:",
             "    cdef unsigned int Ticks = 0", "    cdef _Pyceler_Int Cursor, Stop",
             "    cdef _Pyceler_Int " + ", ".join(Locals), f"    cdef double Total = {Plan['Initial']}",
             f"    Cursor = {Plan['Begin']}", f"    Stop = {Plan['End']}", f"    while Cursor {Compare} Stop:",
             f"        {Plan['Counter']} = Cursor", f"        Cursor = _Pyceler_Add(Cursor, {Plan['Step']})",
             "        _Pyceler_Poll(&Ticks)", f"        Total = _Pyceler_Float_Add(Total, {Plan['Expression']})",
             "        Changed[0] = True", "    return Total"]
    Arguments = ", ".join(Args)
    Lines.extend(["", f"cdef object _Pyceler_Scalar_{Line}({', '.join(['object ' + Var for Var in Args] + ['object Baseline'])}):",
                  "    import builtins as _Pyceler_Builtins", "    cdef double Result", "    cdef bint Changed = False"])
    if Args:
        Lines.append("    cdef _Pyceler_Int " + ", ".join("N" + Var for Var in Args))
    Lines.extend(["    if not _Pyceler_Bindings(Baseline) or _Pyceler_Scalar_Rounding() != _Pyceler_Scalar_Nearest:", f"        return Baseline({Arguments})"])
    for Var in Args:
        Lines.extend([f"    if _Pyceler_Builtins.type({Var}) is not _Pyceler_Builtins.int or not -9223372036854775808 <= {Var} <= 9223372036854775807:",
                      f"        return Baseline({Arguments})", f"    N{Var} = {Var}"])
    Call = ", ".join([*("N" + Var for Var in Args), "&Changed"])
    Lines.extend(["    try:", "        with nogil:", f"            Result = {Native}({Call})",
                  "    except _Pyceler_Overflow:", "        pass", "    else:", "        if Changed:", "            return Result", f"    return Baseline({Arguments})"])
    return "\n".join(Lines)
