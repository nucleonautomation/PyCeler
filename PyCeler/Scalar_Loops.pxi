class _Unsupported_Scalar(Exception):
    pass

cdef str _Scalar_Slot(str Name, dict Plan):
    return Plan["Slots"].setdefault(Name, "V" + str(len(Plan["Slots"])))

cdef str _Scalar_Operation(object Operator):
    if isinstance(Operator, ast.Add):
        return "_Pyceler_Add"
    if isinstance(Operator, ast.Sub):
        return "_Pyceler_Subtract"
    if isinstance(Operator, ast.Mult):
        return "_Pyceler_Multiply"
    if isinstance(Operator, ast.Mod):
        return "_Pyceler_Modulo"
    if isinstance(Operator, ast.FloorDiv):
        return "_Pyceler_Floor_Divide"
    raise _Unsupported_Scalar()

cdef str _Scalar_Expr(object Node, set Bound, dict Plan):
    if isinstance(Node, ast.Name) and Node.id in Bound:
        return _Scalar_Slot(Node.id, Plan)
    if isinstance(Node, ast.Constant) and type(Node.value) is int and 0 <= Node.value <= 2**63 - 1:
        return f"(<_Pyceler_Int>{Node.value})"
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.USub):
        if isinstance(Node.operand, ast.Constant) and type(Node.operand.value) is int and Node.operand.value == 2**63:
            return "_Pyceler_Min"
        if _Integer(Node.operand, 0):
            return "(<_Pyceler_Int>0)"
        return "_Pyceler_Subtract(0, " + _Scalar_Expr(Node.operand, Bound, Plan) + ")"
    if isinstance(Node, ast.BinOp):
        return _Scalar_Operation(Node.op) + "(" + _Scalar_Expr(Node.left, Bound, Plan) + ", " + _Scalar_Expr(Node.right, Bound, Plan) + ")"
    raise _Unsupported_Scalar()

cdef str _Scalar_Test(object Node, set Bound, dict Plan):
    if isinstance(Node, ast.Compare) and len(Node.ops) == 1:
        Operators = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
        Operator = Operators.get(type(Node.ops[0]))
        if Operator is None:
            raise _Unsupported_Scalar()
        return "(" + _Scalar_Expr(Node.left, Bound, Plan) + " " + Operator + " " + _Scalar_Expr(Node.comparators[0], Bound, Plan) + ")"
    if isinstance(Node, ast.BoolOp):
        Operator = " and " if isinstance(Node.op, ast.And) else " or "
        return "(" + Operator.join(_Scalar_Test(Value, Bound, Plan) for Value in Node.values) + ")"
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.Not):
        return "(not " + _Scalar_Test(Node.operand, Bound, Plan) + ")"
    if isinstance(Node, ast.Constant) and type(Node.value) is bool:
        return str(Node.value)
    return "(" + _Scalar_Expr(Node, Bound, Plan) + " != 0)"

