cdef object _Literal_Int(object Node):
    if isinstance(Node, ast.Constant) and type(Node.value) is int:
        return Node.value
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.USub) and isinstance(Node.operand, ast.Constant) and type(Node.operand.value) is int:
        return -Node.operand.value
    return None

cdef object _Margin_Loop(object Node):
    if not isinstance(Node, ast.For) or Node.orelse or not isinstance(Node.target, ast.Name):
        return None
    Call = Node.iter
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or len(Call.args) != 2:
        return None
    Margin, End = _Literal_Int(Call.args[0]), Call.args[1]
    if Margin is None or not 0 <= Margin <= 64 or not isinstance(End, ast.BinOp) or not isinstance(End.op, ast.Sub) or not isinstance(End.left, ast.Name) or _Literal_Int(End.right) != Margin:
        return None
    return Node.target.id, End.left.id, Margin

cdef object _Offset_Index(object Expr, str Index):
    if _Name(Expr, Index):
        return 0
    if isinstance(Expr, ast.BinOp) and _Name(Expr.left, Index) and isinstance(Expr.op, (ast.Add, ast.Sub)):
        Value = _Literal_Int(Expr.right)
        if Value is not None:
            return Value if isinstance(Expr.op, ast.Add) else -Value
    return None

cdef object _Neighborhood_Cell(object Expr, str Row, str Column):
    if isinstance(Expr, ast.Subscript) and isinstance(Expr.value, ast.Name) and isinstance(Expr.slice, ast.Tuple) and len(Expr.slice.elts) == 2:
        Y = _Offset_Index(Expr.slice.elts[0], Row)
        X = _Offset_Index(Expr.slice.elts[1], Column)
        if Y is not None and X is not None:
            return Expr.value.id, Y, X
    return None

cdef object _Mask_Term(list Block, str Row, str Column, str Total):
    Check, Read, Add = Block
    if not isinstance(Check, ast.If) or Check.orelse or len(Check.body) != 1 or not isinstance(Check.body[0], ast.Continue) or not isinstance(Check.test, ast.UnaryOp) or not isinstance(Check.test.op, ast.Not):
        return None
    if not isinstance(Read, ast.Assign) or len(Read.targets) != 1 or not isinstance(Read.targets[0], ast.Name):
        return None
    Value = Read.targets[0].id
    Call = Read.value
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "int") or Call.keywords or len(Call.args) != 1:
        return None
    Mask, Source = _Neighborhood_Cell(Check.test.operand, Row, Column), _Neighborhood_Cell(Call.args[0], Row, Column)
    if Mask is None or Source is None or Mask[1:] != Source[1:]:
        return None
    if not isinstance(Add, ast.AugAssign) or not isinstance(Add.op, ast.Add) or not _Name(Add.target, Total):
        return None
    Expr = Add.value
    if not isinstance(Expr, ast.BinOp) or not isinstance(Expr.op, ast.Mult) or not _Name(Expr.right, Value):
        return None
    Weight = _Literal_Int(Expr.left)
    if Weight is not None:
        return Source[0], Mask[0], Value, Source[1], Source[2], Weight
    return None

cdef object _Stencil_Region(object Function, object Loop, set Bound):
    Vertical = _Margin_Loop(Loop)
    if not Vertical or len(Loop.body) != 1:
        return None
    Inner = Loop.body[0]
    Horizontal = _Margin_Loop(Inner)
    if not Horizontal:
        return None
    Row, Rows, H = Vertical
    Column, Columns, W = Horizontal
    Body = Inner.body
    if len(Body) < 5 or (len(Body) - 2) % 3 or len(Body) > 386:
        return None
    Init, Write = Body[0], Body[-1]
    if not isinstance(Init, ast.Assign) or len(Init.targets) != 1 or not isinstance(Init.targets[0], ast.Name) or not _Integer(Init.value, 0):
        return None
    Total = Init.targets[0].id
    if not isinstance(Write, ast.Assign) or len(Write.targets) != 1 or not isinstance(Write.value, ast.BinOp) or not isinstance(Write.value.op, ast.FloorDiv) or not _Name(Write.value.left, Total):
        return None
    Cell = _Neighborhood_Cell(Write.targets[0], Row, Column)
    Divisor = _Literal_Int(Write.value.right)
    if not Cell or Cell[1:] != (0, 0) or Divisor is None or not 0 < Divisor <= 2**31 - 1:
        return None
    Terms = [_Mask_Term(Body[Index:Index + 3], Row, Column, Total) for Index in range(1, len(Body) - 1, 3)]
    if any(Term is None for Term in Terms):
        return None
    Source, Mask, Value = Terms[0][:3]
    if any(Term[:3] != (Source, Mask, Value) or abs(Term[3]) > H or abs(Term[4]) > W for Term in Terms):
        return None
    if sum(abs(Term[5]) for Term in Terms) > 2**31 - 1:
        return None
    Names = (Source, Mask, Cell[0], Rows, Columns)
    Private = {Row, Column, Value, Total}
    if len(set(Names) | Private) != 9 or not set(Names) <= Bound:
        return None
    return dict(Kind="stencil", Label="masked neighborhood filter", Names=Names, Output=Cell[0], Key=Source, Start=Loop.lineno,
                Region=True, Private=Private, Probe=_Region_Function(Function, [Loop], Names, Cell[0]), Loops=[Loop, Inner],
                Margins=(H, W), Terms=[Term[3:] for Term in Terms], Divisor=Divisor)

