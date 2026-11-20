import ast
# Prove numeric fill spans and emit a guarded native fill implementation.
def _Affine(Node, Index):
    if isinstance(Node, ast.Name):
        return (1, "0") if Node.id == Index else (0, f"Namespace[{Node.id!r}]")
    if isinstance(Node, ast.Constant) and type(Node.value) is int and abs(Node.value) <= 64:
        return 0, str(Node.value)
    if isinstance(Node, ast.BinOp) and isinstance(Node.op, (ast.Add, ast.Sub)):
        Left, Right = _Affine(Node.left, Index), _Affine(Node.right, Index)
        if Left is not None and Right is not None:
            Sign = 1 if isinstance(Node.op, ast.Add) else -1
            return Left[0] + Sign * Right[0], f"({Left[1]} {'+' if Sign == 1 else '-'} {Right[1]})"
    return None

def _Fill_Plan(Plan):
    Body = Plan["Statements"]
    if len(Body) != 1 or not isinstance(Body[0], ast.Assign) or len(Body[0].targets) != 1:
        return None
    Node, Target = Body[0], Body[0].targets[0]
    if not isinstance(Target, ast.Subscript) or not isinstance(Target.value, ast.Name) or len(Plan["Buffers"]) != 1 or Plan["Buffers"][Target.value.id][1] != 1:
        return None
    if not isinstance(Node.value, ast.Constant) or type(Node.value.value) not in (bool, int) or not -5 <= Node.value.value <= 256:
        return None
    Offset = _Affine(Target.slice, Plan["Index"])
    if Offset is None or abs(Offset[0]) > 64:
        return None
    return Target.value.id, Offset, Node.value.value

def _Fill_Kernel(Plan, Line):
    Fill = _Fill_Plan(Plan)
    if Fill is None:
        return ""
    Name, (Scale, Offset), Value = Fill
    Numeric, Prefix = f"_Pyceler_Numeric_{Line}_", f"_Pyceler_Fast_{Line}_"
    Lines = [f"from cpython.list cimport PyList_GetItem as {Numeric}Borrow, PyList_SetItem as {Numeric}Put", f"from cpython.ref cimport Py_INCREF as {Numeric}Own", f"from cpython.object cimport PyObject as {Numeric}Object", f"cdef object {Numeric}Fill(dict Namespace, object Span, object Policy, object Whole):", "    import builtins as B", "    cdef list Output", "    cdef object Previous, Result, Item, Fill_Value", f"    cdef {Numeric}Object* Borrowed", "    cdef Py_ssize_t Index", "    cdef Py_ssize_t Position, Cursor, Last, Step, Length, Count", "    cdef long long Offset, First, Final", f"    global {Prefix}Native_Elements, {Prefix}Last_Team", "    if B.type(Span) is not B.range or not -1125899906842624 <= Span.start <= 1125899906842624 or not -1125899906842624 <= Span.stop <= 1125899906842624 or not -1125899906842624 <= Span.step <= 1125899906842624 or B.len(Span) < 2:", "        return None", f"    if not {Numeric}List(Namespace.get({Name!r})):", "        return None"]
    for Input in Plan["Inputs"]:
        Lines.extend([f"    Item = Namespace.get({Input!r})", f"    if not {Numeric}Integer(Item) or not -1125899906842624 <= Item <= 1125899906842624:", "        return None"])
    Lines.extend([f"    Previous = Namespace.get({Plan['Index']!r})", f"    if not ({Numeric}Integer(Previous) or {Numeric}Float(Previous) or {Numeric}Boolean(Previous) or Previous is None):", "        return None", f"    Output = Namespace[{Name!r}]", "    Length, Count, Last, Step = B.len(Output), B.len(Span), Span[-1], Span.step", f"    Item = {Offset}", "    if not -1125899906842624 <= Item <= 1125899906842624:", "        return None", "    Offset = Item", f"    First, Final = Span.start * {Scale} + Offset, Last * {Scale} + Offset", "    if First < -Length or First >= Length or Final < -Length or Final >= Length:", "        return None", "    Result = (Span[-1],)", f"    Fill_Value = {Value!r}", "    Cursor = Span.start", "    for Position in range(Count):", f"        Index = Cursor * {Scale} + Offset", "        if Index < 0:", "            Index += Length", f"        Borrowed = {Numeric}Borrow(Output, Index)", f"        if not ({Numeric}Integer(<object>Borrowed) or {Numeric}Float(<object>Borrowed) or {Numeric}Boolean(<object>Borrowed) or <object>Borrowed is None):", "            return None", "        Cursor += Step", "    Cursor = Span.start", "    for Position in range(Count):", f"        Index = Cursor * {Scale} + Offset", "        if Index < 0:", "            Index += Length", f"        {Numeric}Own(Fill_Value)", f"        {Numeric}Put(Output, Index, Fill_Value)", "        Cursor += Step", f"    Namespace[{Plan['Index']!r}] = Result[0]", f"    {Prefix}Native_Elements += Count", f"    {Prefix}Last_Team = 1", "    _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)", "    return Result"])
    return "\n".join(Lines) + "\n"