cdef void _Scalar_Block(list Statements, set Bound, dict Plan, str Indent, bint In_Loop) except *:
    Lines = Plan["Lines"]
    for Node in Statements:
        if isinstance(Node, ast.Assign) and len(Node.targets) == 1 and isinstance(Node.targets[0], ast.Name):
            Name = Node.targets[0].id
            Value = _Scalar_Expr(Node.value, Bound, Plan)
            Lines.append(Indent + _Scalar_Slot(Name, Plan) + " = " + Value)
            Bound.add(Name)
        elif isinstance(Node, ast.AugAssign) and isinstance(Node.target, ast.Name) and Node.target.id in Bound:
            Target = _Scalar_Slot(Node.target.id, Plan)
            Lines.append(f"{Indent}{Target} = {_Scalar_Operation(Node.op)}({Target}, {_Scalar_Expr(Node.value, Bound, Plan)})")
        elif isinstance(Node, ast.If):
            Lines.append(Indent + "if " + _Scalar_Test(Node.test, Bound, Plan) + ":")
            Yes, No = Bound.copy(), Bound.copy()
            _Scalar_Block(Node.body, Yes, Plan, Indent + "    ", In_Loop)
            if Node.orelse:
                Lines.append(Indent + "else:")
                _Scalar_Block(Node.orelse, No, Plan, Indent + "    ", In_Loop)
            Bound.update(Yes & No)
        elif isinstance(Node, (ast.For, ast.While)) and not Node.orelse:
            Plan["Loops"].append(Node)
            Inner = Indent + "    "
            Local = Bound.copy()
            if isinstance(Node, ast.For):
                Call = Node.iter
                if not isinstance(Node.target, ast.Name) or not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or not 1 <= len(Call.args) <= 3:
                    raise _Unsupported_Scalar()
                Number = len(Plan["Loops"])
                Cursor, Stop = f"Cursor{Number}", f"Stop{Number}"
                Plan["Temporaries"].extend((Cursor, Stop))
                Begin = "0" if len(Call.args) == 1 else _Scalar_Expr(Call.args[0], Bound, Plan)
                End = _Scalar_Expr(Call.args[0 if len(Call.args) == 1 else 1], Bound, Plan)
                Step = 1
                if len(Call.args) == 3:
                    Literal = Call.args[2]
                    Negative = isinstance(Literal, ast.UnaryOp) and isinstance(Literal.op, ast.USub)
                    Literal = Literal.operand if Negative else Literal
                    if not isinstance(Literal, ast.Constant) or type(Literal.value) is not int or not 1 <= Literal.value <= 2**31 - 1:
                        raise _Unsupported_Scalar()
                    Step = -Literal.value if Negative else Literal.value
                Compare = "<" if Step > 0 else ">"
                Lines.extend([f"{Indent}{Cursor} = {Begin}", f"{Indent}{Stop} = {End}", f"{Indent}while {Cursor} {Compare} {Stop}:",
                              f"{Inner}{_Scalar_Slot(Node.target.id, Plan)} = {Cursor}", f"{Inner}{Cursor} = _Pyceler_Add({Cursor}, {Step})"])
                Local.add(Node.target.id)
            else:
                Lines.append(Indent + "while " + _Scalar_Test(Node.test, Bound, Plan) + ":")
            Lines.append(Inner + "_Pyceler_Poll(&Ticks)")
            _Scalar_Block(Node.body, Local, Plan, Inner, True)
        elif In_Loop and isinstance(Node, (ast.Break, ast.Continue)):
            Lines.append(Indent + ("break" if isinstance(Node, ast.Break) else "continue"))
        else:
            raise _Unsupported_Scalar()

cdef bint _Scalar_Fresh(object Expr):
    return (isinstance(Expr, ast.BinOp) and isinstance(Expr.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv))
            and any(isinstance(Part, ast.Name) for Part in ast.walk(Expr)))

cdef bint _Scalar_Result(object Expr, object Function, tuple Names):
    if isinstance(Expr, ast.BinOp):
        return _Scalar_Fresh(Expr)
    if not isinstance(Expr, ast.Name):
        return False
    Uncertain = set(Names)
    Uncertain.update(Node.target.id for Node in ast.walk(Function) if isinstance(Node, ast.For) and isinstance(Node.target, ast.Name))
    Copies = []
    for Node in ast.walk(Function):
        if isinstance(Node, ast.Assign) and len(Node.targets) == 1 and isinstance(Node.targets[0], ast.Name):
            Target = Node.targets[0].id
            Value = Node.value
            if isinstance(Value, ast.Name):
                Copies.append((Target, Value.id))
                continue
            if isinstance(Value, ast.Constant) and type(Value.value) is int and 0 <= Value.value <= 256:
                continue
            if not _Scalar_Fresh(Value):
                Uncertain.add(Target)
        elif isinstance(Node, ast.AugAssign) and isinstance(Node.target, ast.Name) and isinstance(Node.op, ast.Mod):
            Uncertain.add(Node.target.id)
    while True:
        Added = {Target for Target, Source in Copies if Source in Uncertain} - Uncertain
        if not Added:
            return Expr.id not in Uncertain
        Uncertain.update(Added)

