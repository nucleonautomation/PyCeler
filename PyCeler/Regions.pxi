from dataclasses import replace
from .Common_Analysis import _Definite_Bindings

cdef object _Region_Function(object Function, list Statements, tuple Names, str Result):
    Definition = ast.parse(f"def {Function.name}({', '.join(Names)}):\n    pass").body[0]
    Definition.body = [*Statements, ast.Return(value=ast.Name(id=Result, ctx=ast.Load()))]
    return ast.fix_missing_locations(Definition)

cdef object _Map_Region(object Function, object Loop, set Bound):
    Stores = {Part.id for Part in ast.walk(Loop) if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Store)}
    Targets = {Part.value.id for Part in ast.walk(Loop) if isinstance(Part, ast.Subscript) and isinstance(Part.ctx, ast.Store) and isinstance(Part.value, ast.Name)}
    if len(Targets) != 1:
        return None
    Result = next(iter(Targets))
    Names = tuple(dict.fromkeys(Part.id for Part in ast.walk(Loop) if isinstance(Part, ast.Name) and Part.id not in Stores | {"range", "len"}))
    if not set(Names) <= Bound:
        return None
    Definition = _Region_Function(Function, [Loop], Names, Result)
    Plan = _Map_Plan(Definition, Loop)
    if not isinstance(Plan, dict):
        Plan = _Sized_Map_Region(Function, Loop, Names, Result)
        if Plan is None:
            return None
    Plan.update(Probe=Definition, Private=Stores, Region=True)
    if _Whole_Clear(Definition, Loop, Result) and _Classify(Loop, Definition)[0] == "Potential_Independent_Write":
        Plan["Clear"] = True
    return Plan

cdef object _Sized_Map_Region(object Function, object Loop, tuple Names, str Output):
    Candidate = copy.deepcopy(Loop)
    Level, Dimensions = Candidate, {}
    Axis = 0
    while isinstance(Level, ast.For):
        Call = Level.iter
        if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or Call.keywords or len(Call.args) != 1:
            return None
        End = Call.args[0]
        if isinstance(End, ast.Name):
            if End.id not in Names or End.id == Output or End.id in Dimensions:
                return None
            Dimensions[End.id] = Axis
            Call.args[0] = ast.copy_location(ast.parse(f"{Output}.shape[{Axis}]", mode="eval").body, End)
        if len(Level.body) != 1:
            break
        Level = Level.body[0]
        Axis += 1
    if not Dimensions or any(isinstance(Node, ast.Name) and Node.id in Dimensions for Node in ast.walk(Candidate)):
        return None
    Kernel_Names = tuple(Name for Name in Names if Name not in Dimensions)
    Plan = _Map_Plan(_Region_Function(Function, [Candidate], Kernel_Names, Output), Candidate)
    if not isinstance(Plan, dict):
        return None
    Source_Loops = {Part.lineno: Part for Part in ast.walk(Loop) if isinstance(Part, (ast.For, ast.While))}
    Plan.update(Names=Names, Kernel_Names=Kernel_Names, Dimension_Args=Dimensions, Loops=[Source_Loops[Part.lineno] for Part in Plan["Loops"]])
    return Plan

cdef set _Assigned(object Target):
    if isinstance(Target, ast.Name):
        return {Target.id}
    if isinstance(Target, (ast.Tuple, ast.List)):
        return set().union(*(_Assigned(Child) for Child in Target.elts))
    return set()

