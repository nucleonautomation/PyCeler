cdef object _Coordinate(object Node, str Index, int Axis):
    if not isinstance(Node, ast.Assign) or len(Node.targets) != 1 or not isinstance(Node.targets[0], ast.Name):
        return None
    Expr = Node.value
    if not isinstance(Expr, ast.BinOp) or not isinstance(Expr.op, ast.Sub) or not isinstance(Expr.right, ast.Name):
        return None
    Call = Expr.left
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "float") or Call.keywords or len(Call.args) != 1:
        return None
    Cell = Call.args[0]
    if not isinstance(Cell, ast.Subscript) or not isinstance(Cell.value, ast.Name) or not isinstance(Cell.slice, ast.Tuple) or len(Cell.slice.elts) != 2:
        return None
    if _Name(Cell.slice.elts[0], Index) and _Integer(Cell.slice.elts[1], Axis):
        return Node.targets[0].id, Cell.value.id, Expr.right.id
    return None

cdef object _Projection_Gate(object Node, str Index):
    if not isinstance(Node, ast.If) or Node.orelse or len(Node.body) != 1 or not isinstance(Node.body[0], ast.Continue):
        return None
    Test = Node.test
    Flag = None
    if isinstance(Test, ast.BoolOp) and isinstance(Test.op, ast.And) and len(Test.values) == 2 and isinstance(Test.values[0], ast.Name):
        Flag, Test = Test.values[0].id, Test.values[1]
    if not isinstance(Test, ast.Compare) or len(Test.ops) != 1 or not isinstance(Test.ops[0], ast.NotEq) or not isinstance(Test.comparators[0], ast.Name):
        return None
    Cell = Test.left
    if isinstance(Cell, ast.Subscript) and isinstance(Cell.value, ast.Name) and _Name(Cell.slice, Index):
        return (Flag, Cell.value.id, Test.comparators[0].id)
    return None

cdef object _Projection_Region(object Function, object Loop, list Before, set Bound):
    if not Before or Loop.orelse or not isinstance(Loop.target, ast.Name) or not 4 <= len(Loop.body) <= 8:
        return None
    Call = Loop.iter
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or len(Call.args) != 1 or any(isinstance(Node, (ast.Try, ast.With, getattr(ast, "TryStar", ast.Try))) for Node in ast.walk(Function)):
        return None
    End = Call.args[0]
    Size = End.id if isinstance(End, ast.Name) else None
    Init = Before[-1]
    if not isinstance(Init, ast.Assign) or len(Init.targets) != 1 or not isinstance(Init.targets[0], ast.Name) or not _Integer(Init.value, 0):
        return None
    Count, Cursor = Init.targets[0].id, Loop.target.id
    Index, Rem = Cursor, None
    Body = list(Loop.body)
    First = Body[0]
    if isinstance(First, ast.Assign) and len(First.targets) == 1 and isinstance(First.targets[0], ast.Name) and _Map_Cell(First.value, (Cursor,)) is not None:
        Index, Rem = First.targets[0].id, First.value.value.id
        Body.pop(0)
    Gates = []
    while Body and isinstance(Body[0], ast.If):
        Gate = _Projection_Gate(Body.pop(0), Index)
        if Gate is None or len(Gates) == 2:
            return None
        Gates.append(Gate)
    if len(Body) not in (4, 5):
        return None
    X, Y = _Coordinate(Body[0], Index, 0), _Coordinate(Body[1], Index, 1)
    if X is None or Y is None or X[1] != Y[1] or (Size is None and _Axis_Source(End, 0, (), {}) != (Rem or X[1])):
        return None
    Dot = Body[2]
    if not isinstance(Dot, ast.Assign) or len(Dot.targets) != 1 or not isinstance(Dot.targets[0], ast.Name) or not isinstance(Dot.value, ast.BinOp) or not isinstance(Dot.value.op, ast.Add):
        return None
    Distance = Dot.targets[0].id
    Factors = []
    for Product, Axis in ((Dot.value.left, X), (Dot.value.right, Y)):
        if not isinstance(Product, ast.BinOp) or not isinstance(Product.op, ast.Mult) or not _Name(Product.left, Axis[0]) or not isinstance(Product.right, ast.Name):
            return None
        Factors.append(Product.right.id)
    Check = Body[-1]
    if not isinstance(Check, ast.If) or Check.orelse or len(Check.body) != 1 or not isinstance(Check.test, ast.Compare) or len(Check.test.ops) != 1 or not isinstance(Check.test.ops[0], ast.LtE) or not isinstance(Check.test.comparators[0], ast.Name):
        return None
    if len(Body) == 5:
        Normalize = ast.parse(f"if {Distance} < 0.0:\n    {Distance} = -{Distance}").body[0]
        if ast.dump(Body[3]) != ast.dump(Normalize) or not _Name(Check.test.left, Distance):
            return None
    else:
        Call = Check.test.left
        if not isinstance(Call, ast.Call) or not _Name(Call.func, "abs") or Call.keywords or len(Call.args) != 1 or not _Name(Call.args[0], Distance):
            return None
    Add = Check.body[0]
    if not isinstance(Add, ast.AugAssign) or not isinstance(Add.op, ast.Add) or not _Name(Add.target, Count) or not _Integer(Add.value, 1):
        return None
    Names = (X[1], *((Rem,) if Rem else ()), X[2], Y[2], *Factors, Check.test.comparators[0].id,
             *(Name for Gate in Gates for Name in Gate if Name is not None), *((Size,) if Size else ()))
    Temps = [Cursor, X[0], Y[0], Distance, Count] + ([Index] if Rem else [])
    if len(set(Names + tuple(Temps))) != len(Names) + len(Temps) or not set(Names) <= Bound:
        return None
    return dict(Kind="projection", Label="line inlier count", Names=Names, Output=X[1], Key=X[1], Result=Count, Start=Loop.lineno,
                Region=True, Private=set(Temps) - {Count}, Probe=_Region_Function(Function, [Init, Loop], Names, Count),
                Loops=[Loop], Indirect=Rem is not None, Gates=Gates, Named_Size=Size is not None)

