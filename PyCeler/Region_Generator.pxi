cdef list _Thread_Guard(bint Parallel):
    if not Parallel:
        return ["    cdef bint Threaded = False"]
    return ["    from threading import current_thread, main_thread",
            "    cdef bint Threaded = Allow_Threads and current_thread() is main_thread() and not _Pyceler_In_Parallel()"]

cdef str _Stencil_Kernel(dict Plan, int Line, bint Parallel):
    H, W = Plan["Margins"]
    Row = f"_Pyceler_Filter_Row_{Line}"
    Run = f"_Pyceler_Filter_Run_{Line}"
    Views = "const _Pyceler_Pixel[:, :] A, const unsigned char[:, :] M, _Pyceler_S64[:, ::1] O"
    Lines = ["@_Pyceler_Bounds(False)", "@_Pyceler_Wrap(False)", f"cdef inline void {Row}({Views}, Py_ssize_t Y, Py_ssize_t Start, Py_ssize_t Stop) noexcept nogil:",
             "    cdef Py_ssize_t X", "    cdef _Pyceler_S64 Total", "    for X in range(Start, Stop):", "        Total = 0"]
    for DY, DX, Weight in Plan["Terms"]:
        Index = f"Y + ({DY}), X + ({DX})"
        Lines.extend([f"        if not M[{Index}]:", "            continue", f"        Total += (<_Pyceler_S64>A[{Index}]) * ({Weight})"])
    Divisor = Plan["Divisor"]
    Lines.extend([f"        O[Y, X] = Total // {Divisor}", "", f"cdef void {Run}({Views}, bint Threaded, bint Tiled, Py_ssize_t Tile_Size):", "    cdef Py_ssize_t Y, Y0, X0, Y1, X1",
                  "    if Tiled:", "        with nogil:", f"            Y0 = {H}", f"            while Y0 < A.shape[0] - {H}:",
                  f"                Y1 = Y0 + Tile_Size if Y0 + Tile_Size < A.shape[0] - {H} else A.shape[0] - {H}",
                  f"                X0 = {W}", f"                while X0 < A.shape[1] - {W}:",
                  f"                    X1 = X0 + Tile_Size if X0 + Tile_Size < A.shape[1] - {W} else A.shape[1] - {W}",
                  "                    for Y in range(Y0, Y1):", f"                        {Row}(A, M, O, Y, X0, X1)", "                    X0 = X1", "                Y0 = Y1", "        return"])
    if Parallel:
        Lines.extend(["    if Threaded:", f"        for Y in _Pyceler_Prange({H}, A.shape[0] - {H}, schedule='static', nogil=True):",
                      f"            {Row}(A, M, O, Y, {W}, A.shape[1] - {W})", "        return"])
    Lines.extend(["    with nogil:", f"        for Y in range({H}, A.shape[0] - {H}):", f"            {Row}(A, M, O, Y, {W}, A.shape[1] - {W})", "",
                  f"cdef object _Pyceler_Special_{Line}(object A, object M, object O, object H, object W, object Baseline, bint Allow_Threads, bint Tiled, Py_ssize_t Tile_Size):",
                  "    if not _Pyceler_Stencil_OK(A, M, O, H, W, Baseline):", "        return Baseline(A, M, O, H, W)", "    Mask = M.view('uint8')"])
    Lines.extend(_Thread_Guard(Parallel))
    for Keyword, Dtype, Native in (("if", "uint8", "_Pyceler_U8"), ("elif", "int16", "_Pyceler_S16"), ("elif", "uint16", "_Pyceler_U16"), ("elif", "int32", "_Pyceler_S32")):
        Lines.extend([f"    {Keyword} A.dtype.name == '{Dtype}':", f"        {Run}[{Native}](A, Mask, O, Threaded, Tiled, Tile_Size)"])
    Lines.append("    return O")
    return "\n".join(Lines)

cdef str _Count_Kernel(dict Plan, int Line, bint Parallel):
    Run = f"_Pyceler_Count_Run_{Line}"
    Op = Plan["Operator"]
    Lines = ["@_Pyceler_Bounds(False)", "@_Pyceler_Wrap(False)",
             f"cdef Py_ssize_t {Run}(const _Pyceler_Sample[:] A, _Pyceler_Sample Limit, bint Threaded):",
             "    cdef Py_ssize_t I, Total = 0"]
    if Parallel:
        Lines.extend(["    if Threaded:", "        for I in _Pyceler_Prange(A.shape[0], schedule='static', nogil=True):",
                      f"            if A[I] {Op} Limit:", "                Total += 1", "        return Total"])
    Lines.extend(["    with nogil:", "        for I in range(A.shape[0]):", f"            if A[I] {Op} Limit:", "                Total += 1", "    return Total", "",
                  f"cdef object _Pyceler_Special_{Line}(object A, object Limit, object Baseline, bint Allow_Threads):",
                  "    if not _Pyceler_Count_OK(A, Limit, Baseline):", "        return Baseline(A, Limit)"])
    Lines.extend(_Thread_Guard(Parallel))
    for Keyword, Dtype, Native in (("if", "int32", "_Pyceler_S32"), ("elif", "int64", "_Pyceler_S64"), ("elif", "float32", "float")):
        Lines.extend([f"    {Keyword} A.dtype.name == '{Dtype}':", f"        return {Run}[{Native}](A, Limit, Threaded)"])
    Lines.append(f"    return {Run}[double](A, Limit, Threaded)")
    return "\n".join(Lines)
