cdef object _Module_Reduction_Plan(dict Region):
    Statements = Region["Statements"]
    if len(Statements) != 1 or not isinstance(Statements[0], ast.AugAssign):
        return None
    Statement = Statements[0]
    if not isinstance(Statement.target, ast.Name) or not isinstance(Statement.op, ast.Add):
        return None
    Target = Statement.target.id
    if any(isinstance(Part, ast.Name) and Part.id == Target for Part in ast.walk(Statement.value)):
        return None
    if Region.get("Floating") or type(Region.get("Step")) is not int:
        return None
    Stop, Begin = Region["Names"][:2]
    Inputs = tuple(Name for Name in Region["Inputs"] if Name != Target)
    Names = (Begin, Stop, *Inputs)
    Definition = ast.parse(f"def _Pyceler_Module_Sum({', '.join(Names)}):\n    {Target} = 0\n    for {Region['Index']} in range({Begin}, {Stop}, {Region['Step']}):\n        {Target} += 0\n    return {Target}\n").body[0]
    Definition.body[1].body = [copy.deepcopy(Statement)]
    Reduction = _Scalar_Parallel_Plan(Definition, dict(Names=Names))
    if Reduction is None:
        return None
    return dict(Target=Target, Inputs=Inputs, Names=Names, Step=Region["Step"], Reduction=Reduction, Index=Region["Index"])

cdef str _Module_Reduction_Kernel(dict Plan, int Line, bint Parallel):
    Slots = ["A" + str(Index) for Index in range(len(Plan["Names"]))]
    Term = f"_Pyceler_Module_Term_{Line}"
    Helper = f"_Pyceler_Module_Reduction_{Line}"
    Parameters = ", ".join([*("_Pyceler_Int " + Slot for Slot in Slots), "_Pyceler_Int Index"])
    Expression = _Scalar_Parallel_Expression(Plan["Reduction"]["Term"], [*Slots, "Index"])
    Call = Term + "(" + ", ".join([*Slots, f"Begin + Position * (<_Pyceler_Int>{Plan['Step']})"]) + ")"
    Lines = [f"cdef inline _Pyceler_Int {Term}({Parameters}) noexcept nogil:", "    return " + Expression, "",
             f"cdef object {Helper}(tuple Args, bint Allow_Threads, int Thread_Count):", "    cdef object Proof", "    cdef Py_ssize_t Position, Count",
             "    cdef _Pyceler_Int Begin, Result = 0", "    cdef _Pyceler_Int " + ", ".join(Slots),
             "    global _Pyceler_Module_Native, _Pyceler_Module_Parallel, _Pyceler_Module_Team"]
    if Parallel:
        Lines.append("    cdef int Team[1]")
    Lines.extend([f"    if len(Args) != {len(Slots)}:", "        return None", f"    Proof = _Pyceler_Reduction_Allowed(Args, {Plan['Reduction']!r})",
                  "    if Proof is None or Proof[1] > 1048576:", "        return None", "    if Proof[1] == 0:", "        return (0, None)",
                  "    Begin, Count = Proof", "    _Pyceler_Module_Native += 1", "    _Pyceler_Module_Team = 1"])
    Lines.extend(f"    {Slot} = Args[{Index}]" for Index, Slot in enumerate(Slots))
    if Parallel:
        Lines.extend(["    if Allow_Threads and not _Pyceler_In_Parallel():", "        Team[0] = 1",
                      "        for Position in _Pyceler_Prange(Count, nogil=True, schedule='static', num_threads=Thread_Count if Thread_Count > 0 else _Pyceler_Max_Threads()):",
                      "            if Position == 0:", "                Team[0] = _Pyceler_Reduction_Team()",
                      "            Result += " + Call, "        _Pyceler_Module_Parallel += 1", "        _Pyceler_Module_Team = Team[0]",
                      f"        return (Result, Begin + (Count - 1) * (<_Pyceler_Int>{Plan['Step']}))"])
    Lines.extend(["    _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)", "    with nogil:", "        for Position in range(Count):",
                  "            Result += " + Call, f"    return (Result, Begin + (Count - 1) * (<_Pyceler_Int>{Plan['Step']}))"])
    return "\n".join(Lines)
