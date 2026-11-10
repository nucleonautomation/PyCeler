cdef str _Structural_Value(tuple Recipe, dict Aliases):
    Kind = Recipe[0]
    if Kind == "array":
        return f"V{Recipe[1]}[Index]"
    if Kind == "scalar":
        return f"V{Recipe[1]}"
    if Kind == "literal":
        return f"(<_Pyceler_Value>({Recipe[1]}))"
    if Kind == "abs":
        Value = f"T{Aliases.get(Recipe[1], Recipe[1])}"
        return f"(-{Value} if {Value} < 0 else {Value})"
    return f"T{Aliases.get(Recipe[1], Recipe[1])} {Kind} T{Aliases.get(Recipe[2], Recipe[2])}"

cdef list _Structural_Item(dict Plan, str Name, str Parameters, list Actions, bint Optimized):
    Aliases, Seen, Stored, Lines = {}, {}, {}, []
    Invariant = set(Plan["Invariant"]) if Optimized else set()
    Temporary = len(Plan["Names"]) if Plan["Temporary"] else -1
    for Number in sorted(Invariant):
        Recipe = Plan["Nodes"][Number]
        Key = Recipe if Recipe[0] not in ("+", "-", "*") else (Recipe[0], Aliases.get(Recipe[1], Recipe[1]), Aliases.get(Recipe[2], Recipe[2]))
        if Recipe[0] == "abs":
            Key = ("abs", Aliases.get(Recipe[1], Recipe[1]))
        if Key in Seen:
            Aliases[Number] = Seen[Key]
        else:
            Seen[Key] = Number
    for Action in Actions:
        if Action[0] == "write":
            Slot, Number, Version = Action[1:]
            Number = Aliases.get(Number, Number)
            Stored[(Slot, Version)] = Number
            if not Optimized or Slot != Temporary:
                Lines.append(f"    V{Slot}[Index] = T{Number}")
            continue
        Number = Action[1]
        Recipe = Plan["Nodes"][Number]
        if Number in Invariant:
            continue
        if Optimized and Recipe[0] == "array" and Recipe[1] == Temporary and (Recipe[1], Recipe[2]) in Stored:
            Aliases[Number] = Stored[(Recipe[1], Recipe[2])]
            continue
        Key = Recipe if Recipe[0] not in ("+", "-", "*") else (Recipe[0], Aliases.get(Recipe[1], Recipe[1]), Aliases.get(Recipe[2], Recipe[2]))
        if Recipe[0] == "abs":
            Key = ("abs", Aliases.get(Recipe[1], Recipe[1]))
        if Optimized and Key in Seen:
            Aliases[Number] = Seen[Key]
            continue
        Seen[Key] = Number
        Lines.append(f"    T{Number} = {_Structural_Value(Recipe, Aliases)}")
    Locals = [Action[1] for Action in Actions if Action[0] == "value" and Action[1] not in Invariant and Action[1] not in Aliases]
    Extra = ", " + ", ".join(f"_Pyceler_Value T{Number}" for Number in sorted(Invariant)) if Invariant else ""
    Header = ["@_Pyceler_Bounds(False)", "@_Pyceler_Wrap(False)", f"cdef inline void {Name}({Parameters}, Py_ssize_t Index{Extra}) noexcept nogil:"]
    if Locals:
        Header.append("    cdef _Pyceler_Value " + ", ".join(f"T{Number}" for Number in Locals))
    return [*Header, *(Lines or ["    pass"]), ""]

include "Structural_Guards.pxi"

