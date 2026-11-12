cdef str _Scalar_Region_Kernel(dict Plan, int Line):
    Names = Plan["Names"]
    Slots = Plan["Slots"]
    Floating = Plan.get("Floating", set())
    Integers = [Slot for Name, Slot in Slots.items() if Name not in Floating]
    Lines = [f"cdef object _Pyceler_Scalar_Region_{Line}({', '.join('object A' + str(Index) for Index in range(len(Names)))}):",
             "    import builtins as _Pyceler_Builtins", "    global _Pyceler_Region_Attempts", "    _Pyceler_Region_Attempts += 1", "    cdef unsigned int Ticks = 0",
             "    cdef _Pyceler_Int Cursor", "    cdef _Pyceler_Int " + ", ".join(Integers)]
    if Floating:
        Lines.append("    cdef double " + ", ".join(Slots[Name] for Name in Floating))
        Lines.extend(["    if _Pyceler_Scalar_Rounding() != _Pyceler_Scalar_Nearest:", "        return None"])
    for Index, Name in enumerate(Names):
        Argument = "A" + str(Index)
        if Name in Floating:
            Test = f"_Pyceler_Builtins.type({Argument}) is _Pyceler_Builtins.float or _Pyceler_Builtins.type({Argument}) is _Pyceler_Builtins.int and -9223372036854775808 <= {Argument} <= 9223372036854775807"
        else:
            Test = f"_Pyceler_Builtins.type({Argument}) is _Pyceler_Builtins.int and -9223372036854775808 <= {Argument} <= 9223372036854775807"
        Lines.extend([f"    if not ({Test}):", "        return None", f"    {Slots[Name]} = {Argument}"])
    Stop, Begin = (Slots[Name] for Name in Names[:2])
    Step = Plan["Step"] if Plan["Step"] is not None else Slots[Plan["Step_Name"]]
    if Plan["Step"] is None:
        Lines.extend([f"    if {Step} == 0:", "        return None"])
        Condition = f"({Step} > 0 and Cursor < {Stop}) or ({Step} < 0 and Cursor > {Stop})"
        Empty = f"({Step} > 0 and {Begin} >= {Stop}) or ({Step} < 0 and {Begin} <= {Stop})"
    else:
        Condition = f"Cursor {'<' if Step > 0 else '>'} {Stop}"
        Empty = f"{Begin} {'>=' if Step > 0 else '<='} {Stop}"
    Lines.extend([f"    if {Empty}:", "        return None", f"    Cursor = {Begin}", "    try:", "        with nogil:",
                  f"            while {Condition}:", f"                {Slots[Plan['Index']]} = Cursor", "                _Pyceler_Poll(&Ticks)"])
    Lines.extend(Plan["Lines"])
    Lines.extend([f"                Cursor = _Pyceler_Add(Cursor, {Step})", "    except (_Pyceler_Overflow, _Pyceler_Zero_Division):", "        return None",
                  "    return (" + ", ".join(Slots[Name] for Name in Plan["Outputs"]) + ",)"])
    return "\n".join(Lines)

cdef object _Scalar_Region_Minimum(object Table):
    if not isinstance(Table, dict):
        return None
    Minimum = None
    for Rows in Table.values():
        for Bound, Mode in Rows:
            if type(Bound) is not int or Bound < 0 or type(Mode) is not int or Mode not in (0, 1):
                return None
            if Mode and (Minimum is None or Bound < Minimum):
                Minimum = Bound
    return Minimum if Minimum else None

cdef str _Scalar_Region_Source(dict Plan, object Node, int Line, str Prefix, object Table):
    Original = ast.unparse(Node)
    Pure = "\n".join(ast.unparse(Statement) for Statement in Plan["Statements"])
    Range = f"{Prefix}Range_{Line}"
    Begin, Stop = f"{Prefix}Begin_{Line}", f"{Prefix}Stop_{Line}"
    Span, Size = f"{Prefix}Span_{Line}", f"{Prefix}Size_{Line}"
    Result = f"{Prefix}Result_{Line}"
    Candidate = f"{Prefix}Scalar_Region_{Line}"
    Arguments = ", ".join([Stop, Begin, *Plan["Inputs"], *([Span + ".step"] if Plan["Step"] is None else [])])
    Range_Arguments = ", ".join(ast.unparse(Argument) for Argument in Node.iter.args)
    Lines = [f"{Range} = {Prefix}Region_Binding()({Range_Arguments})", f"if {Prefix}Region_Range({Range}, {Plan['Step']}):",
             f"    for {Span}, {Size} in {Prefix}Region_Spans({Range}, {Plan['Period']!r}):",
             f"        {Begin}, {Stop} = {Span}.start, {Span}.stop"]
    if Table is None:
        Lines.append(f"        {Result} = {Candidate}({Arguments})")
    elif any(Mode for Rows in Table.values() for Size, Mode in Rows):
        Lines.append(f"        {Result} = {Candidate}({Arguments}) if {Prefix}Choose(({Size},), True, {Prefix}Table_{Line}) else None")
    else:
        return Original
    Lines.extend([f"        if {Result} is None:", f"            {Prefix}Region_Declined()",
                  f"            for {Plan['Index']} in {Span}:"])
    Lines.extend("                " + Text for Text in Pure.splitlines())
    Lines.extend(["        else:", "            " + ", ".join(Plan["Outputs"]) + f" = {Result}"])
    if Plan["Reporting"] is not None:
        Lines.extend("        " + Text for Text in ast.unparse(Plan["Reporting"]).splitlines())
    for Statement in Node.orelse:
        Lines.extend("    " + Text for Text in ast.unparse(Statement).splitlines())
    Fallback = copy.deepcopy(Node)
    Fallback.iter = ast.Name(id=Range, ctx=ast.Load())
    Minimum = _Scalar_Region_Minimum(Table)
    if Minimum is not None:
        Lines = [*Lines[:2], f"    if {Prefix}Region_Count({Range}) < {Minimum}:",
                 *("        " + Text for Text in ast.unparse(Fallback).splitlines()), "    else:", *("    " + Text for Text in Lines[2:])]
    Lines.append("else:")
    Lines.append(f"    {Prefix}Region_Declined()")
    Lines.extend("    " + Text for Text in ast.unparse(Fallback).splitlines())
    return "\n".join(Lines)
