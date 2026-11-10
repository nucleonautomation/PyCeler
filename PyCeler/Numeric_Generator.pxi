cdef str _Median_Kernel(dict Plan, int Line, bint Parallel):
    Row = f"_Pyceler_Median_Row_{Line}"
    Run = f"_Pyceler_Median_Run_{Line}"
    Views = "const _Pyceler_Value[:, ::1] Input, _Pyceler_Value[:, ::1] Output"
    Lines = ["@_Pyceler_Bounds(False)", "@_Pyceler_Wrap(False)", f"cdef void {Row}({Views}, Py_ssize_t Row) noexcept nogil:",
             "    cdef _Pyceler_Value Values[9]", "    cdef _Pyceler_Value Value", "    cdef Py_ssize_t Column, Y, X, Count, Index, Position, Y0, Y1, X0, X1",
             "    Y0 = Row - 1 if Row else 0", "    Y1 = Row + 2 if Row < Input.shape[0] - 1 else Input.shape[0]",
             "    for Column in range(Input.shape[1]):", "        X0 = Column - 1 if Column else 0",
             "        X1 = Column + 2 if Column < Input.shape[1] - 1 else Input.shape[1]", "        Count = 0",
             "        for Y in range(Y0, Y1):", "            for X in range(X0, X1):", "                Values[Count] = Input[Y, X]", "                Count += 1",
             "        for Index in range(1, Count):", "            Value = Values[Index]", "            Position = Index",
             "            while Position > 0 and Values[Position - 1] > Value:", "                Values[Position] = Values[Position - 1]", "                Position -= 1",
             "            Values[Position] = Value", "        Output[Row, Column] = Values[Count // 2]", "",
             f"cdef void {Run}({Views}, bint Threaded):", "    cdef Py_ssize_t Row"]
    if Parallel:
        Lines.extend(["    if Threaded:", "        for Row in _Pyceler_Prange(Input.shape[0], schedule='static', nogil=True):",
                      f"            {Row}(Input, Output, Row)", "        return"])
    Lines.extend(["    with nogil:", "        for Row in range(Input.shape[0]):", f"            {Row}(Input, Output, Row)", "",
                  f"cdef object _Pyceler_Median_{Line}(object Input, object Output, object Baseline, bint Allow_Threads):",
                  "    import sys as S", "    import builtins as B", "    N = S.modules.get('numpy')",
                  "    if not _Pyceler_Bindings(Baseline) or not _Pyceler_Array(Input, N, 2, True) or not _Pyceler_Array(Output, N, 2, True):", "        return Baseline(Input, Output)",
                  "    if Input.dtype.kind not in ('i', 'u') or Output.dtype != Input.dtype or Input.shape != Output.shape or not Output.flags.writeable or N.may_share_memory(Input, Output):",
                  "        return Baseline(Input, Output)", "    Integer = Baseline.__globals__.get('int', Baseline.__builtins__.get('int'))",
                  "    if <void*>Integer != <void*>&_Pyceler_Int_Type:", "        return Baseline(Input, Output)"])
    for Name in ("min", "max"):
        Lines.extend([f"    Function = Baseline.__globals__.get('{Name}', Baseline.__builtins__.get('{Name}'))",
                      f"    if not _Pyceler_Is_C_Function(Function) or Function.__self__ is not B or Function.__name__ != '{Name}':", "        return Baseline(Input, Output)"])
    Lines.extend(_Thread_Guard(Parallel))
    for Keyword, Dtype, Native in (("if", "int8", "_Pyceler_Map_I8"), ("elif", "uint8", "_Pyceler_Map_U8"),
                                 ("elif", "int16", "_Pyceler_Map_I16"), ("elif", "uint16", "_Pyceler_Map_U16"),
                                 ("elif", "int32", "_Pyceler_I32"), ("elif", "int64", "_Pyceler_I64")):
        Lines.extend([f"    {Keyword} Input.dtype.name == '{Dtype}':", f"        {Run}[{Native}](Input, Output, Threaded)"])
    return "\n".join([*Lines, "    return Output"])