cdef str _Structural_Kernel(dict Plan, int Line, bint Parallel):
    Names = Plan["Names"]
    Arrays = tuple(Index for Index, Name in enumerate(Names) if Name in Plan["Arrays"])
    Scalars = tuple(Index for Index, Name in enumerate(Names) if Name in Plan["Scalars"])
    Outputs = tuple(Names.index(Name) for Name in Plan["Outputs"] if Name in Names)
    Destination = Names.index(Plan["Output"])
    Temporary = len(Names) if Plan["Temporary"] else None
    Slots = sorted((*Arrays, *Scalars, *((Temporary,) if Temporary is not None else ())))
    Declarations = []
    for Slot in Slots:
        if Slot in Scalars:
            Declarations.append(f"_Pyceler_Value V{Slot}")
        else:
            Modifier = "" if Slot in Outputs or Slot == Temporary else "const "
            Declarations.append(f"{Modifier}_Pyceler_Value[::1] V{Slot}")
    Parameters = ", ".join(Declarations)
    Arguments = ", ".join(f"V{Slot}" for Slot in Slots)
    Run = f"_Pyceler_Structure_Run_{Line}"
    Lines = []
    for Index, (Axes, Actions) in enumerate(Plan["Blocks"]):
        Lines.extend(_Structural_Item(Plan, f"{Run}_Original_{Index}", Parameters, Actions, False))
    Actions = [Action for Axes, Block in Plan["Blocks"] for Action in Block]
    Lines.extend(_Structural_Item(Plan, Run + "_Optimized", Parameters, Actions, True))
    Lines.extend([f"cdef void {Run}({Parameters}, Py_ssize_t Width, int Mode, bint Threaded):",
                  "    cdef Py_ssize_t Index, Row, Column", f"    cdef Py_ssize_t Size = V{Destination}.shape[0]"])
    if Plan["Invariant"]:
        Lines.append("    cdef _Pyceler_Value " + ", ".join(f"T{Number}" for Number in Plan["Invariant"]))
    Lines.extend(["    if Size == 0:", "        return", "    if Mode == 1:", "        with nogil:"])
    for Index, (Axes, Actions) in enumerate(Plan["Blocks"]):
        if Axes == (1, 0):
            Lines.extend(["            for Column in range(Width):", "                for Row in range(Size // Width):",
                          f"                    {Run}_Original_{Index}({Arguments}, Row * Width + Column)"])
        else:
            Lines.extend(["            for Index in range(Size):", f"                {Run}_Original_{Index}({Arguments}, Index)"])
    Lines.append("        return")
    for Number in Plan["Invariant"]:
        Lines.append(f"    T{Number} = {_Structural_Value(Plan['Nodes'][Number], {})}")
    Extra = ", " + ", ".join(f"T{Number}" for Number in Plan["Invariant"]) if Plan["Invariant"] else ""
    if Parallel:
        Lines.extend(["    if Threaded:", "        for Index in _Pyceler_Prange(Size, schedule='static', nogil=True):",
                      f"            {Run}_Optimized({Arguments}, Index{Extra})", "        return"])
    Lines.extend(["    with nogil:", "        for Index in range(Size):", f"            {Run}_Optimized({Arguments}, Index{Extra})", ""])
    Guard = f"_Pyceler_Structure_{Line}"
    Values = ", ".join(f"V{Index}" for Index in range(len(Names)))
    Lines.extend(_Structural_Guard_Code(Plan, Guard))
    Lines.extend([f"cdef object {Guard}({', '.join(f'object V{Index}' for Index in range(len(Names)))}, object Baseline, int Mode):",
                  f"    if not {Guard}_Allowed({Values}, Baseline):", f"        return Baseline({Values})",
                  "    cdef bint Threaded = False"])
    if Parallel:
        Lines.extend(["    from threading import current_thread, main_thread",
                      "    Threaded = Mode == 2 and current_thread() is main_thread() and not _Pyceler_In_Parallel()"])
    if Temporary is not None:
        Source = Plan["Allocation"][1]
        Lines.extend(["    if Mode == 1:", "        import sys as S", f"        V{Temporary} = S.modules['numpy'].empty_like(V{Source})",
                      "    else:", f"        V{Temporary} = V{Destination}"])
    Width = f"V{Destination}.shape[1]" if Plan["Dimensions"] == 2 else "1"
    Call = ", ".join(f"V{Slot}" if Slot in Scalars else f"V{Slot}.reshape(-1)" for Slot in Slots)
    for Keyword, Condition, Native in (("if", 'dtype.name == "int8"', "_Pyceler_Map_I8"), ("elif", 'dtype.name == "uint8"', "_Pyceler_Map_U8"),
                                     ("elif", 'dtype.name == "int16"', "_Pyceler_Map_I16"), ("elif", 'dtype.name == "uint16"', "_Pyceler_Map_U16"),
                                     ("elif", 'dtype.name == "int32"', "_Pyceler_I32"), ("elif", 'dtype.kind == "i"', "_Pyceler_I64"),
                                     ("elif", 'dtype.itemsize == 4', "float")):
        Lines.extend([f"    {Keyword} V{Destination}.{Condition}:", f"        {Run}[{Native}]({Call}, {Width}, Mode, Threaded)"])
    Result = "None" if Plan["Returns_None"] else f"V{Destination}"
    Lines.extend(["    else:", f"        {Run}[double]({Call}, {Width}, Mode, Threaded)", f"    return {Result}"])
    return "\n".join(Lines)