include "Scalar_Division.pxi"
include "Scalar_Parallel.pxi"

cdef object _Scalar_Plan(object Function):
    Division = _Scalar_Division_Plan(Function)
    if Division is not None:
        return Division
    if not isinstance(Function, ast.FunctionDef) or Function.decorator_list or getattr(Function, "type_params", ()):
        return None
    Args = Function.args
    Names = tuple(Arg.arg for Arg in Args.posonlyargs + Args.args)
    if Args.kwonlyargs or Args.vararg or Args.kwarg or "range" in Names:
        return None
    Body = Function.body[1:] if ast.get_docstring(Function, clean=False) is not None else Function.body
    if len(Body) < 2 or not isinstance(Body[-1], ast.Return) or Body[0].lineno <= Function.lineno:
        return None
    if Body[0] is not Function.body[0] and Body[0].lineno <= Function.body[0].end_lineno:
        return None
    if not any(isinstance(Part, (ast.For, ast.While)) for Part in Body) or not _Scalar_Result(Body[-1].value, Function, Names):
        return None
    Plan = dict(Kind="scalar", Names=Names, Start=Body[0].lineno, Slots={}, Temporaries=[], Lines=[], Loops=[], Size_Function=Function)
    for Name in Names:
        _Scalar_Slot(Name, Plan)
    Bound = set(Names)
    try:
        _Scalar_Block(Body[:-1], Bound, Plan, "    ", False)
        Plan["Lines"].append("    return " + _Scalar_Expr(Body[-1].value, Bound, Plan))
    except _Unsupported_Scalar:
        return _Scalar_Division_Plan(Function)
    if "range" in Plan["Slots"] or not Plan["Loops"]:
        return None
    Plan["Parallel_Reduction"] = _Scalar_Parallel_Plan(Function, Plan)
    return Plan

cdef str _Scalar_Kernel(dict Plan, int Line, bint Parallel=False):
    if Plan.get("Division"):
        return _Scalar_Division_Kernel(Plan, Line)
    Args = [Plan["Slots"][Name] for Name in Plan["Names"]]
    Locals = list(Plan["Slots"].values())[len(Args):] + Plan["Temporaries"]
    Native = f"_Pyceler_Int_Loop_{Line}"
    Lines = [f"cdef _Pyceler_Int {Native}({', '.join('_Pyceler_Int ' + Var for Var in Args)}) except? -1 nogil:",
             "    cdef unsigned int Ticks = 0"]
    if Locals:
        Lines.append("    cdef _Pyceler_Int " + ", ".join(Locals))
    Lines.extend(Plan["Lines"])
    Arguments = ", ".join(Args)
    Lines.extend(["", f"cdef object _Pyceler_Scalar_{Line}({', '.join(['object ' + Var for Var in Args] + ['object Baseline'])}):",
                  "    import builtins as _Pyceler_Builtins", "    cdef _Pyceler_Int Result"])
    if Args:
        Lines.append("    cdef _Pyceler_Int " + ", ".join("N" + Var for Var in Args))
    if any(isinstance(Loop, ast.For) for Loop in Plan["Loops"]):
        Lines.extend(["    if not _Pyceler_Bindings(Baseline):", f"        return Baseline({Arguments})"])
    for Var in Args:
        Lines.extend([f"    if _Pyceler_Builtins.type({Var}) is not _Pyceler_Builtins.int or not -9223372036854775808 <= {Var} <= 9223372036854775807:",
                      f"        return Baseline({Arguments})", f"    N{Var} = {Var}"])
    Lines.extend(["    try:", "        with nogil:", f"            Result = {Native}({', '.join('N' + Var for Var in Args)})",
                  "    except _Pyceler_Overflow:", "        pass", "    else:", "        return Result", f"    return Baseline({Arguments})"])
    Serial = "\n".join(Lines)
    return _Scalar_Parallel_Kernel(Plan, Line, Serial, Parallel) if Plan.get("Parallel_Reduction") else Serial