cdef void _Region_Block(object Function, list Statements, set Entering, dict Edits, dict Updates, dict Context) except *:
    Bound = Entering.copy()
    for Position, Node in enumerate(Statements):
        Plan = None
        if isinstance(Node, ast.For) and Node.lineno not in Edits:
            Available = Bound - Context["Handler_Names"]
            Plan = _Special_Region(Function, Node, Statements[:Position], Available)
            if Plan is None:
                Plan = _Map_Region(Function, Node, Available)
        if Plan is not None:
            Inside = set(ast.walk(Node))
            Hidden = set()
            for Other in Context["For_Loops"]:
                if (Other not in Inside and isinstance(Other.target, ast.Name) and Other.target.id in Plan["Private"] and
                        (Other.end_lineno < Node.lineno or Other.lineno > Node.end_lineno)):
                    Hidden.add(Other.target)
                    Hidden.update(Part for Statement in Other.body for Part in ast.walk(Statement) if _Name(Part, Other.target.id))
            Outside = {Part.id for Part in Context["Names"] if Part not in Inside and Part not in Hidden}
            Used = Plan["Private"] & (Outside | Context["Bindings"])
            if Used:
                Context["Rejected"][Node.lineno] = "Extraction would hide or change local bindings used elsewhere: " + ", ".join(sorted(Used)) + "."
                Plan = None
            elif Node.lineno in Context["Shared"] or Node.end_lineno in Context["Shared"]:
                Context["Rejected"][Node.lineno] = "Another statement shares the source line at the extraction boundary."
                Plan = None
        if Plan is not None:
            Edits[Node.lineno] = (Plan["Names"], Node, Function, Plan)
            Plan["Scope"] = Context["Scope"]
            for Loop in Plan["Loops"]:
                Updates[Loop.lineno] = Plan
        else:
            if isinstance(Node, (ast.For, ast.While, ast.If)):
                Extra = _Assigned(Node.target) if isinstance(Node, ast.For) else set()
                _Region_Block(Function, Node.body, Bound | Extra, Edits, Updates, Context)
                _Region_Block(Function, Node.orelse, Bound, Edits, Updates, Context)
            elif isinstance(Node, ast.Try):
                for Block in (Node.body, Node.orelse, Node.finalbody, *(Handler.body for Handler in Node.handlers)):
                    _Region_Block(Function, Block, Bound, Edits, Updates, Context)
            elif isinstance(Node, ast.With):
                _Region_Block(Function, Node.body, Bound, Edits, Updates, Context)
        if isinstance(Node, ast.Assign):
            for Target in Node.targets:
                Bound.update(_Assigned(Target))
        elif isinstance(Node, ast.If):
            Branch_Bound = _Definite_Bindings((Node,), Bound)
            if Branch_Bound is not None:
                Bound.update(Branch_Bound)
        elif isinstance(Node, ast.Try) and all(Handler.body and isinstance(Handler.body[-1], (ast.Raise, ast.Break, ast.Continue, ast.Return)) for Handler in Node.handlers):
            for Part in Node.body:
                if isinstance(Part, ast.Assign):
                    for Target in Part.targets:
                        Bound.update(_Assigned(Target))

cdef void _Find_Regions(object Tree, list Findings, dict Edits, bint Parallel) except *:
    Existing = {Edit[2] for Edit in Edits.values()}
    Updates = {}
    Rejected = {}
    for Top in Tree.body:
        for Function in (Top.body if isinstance(Top, ast.ClassDef) else [Top]):
            if not isinstance(Function, ast.FunctionDef) or Function in Existing or getattr(Function, "type_params", ()):
                continue
            Parts = list(ast.walk(Function))
            if any(isinstance(Part, (ast.Global, ast.Nonlocal, ast.Delete, ast.Lambda, ast.Yield, ast.YieldFrom)) or
                   (Part is not Function and isinstance(Part, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))) or
                   (isinstance(Part, ast.Name) and Part.id in {"locals", "vars", "eval", "exec", "super", "_getframe", "currentframe"}) for Part in Parts):
                continue
            Names = [Part for Part in Parts if isinstance(Part, ast.Name)]
            Arguments = {Part.arg for Part in Parts if isinstance(Part, ast.arg)}
            Bindings = Arguments | {Part.name for Part in Parts if isinstance(Part, ast.ExceptHandler) and Part.name}
            Bindings.update((Part.asname or Part.name.split(".")[0]) for Part in Parts if isinstance(Part, ast.alias))
            Bindings.update(Part.name for Part in Parts if isinstance(Part, (ast.MatchAs, ast.MatchStar)) and Part.name)
            if {"range", "len", "int", "float", "abs"} & (Bindings | {Part.id for Part in Names if isinstance(Part.ctx, ast.Store)}):
                continue
            Counts = {}
            for Part in Parts:
                if isinstance(Part, ast.stmt):
                    Counts[Part.lineno] = Counts.get(Part.lineno, 0) + 1
            Scope = f"{Top.name}.{Function.name}" if isinstance(Top, ast.ClassDef) else Function.name
            _Region_Block(Function, Function.body, Arguments, Edits, Updates, dict(Names=Names, Bindings=Bindings, Scope=Scope, Rejected=Rejected,
                          For_Loops=[Part for Part in Parts if isinstance(Part, ast.For)],
                          Handler_Names={Part.name for Part in Parts if isinstance(Part, ast.ExceptHandler) and Part.name},
                          Shared={Line for Line, Count in Counts.items() if Count > 1}))
    for Index, Finding in enumerate(Findings):
        Plan = Updates.get(Finding.Line)
        if Plan is not None:
            Label = Plan.get("Label", "element-wise array loop")
            Updates_Mode = "serial/OpenMP" if Parallel and Plan.get("Kind") != "span" else "serial"
            Classification = {"projection": "Integer_Count_Reduction", "count": "Integer_Count_Reduction", "span": "Byte_Buffer_Span",
                              "stencil": "Masked_Neighborhood", "row_selection": "Independent_Row_Selection"}.get(Plan.get("Kind"), "Potential_Independent_Write")
            Findings[Index] = replace(Finding, Classification=Classification, Change=f"Extract guarded {Updates_Mode} {Label}",
                                      Reason="Only the extracted loop is probed. Surrounding calls stay in source order.")
        elif Finding.Line in Rejected and Finding.Change == "Keep original loop":
            Findings[Index] = replace(Finding, Reason=Rejected[Finding.Line])
