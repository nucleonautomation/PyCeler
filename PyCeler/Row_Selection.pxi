cdef object _Row_Selection(object Function, object Loop, set Bound):
    if len(Loop.body) != 3 or not isinstance(Loop.target, ast.Name):
        return None
    Init, Inner, Write = Loop.body
    if not isinstance(Init, ast.Assign) or len(Init.targets) != 1 or not isinstance(Init.targets[0], ast.Name):
        return None
    if not isinstance(Inner, ast.For) or not isinstance(Inner.target, ast.Name) or len(Inner.body) != 1 or not isinstance(Inner.body[0], ast.If):
        return None
    Row, Column, Best = Loop.target.id, Inner.target.id, Init.targets[0].id
    Test = Inner.body[0].test
    if not isinstance(Test, ast.Compare) or len(Test.ops) != 1 or not isinstance(Test.ops[0], (ast.Lt, ast.Gt)):
        return None
    Source = _Map_Cell(Test.left, (Row, Column))
    Output = _Map_Cell(Write.targets[0], (Row,)) if isinstance(Write, ast.Assign) and len(Write.targets) == 1 else None
    if not Source or not Output:
        return None
    Names, Bounds, Named = [Source, Output], [], []
    for Axis, Nest in enumerate((Loop, Inner)):
        Call = Nest.iter
        if not isinstance(Call, ast.Call) or len(Call.args) != Axis + 1:
            return None
        Limit = Call.args[-1]
        if isinstance(Limit, ast.Name):
            Names.append(Limit.id)
            Named.append(Axis)
        elif _Axis_Source(Limit, Axis, (), {}) != Source or not isinstance(Limit, ast.Subscript):
            return None
        Bounds.append(ast.unparse(Limit))
    Temps = {Row, Column, Best}
    if len(set(Names) | Temps) != len(Names) + 3 or not set(Names) <= Bound:
        return None
    Operator = "<" if isinstance(Test.ops[0], ast.Lt) else ">"
    Expected = (f"for {Row} in range({Bounds[0]}):\n    {Best} = 0\n    for {Column} in range(1, {Bounds[1]}):\n"
                f"        if {Source}[{Row}, {Column}] {Operator} {Source}[{Row}, {Best}]:\n            {Best} = {Column}\n    {Output}[{Row}] = {Best}")
    if ast.dump(Loop) != ast.dump(ast.parse(Expected).body[0]):
        return None
    return dict(Kind="row_selection", Label="row-wise best index", Names=tuple(Names), Output=Output, Key=Source,
                Start=Loop.lineno, Region=True, Private=Temps, Probe=_Region_Function(Function, [Loop], tuple(Names), Output),
                Loops=[Loop, Inner], Operator=Operator, Named=Named)

cdef str _Row_Selection_Kernel(dict Plan, int Line, bint Parallel):
    Item, Run = f"_Pyceler_Best_{Line}", f"_Pyceler_Best_Rows_{Line}"
    Extra = [f"V{Axis}" for Axis in Plan["Named"]]
    Args = ["A", "O", *Extra]
    Checks = ["_Pyceler_Rows_OK(A, O, Baseline)"] + [f"_Pyceler_B.type(V{Axis}) is _Pyceler_B.int and V{Axis} == A.shape[{Axis}]" for Axis in Plan["Named"]]
    Lines = ["@_Pyceler_Bounds(False)", "@_Pyceler_Wrap(False)", f"cdef inline void {Item}(const _Pyceler_Sample[:, :] A, unsigned char[::1] O, Py_ssize_t R) noexcept nogil:",
             "    cdef Py_ssize_t C, Best = 0", "    for C in range(1, A.shape[1]):",
             f"        if A[R, C] {Plan['Operator']} A[R, Best]:", "            Best = C", "    O[R] = <unsigned char>Best", "",
             f"cdef void {Run}(const _Pyceler_Sample[:, :] A, unsigned char[::1] O, bint Threaded):", "    cdef Py_ssize_t R"]
    if Parallel:
        Lines.extend(["    if Threaded:", "        for R in _Pyceler_Prange(A.shape[0], schedule='static', nogil=True):", f"            {Item}(A, O, R)", "        return"])
    Lines.extend(["    with nogil:", "        for R in range(A.shape[0]):", f"            {Item}(A, O, R)", "",
                  f"cdef object _Pyceler_Special_{Line}({', '.join('object ' + V for V in Args)}, object Baseline, bint Allow_Threads):",
                  "    import builtins as _Pyceler_B", "    if not (" + " and ".join(Checks) + "):",
                  f"        return Baseline({', '.join(Args)})"])
    Lines.extend(_Thread_Guard(Parallel))
    for Keyword, Dtype, Native in (("if", "int32", "_Pyceler_S32"), ("elif", "int64", "_Pyceler_S64"), ("elif", "float32", "float"), ("elif", "float64", "double")):
        Lines.extend([f"    {Keyword} A.dtype.name == '{Dtype}':", f"        {Run}[{Native}](A, O, Threaded)"])
    Lines.append("    return O")
    return "\n".join(Lines)