cdef object _Count_Region(object Function, object Loop, list Before, set Bound):
    if not Before or not isinstance(Loop.target, ast.Name) or Loop.orelse or len(Loop.body) != 1 or any(isinstance(Node, (ast.Try, ast.With, getattr(ast, "TryStar", ast.Try))) for Node in ast.walk(Function)):
        return None
    Bounds = _Bounds(Loop.iter)
    Check = Loop.body[0]
    if not Bounds or Bounds[1] or not isinstance(Check, ast.If) or Check.orelse or len(Check.body) != 1:
        return None
    Expr, Add = Check.test, Check.body[0]
    if not isinstance(Expr, ast.Compare) or len(Expr.ops) != 1 or not isinstance(Expr.comparators[0], ast.Name):
        return None
    Operators = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
    Op = Operators.get(type(Expr.ops[0]))
    Source, Index, Limit = Bounds[0], Loop.target.id, Expr.comparators[0].id
    if not Op or not _Element(Expr.left, Source, Index) or not isinstance(Add, ast.AugAssign) or not isinstance(Add.op, ast.Add) or not isinstance(Add.target, ast.Name) or not _Integer(Add.value, 1):
        return None
    Count = Add.target.id
    Init = Before[-1]
    if not isinstance(Init, ast.Assign) or len(Init.targets) != 1 or not _Name(Init.targets[0], Count) or not _Integer(Init.value, 0):
        return None
    Names = (Source, Limit)
    if len({Source, Limit, Count, Index}) != 4 or not set(Names) <= Bound:
        return None
    return dict(Kind="count", Label="threshold count", Names=Names, Output=Source, Key=Source, Result=Count, Start=Loop.lineno,
                Region=True, Private={Index}, Probe=_Region_Function(Function, [Init, Loop], Names, Count), Loops=[Loop], Operator=Op)

cdef object _Special_Region(object Function, object Loop, list Before, set Bound):
    Plan = _Stencil_Region(Function, Loop, Bound)
    if Plan is None:
        Plan = _Byte_Span_Region(Function, Loop, Bound)
    if Plan is None:
        Plan = _Projection_Region(Function, Loop, Before, Bound)
    if Plan is None:
        Plan = _Row_Selection(Function, Loop, Bound)
    return Plan if Plan is not None else _Count_Region(Function, Loop, Before, Bound)

cdef object _Byte_Span_Region(object Function, object Loop, set Bound):
    if not isinstance(Loop.target, ast.Name) or Loop.orelse or len(Loop.body) != 1:
        return None
    I = Loop.target.id
    Call, Write = Loop.iter, Loop.body[0]
    if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or not isinstance(Write, ast.Assign) or len(Write.targets) != 1:
        return None
    Target, Read = Write.targets[0], Write.value
    if not isinstance(Target, ast.Subscript) or not isinstance(Target.value, ast.Name) or not _Name(Target.slice, I):
        return None
    Output = Target.value.id
    if len(Call.args) == 1 and isinstance(Call.args[0], ast.Name) and isinstance(Read, ast.Subscript) and isinstance(Read.value, ast.Name):
        Cell = Read.slice
        if not isinstance(Cell, ast.BinOp) or not isinstance(Cell.op, ast.Add) or not isinstance(Cell.left, ast.Name) or not _Name(Cell.right, I):
            return None
        Names = (Read.value.id, Output, Cell.left.id, Call.args[0].id)
        Mode = "copy"
    elif len(Call.args) == 2 and isinstance(Call.args[0], ast.Name) and _Integer(Read, 0):
        End = Call.args[1]
        if isinstance(End, ast.Name):
            Names = (Output, Call.args[0].id, End.id)
        elif isinstance(End, ast.Call) and _Name(End.func, "len") and not End.keywords and len(End.args) == 1 and _Name(End.args[0], Output):
            Names = (Output, Call.args[0].id)
        else:
            return None
        Mode = "fill"
    else:
        return None
    if len(set(Names) | {I}) != len(Names) + 1 or not set(Names) <= Bound:
        return None
    return dict(Kind="span", Mode=Mode, Label="byte buffer " + Mode, Names=Names, Output=Output, Key=Output, Start=Loop.lineno,
                Region=True, Private={I}, Probe=_Region_Function(Function, [Loop], Names, Output), Loops=[Loop])
