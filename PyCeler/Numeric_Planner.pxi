cdef str _Median_Pattern = """def Median(Input, Output):
    Height, Width = Input.shape
    for Row in range(Height):
        for Column in range(Width):
            Values = []
            for Y in range(max(0, Row - 1), min(Height, Row + 2)):
                for X in range(max(0, Column - 1), min(Width, Column + 2)):
                    Values.append(int(Input[Y, X]))
            Values.sort()
            Output[Row, Column] = Values[len(Values) // 2]
    return Output
"""

cdef bint _Numeric_Match(object Pattern, object Actual, dict Names):
    if type(Pattern) is not type(Actual):
        return False
    if isinstance(Pattern, (ast.Name, ast.arg)):
        Left = Pattern.id if isinstance(Pattern, ast.Name) else Pattern.arg
        Right = Actual.id if isinstance(Actual, ast.Name) else Actual.arg
        Reserved = {"range", "min", "max", "len", "int"}
        if Left in Reserved:
            return Left == Right
        if Left not in Names:
            if Right in Reserved or Right in Names.values():
                return False
            Names[Left] = Right
        return Names[Left] == Right
    if isinstance(Pattern, ast.AST):
        for Field, Value in ast.iter_fields(Pattern):
            if isinstance(Pattern, ast.FunctionDef) and Field in ("name", "returns", "type_comment"):
                continue
            if not _Numeric_Match(Value, getattr(Actual, Field, None), Names):
                return False
        return True
    if isinstance(Pattern, list):
        return len(Pattern) == len(Actual) and all(_Numeric_Match(Left, Right, Names) for Left, Right in zip(Pattern, Actual))
    return Pattern == Actual

cdef void _Numeric_Plans(object Tree, list Findings, dict Edits, bint Parallel, bint Elide_Temporaries) except *:
    Pattern = ast.parse(_Median_Pattern).body[0]
    for Function in Tree.body:
        if not isinstance(Function, ast.FunctionDef) or Function.decorator_list:
            continue
        Names = {}
        if not _Numeric_Match(Pattern, Function, Names):
            continue
        Loops = [Node for Node in ast.walk(Function) if isinstance(Node, ast.For)]
        Lines = {Node.lineno for Node in Loops}
        for Index, Finding in enumerate(Findings):
            if Finding.Line in Lines:
                Findings[Index] = replace(Finding, Classification="Clipped_Integer_Median",
                    Change="Guarded clipped median with row-local scratch" if Elide_Temporaries else "Keep original loop",
                    Reason="A clipped 3x3 integer neighborhood selects its upper middle value. Removing temporary lists requires Elide_Temporaries=True; output storage must be disjoint.")
        if not Elide_Temporaries:
            continue
        for Line in [Line for Line, Edit in Edits.items() if Edit[2] is Function]:
            del Edits[Line]
        Arguments = (Names["Input"], Names["Output"])
        Plan = dict(Kind="median", Names=Arguments, Arrays=set(Arguments), Output=Arguments[1], Indices=(Names["Row"], Names["Column"]),
                    Start=Function.body[0].lineno, Loops=Loops, Transformations=["clipped_median", "row_scratch", "temporary_elimination"])
        Edits[Loops[0].lineno] = (Arguments, Loops[0], Function, Plan)
