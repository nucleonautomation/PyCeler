cdef list _Dispatch_Parallel_Block(list Lines, str Prefix):
    Result = []
    Position = 0
    while Position < len(Lines):
        Line = Lines[Position]
        Stripped = Line.lstrip()
        if not Stripped.startswith("for ") or Prefix + "Prange(" not in Stripped:
            Result.append(Line)
            Position += 1
            continue
        Indent = Line[:len(Line) - len(Stripped)]
        Loop = ast.parse(Stripped + "\n    pass").body[0]
        First = "0" if len(Loop.iter.args) == 1 else ast.unparse(Loop.iter.args[0])
        Index = ast.unparse(Loop.target)
        End = Position + 1
        while End < len(Lines) and (not Lines[End].strip() or len(Lines[End]) - len(Lines[End].lstrip()) > len(Indent)):
            End += 1
        Body = Lines[Position + 1:End]
        Result.extend([Indent + f"if {Prefix}Dispatch_Enabled:", Indent + f"    {Prefix}Observed_Team[0] = 0", "    " + Line,
                       Indent + f"        if {Index} == {First}:", Indent + f"            {Prefix}Observed_Team[0] = {Prefix}Reduction_Team()"])
        Result.extend("    " + Value for Value in Body)
        Result.extend([Indent + f"    {Prefix}Dispatch_Event('Execution', 'native_parallel', {Prefix}Observed_Team[0])", Indent + "else:", "    " + Line])
        Result.extend("    " + Value for Value in Body)
        Position = End
    return Result

cdef list _Dispatch_Function(list Lines, str Name, str Prefix):
    Signature = Lines[0]
    if " nogil" in Signature or Name.startswith(Prefix + "Dispatch_"):
        return Lines
    Parallel = any(Prefix + "Prange(" in Line for Line in Lines)
    Native_Run = not Name.startswith(Prefix + 'Module_Run_') and bool(re.search(r"(?:^|_)(?:Run|Reduction_Serial|Inliers|Best_Rows)_\d+(?:_Team_\d+)?$", Name[len(Prefix):]))
    Scalar = bool(re.fullmatch(re.escape(Prefix) + r"Scalar_(?:Region_)?\d+(?:_Team_\d+)?", Name))
    Boolean_Guard = bool(re.fullmatch(re.escape(Prefix) + r"(?:Clear(?:_Team_\d+)?|Map_\d+(?:_Team_\d+)?)", Name))
    Region = Name.startswith(Prefix + "Scalar_Region_")
    Result = [Signature]
    if Parallel:
        Result.append(f"    cdef int {Prefix}Observed_Team[1]")
    Entered = False
    for Line in Lines[1:]:
        Stripped = Line.lstrip()
        Indent = Line[:len(Line) - len(Stripped)]
        if Native_Run and not Entered and Stripped and not Stripped.startswith(("cdef ", "global ")):
            Result.append(f"    {Prefix}Dispatch_Event('Execution', 'native_serial', 1)")
            Entered = True
        if Stripped.startswith("return Baseline(") or Boolean_Guard and Stripped == "return False" or Region and Stripped == "return None":
            Result.append(Indent + f"{Prefix}Dispatch_Event('Execution', 'python_fallback', 0)")
        if Scalar and Stripped == "with nogil:":
            Result.append(Indent + f"{Prefix}Dispatch_Event('Execution', 'native_serial', 1)")
        if Name.startswith(Prefix + "Clear") and Stripped.startswith("Data = "):
            Result.append(Indent + f"{Prefix}Dispatch_Event('Execution', 'native_serial', 1)")
        if Name in (Prefix + "Copy_Span", Prefix + "Zero_Span") and Stripped.startswith("Offset, Length = "):
            Result.append(Indent + f"{Prefix}Dispatch_Event('Execution', 'native_serial', 1)")
        if Name == Prefix + "Copy_Span" and Stripped.startswith("Start, Length = "):
            Result.append(Indent + f"{Prefix}Dispatch_Event('Execution', 'native_serial', 1)")
        if Name == Prefix + "Copy_Bytes" and Stripped == "Input_View = Source":
            Result.append(Indent + f"{Prefix}Dispatch_Event('Execution', 'native_serial', 1)")
        if Name.startswith(Prefix + "Special_") and Stripped.startswith("while ") and not Entered:
            Result.append(Indent + f"{Prefix}Dispatch_Event('Execution', 'native_serial', 1)")
            Entered = True
        if Boolean_Guard and Stripped == "return True" and Result and Result[-1].strip() in ("if Output.size == 0:", "if Size == 0:"):
            Result.append(Indent + f"{Prefix}Dispatch_Event('Execution', 'native_serial', 1)")
        Result.append(Line)
    return _Dispatch_Parallel_Block(Result, Prefix) if Parallel else Result

cdef tuple _Dispatch_Instrument(str Source, str Native, str Prefix):
    Source_Lines = []
    for Line in Source.splitlines():
        Stripped = Line.lstrip()
        if Stripped.startswith("return " + Prefix + "Original_"):
            Source_Lines.append(Line[:len(Line) - len(Stripped)] + f"{Prefix}Dispatch_Event('Execution', 'python_fallback', 0)")
        Source_Lines.append(Line)
    Lines = Native.splitlines()
    Result = []
    Position = 0
    Pattern = re.compile(r"^cdef (?:inline )?\w+ (" + re.escape(Prefix) + r"\w+)\(.*\).*:\s*$")
    while Position < len(Lines):
        Match = Pattern.match(Lines[Position])
        if Match is None:
            Result.append(Lines[Position])
            Position += 1
            continue
        End = Position + 1
        while End < len(Lines) and (not Lines[End].strip() or Lines[End][:1].isspace()):
            End += 1
        Result.extend(_Dispatch_Function(Lines[Position:End], Match.group(1), Prefix))
        Position = End
    Runtime = _Resource("Dispatch_Runtime.pxi.in").replace("_Pyceler_", Prefix)
    return "\n".join(Source_Lines), Runtime + "\n" + "\n".join(Result)
