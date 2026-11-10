cdef str _Map_Kernel(dict Plan, int Line, bint Parallel, bint Measured=False):
    Names = Plan.get("Kernel_Names", Plan["Names"])
    Destination = Names.index(Plan["Output"])
    Arrays = tuple(Index for Index, Name in enumerate(Names) if Name in Plan["Arrays"])
    Scalars = tuple(Index for Index, Name in enumerate(Names) if Name in Plan["Scalars"])
    Variables = [f"V{Index}" for Index in range(len(Names))]
    Arguments = ", ".join(Variables)
    Declarations = []
    Views = []
    for Index, Variable in enumerate(Variables):
        if Index in Scalars:
            Declarations.append("_Pyceler_Value " + Variable)
            Views.append(Variable)
        else:
            Modifier = "" if Index == Destination else "const "
            Declarations.append(Modifier + "_Pyceler_Value[::1] " + Variable)
            Views.append(Variable + ".reshape(-1)")
    Parameters = ", ".join(Declarations)
    Typed_Call = ", ".join(Views)
    Item = f"_Pyceler_Item_{Line}"
    Run = f"_Pyceler_Run_{Line}"
    Guard = f"_Pyceler_Map_{Line}"
    Checks = (Destination, Arrays, Scalars, tuple(sorted(Plan["Reads"])), len(Plan["Indices"]),
              tuple(Plan["Arithmetic"]), Plan["Comparison"], tuple(Plan["Float_Literals"]), tuple(sorted(Plan["Integer_Literals"])))
    Check_Args = ", ".join(repr(Value) for Value in Checks)
    Lines = ["@_Pyceler_Bounds(False)", "@_Pyceler_Wrap(False)",
             f"cdef inline void {Item}({Parameters}, Py_ssize_t Index) noexcept nogil:"]
    Lines.extend("    " + Statement for Statement in Plan["Lines"])
    Lines.extend(["", f"cdef void {Run}({Parameters}, bint Threaded):", "    cdef Py_ssize_t Index",
                  f"    cdef Py_ssize_t Count = V{Destination}.shape[0]"])
    if Parallel:
        Lines.extend(["    if Threaded:", "        for Index in _Pyceler_Prange(Count, nogil=True, schedule='static'):",
                      f"            {Item}({Arguments}, Index)", "        return"])
    Lines.extend(["    with nogil:", "        for Index from 0 <= Index < Count:", f"            {Item}({Arguments}, Index)",
                  "", f"cdef bint {Guard}({', '.join('object ' + Variable for Variable in Variables)}, object Baseline, bint Allow_Threads) except -1:",
                  *([f"    if _Pyceler_Copy_Bytes(V{Plan['Byte_Copy'][0]}, V{Destination}, Baseline):", "        return True"] if "Byte_Copy" in Plan else []),
                  f"    if not _Pyceler_Map_Allowed(({Arguments},), {Check_Args}, Baseline):", "        return False",
                  f"    Output = V{Destination}", "    if Output.size == 0:", "        return True", "    cdef bint Threaded = False"])
    if Parallel:
        Lines.extend(["    if Allow_Threads:" if Measured else "    if Allow_Threads and Output.nbytes > 65536:", "        from threading import current_thread, main_thread",
                      "        Threaded = current_thread() is main_thread() and not _Pyceler_In_Parallel()"])
    for Keyword, Condition, Dtype in (("if", 'Output.dtype.name == "int8"', "_Pyceler_Map_I8"),
                                      ("elif", 'Output.dtype.name == "uint8"', "_Pyceler_Map_U8"),
                                      ("elif", 'Output.dtype.name == "int16"', "_Pyceler_Map_I16"),
                                      ("elif", 'Output.dtype.name == "uint16"', "_Pyceler_Map_U16"),
                                      ("elif", 'Output.dtype.kind == "i" and Output.itemsize == 4', "_Pyceler_I32"),
                                      ("elif", 'Output.dtype.kind == "i"', "_Pyceler_I64"),
                                      ("elif", "Output.itemsize == 4", "float")):
        Lines.extend([f"    {Keyword} {Condition}:", f"        {Run}[{Dtype}]({Typed_Call}, Threaded)"])
    Lines.extend(["    else:", f"        {Run}[double]({Typed_Call}, Threaded)", "    return True"])
    return "\n".join(Lines)