cdef str _Projection_Kernel(dict Plan, int Line, bint Parallel):
    Indirect = Plan["Indirect"]
    Variables = [f"V{I}" for I in range(len(Plan["Names"]))]
    Base = 2 if Indirect else 1
    Coeff = Variables[Base:Base + 5]
    Checks, Tests = [], []
    Signature = "const _Pyceler_Coordinate[:, :] Points, const _Pyceler_S64[:] Rem, double Ax, double Ay, double Nx, double Ny, double Limit"
    Pass = "Points, Rem, Ax, Ay, Nx, Ny, Limit"
    Call = [Variables[0], "Indices" if Indirect else "None", *Coeff]
    for Number, (Flag, Labels, Label) in enumerate(Plan["Gates"]):
        F = Variables[Plan["Names"].index(Flag)] if Flag is not None else "True"
        A, V = Variables[Plan["Names"].index(Labels)], Variables[Plan["Names"].index(Label)]
        Checks.append(f"_Pyceler_Labels_OK({F}, {A}, {V}, V0)")
        Signature += f", bint F{Number}, const _Pyceler_S32[:] A{Number}, _Pyceler_S32 L{Number}"
        Pass += f", F{Number}, A{Number}, L{Number}"
        Call.extend([F, f"({A} if {F} else None)", f"({V} if {F} else 0)"])
        Tests.extend([f"    if F{Number} and A{Number}[K] != L{Number}:", "        return 0"])
    Item, Run = f"_Pyceler_Inlier_{Line}", f"_Pyceler_Inliers_{Line}"
    Lines = ["@_Pyceler_Bounds(False)", "@_Pyceler_Wrap(False)", f"cdef inline int {Item}({Signature}, Py_ssize_t I) noexcept nogil:",
             "    cdef Py_ssize_t K = " + ("Rem[I]" if Indirect else "I"), "    cdef volatile double DX, DY, PX, PY, Distance", *Tests,
             "    DX = <double>Points[K, 0] - Ax", "    DY = <double>Points[K, 1] - Ay", "    PX = DX * Nx", "    PY = DY * Ny",
             "    Distance = PX + PY", "    if Distance < 0:", "        Distance = -Distance", "    return Distance <= Limit", "",
             f"cdef Py_ssize_t {Run}({Signature}, bint Threaded):", "    cdef Py_ssize_t I, Count = 0",
             "    cdef Py_ssize_t Size = " + ("Rem.shape[0]" if Indirect else "Points.shape[0]")]
    if Parallel:
        Lines.extend(["    if Threaded:", "        for I in _Pyceler_Prange(Size, schedule='static', nogil=True):",
                      f"            Count += {Item}({Pass}, I)", "        return Count"])
    Lines.extend(["    with nogil:", "        for I in range(Size):", f"            Count += {Item}({Pass}, I)", "    return Count", "",
                  f"cdef object _Pyceler_Special_{Line}({', '.join('object ' + V for V in Variables)}, object Baseline, bint Allow_Threads):"])
    Checks.insert(0, f"_Pyceler_Points_OK(V0, {Call[1]}, {Indirect}, ({', '.join(Coeff)},), Baseline)")
    if Plan["Named_Size"]:
        Lines.append("    import builtins as _Pyceler_B")
        Checks.append(f"_Pyceler_B.type({Variables[-1]}) is _Pyceler_B.int and {Variables[-1]} == {'Indices' if Indirect else 'V0'}.shape[0]")
    if Indirect:
        Lines.append("    Indices = _Pyceler_Indices(V1)")
    Lines.extend(["    if not (" + " and ".join(Checks) + "):", f"        return Baseline({', '.join(Variables)})"])
    Lines.extend(_Thread_Guard(Parallel))
    Call.append("Threaded")
    Lines.extend(["    if V0.itemsize == 4:", f"        return {Run}[float]({', '.join(Call)})", f"    return {Run}[double]({', '.join(Call)})"])
    return "\n".join(Lines)
