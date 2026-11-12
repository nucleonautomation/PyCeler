import copy
import json
import shutil
import subprocess
import tempfile
from .Native_Build import _Interpreter
from .Selection_Cache import _Normalize_Workloads, _Cache_Context, _Cache_Read, _Cache_Write
from .Selection_Policy import _Selection_Table, _Candidate_Code, _Candidate_Name, _Candidate_Order, _Normalize_Tuning, _Explain_Selection

cdef str _Team_Probe = """
from cython.parallel cimport parallel as _Probe_Parallel, threadid as _Probe_Id
from openmp cimport omp_get_num_threads as _Probe_Count, omp_get_max_threads as _Probe_Max, omp_set_num_threads as _Probe_Set, omp_get_dynamic as _Probe_Dynamic

def _Probe_Settings():
    return _Probe_Max(), _Probe_Dynamic()
def _Probe_Threads(int Count=0):
    cdef int Team[1]
    cdef int Previous = _Probe_Max()
    Team[0] = 1
    if Count:
        _Probe_Set(Count)
    try:
        with nogil, _Probe_Parallel():
            if _Probe_Id() == 0:
                Team[0] = _Probe_Count()
    finally:
        _Probe_Set(Previous)
    return Team[0]
"""

cdef tuple _Size_Arguments(dict Plan):
    if "Size_Arguments" in Plan:
        return Plan["Size_Arguments"]
    return tuple(_Scalar_Size_Plan(Plan)["Arguments"])

cdef tuple _Probe_Item(int Line, tuple Edit, bint Parallel):
    Names, Node, Function, Plan = Edit
    Region = Plan is not None and Plan.get("Region", False)
    Definition = copy.deepcopy(Plan["Probe"] if Region else Function)
    Definition.name = f"Item_{Line}"
    Definition.args.defaults = []
    Definition.returns = None
    for Arg in Definition.args.posonlyargs + Definition.args.args:
        Arg.annotation = None
    Scalar = Plan is not None and Plan.get("Kind") in ("scalar", "scalar_region", "module_scalar")
    Loops = [Node] if Plan is None else Plan["Loops"]
    Item = dict(Function=Plan["Scope"] if Region else Function.name, Line=Line, End_Line=Node.end_lineno if Region else Function.end_lineno, Loops=len(Loops),
                Loop_Lines=[Loop.lineno for Loop in Loops], Kind="scalar" if Scalar else "array",
                Arguments=len(Names), Probe=Definition.name, Eligible=["Python", "Serial"])
    if Region:
        Item["Extracted"] = True
    if Plan is not None and Plan.get("Kind") == "receive":
        Item.update(Kind="receive", Reader=Plan["Reader"], Workload="In-memory fragmented reads; excludes transport latency",
                    Skipped_Candidates={"OpenMP": "Reads from one stream consume ordered state"})
    elif Plan is not None and Plan.get("Kind") == "span":
        Item.update(Kind="span", Mode=Plan["Mode"], Skipped_Candidates={"OpenMP": "Contiguous byte span operation runs serially"})
    elif Scalar:
        Item["Size_Arguments"] = _Size_Arguments(Plan)
        if Plan.get("Kind") in ("scalar_region", "module_scalar"):
            Item["Range_Start_Argument"] = 1
            Item["Range_Step"] = Plan["Step"]
            Period = Plan.get("Period")
            if Plan["Step"] is None:
                Item["Range_Step_Argument"] = Plan["Step_Argument"]
                Item["Range_Period"] = Period
            Item["Span_Maximum"] = Period // math.gcd(Plan["Step"], Period) if Period is not None and Plan["Step"] is not None else None
            Item["Workload"] = "Isolated pure numeric span; excludes surrounding Python calls and reporting"
        else:
            Item["Size_Plan"] = _Scalar_Size_Plan(Plan)
        if Plan.get("Parallel_Reduction") or Plan.get('Module_Reduction'):
            Item["Numerical_Contract"] = "Exact integer addition; runtime interval proof bounds every expression and every possible partial sum to int64"
            Item["Serial_Contract"] = "The same interval proof and unchecked integer term as OpenMP, accumulated sequentially"
            if Parallel:
                Item["Eligible"].append("OpenMP")
            else:
                Item["Skipped_Candidates"] = {"OpenMP": "Disabled by caller"}
        else:
            Item["Skipped_Candidates"] = {"OpenMP": "Ordered scalar control flow has no proven parallel implementation"}
    else:
        Kind = Plan.get("Kind") if Plan is not None else None
        if Kind == 'math_map':
            Item.update(Math_Imports=Plan['Math_Imports'], Math_Functions=Plan['Math_Functions'], Numerical_Contract=Plan['Numerical_Contract'], Registry_Version=Plan['Registry_Version'])
            Item['Unboxed_Math'] = Plan['Fast_Math']['Functions'] if Plan.get('Fast_Math') else ()
        if Kind == "median":
            Item.update(Kind="median", Transformations=Plan["Transformations"])
        if Kind == "structural":
            Item.update(Kind=Kind, Outputs=[Names.index(Name) for Name in Plan["Outputs"] if Name in Names], Transformations=Plan.get("Transformations", []))
            Item["Eligible"].append("Optimized")
            if Plan.get("Allocation"):
                Alias = Plan["Allocation"][0]
                Probe_Alias = "_Probe_Numpy"
                Used = {Part.id for Part in ast.walk(Definition) if isinstance(Part, ast.Name)} | set(Names)
                while Probe_Alias in Used:
                    Probe_Alias += "_X"
                for Part in ast.walk(Definition):
                    if isinstance(Part, ast.Attribute) and Part.attr == "empty_like" and _Name(Part.value, Alias):
                        Part.value.id = Probe_Alias
                Item["NumPy_Alias"] = Probe_Alias
        if Kind == "projection":
            Item.update(Kind=Kind, Destination=0, Indirect=Plan["Indirect"], Gates=[Flag is not None for Flag, A, V in Plan["Gates"]], Named_Size=Plan["Named_Size"])
        elif Kind == "row_selection":
            Item.update(Kind=Kind, Destination=0, Named=Plan["Named"])
        elif Kind in ("stencil", "count"):
            Item.update(Kind=Kind, Destination=0, Dimensions=2 if Kind == "stencil" else 1)
            if Kind == "stencil":
                Item["Eligible"].append("Tiled")
        else:
            Item.update(Arrays=[Index for Index, Name in enumerate(Names) if Plan is None or Name in Plan["Arrays"]],
                        Destination=0 if Plan is None else Names.index(Plan["Output"]), Dimensions=1 if Plan is None else len(Plan["Indices"]))
            if Plan is not None and "Byte_Copy" in Plan:
                Item["Byte_Copy"] = Plan["Byte_Copy"]
            if Plan is not None and not Plan.get("Clear"):
                Item["Pixel_Dtypes"] = True
            if Plan is not None and "Dimension_Args" in Plan:
                Item["Dimension_Args"] = [(Names.index(Name), Axis) for Name, Axis in Plan["Dimension_Args"].items()]
        if Parallel and (Kind != 'math_map' or Plan.get('Fast_Math')):
            Item["Eligible"].append("OpenMP")
        else:
            Item["Skipped_Candidates"] = {"OpenMP": "Ordered original library calls require the GIL and original mutation order" if Kind == 'math_map' else "Disabled by caller"}
    return Item, ast.unparse(Definition)

cdef dict _Probe_Builds(object Reference, list Items, object Folder, object Mode, object Version, dict Builds, tuple Variants=("Serial", "Optimized", "Tiled", "OpenMP"), bint Elide_Temporaries=False):
    Modules = {Item["Probe"]: {"Python": str(Reference)} for Item in Items}
    Prepared = _Plan(Reference, False, Elide_Temporaries)
    By_Name = {Edit[2].name: Line for Line, Edit in Prepared[2].items()}
    for Variant in Variants:
        Eligible = [Item for Item in Items if Variant in Item["Eligible"]]
        if not Eligible:
            continue
        Number = _Candidate_Code(Variant)
        Threaded = Variant.startswith("OpenMP")
        Choices = {}
        for Item in Eligible:
            if Item["Probe"] not in By_Name:
                Item.setdefault("Skipped_Candidates", {})[Variant] = "Isolated definition did not reproduce the original plan"
                continue
            Keys = ("int",) if Item["Kind"] in ("scalar", "receive") else ("<i4", "<i8", "<f4", "<f8", ">i4", ">i8", ">f4", ">f8")
            if Item["Kind"] == "stencil":
                Keys = ("|u1", "<i2", "<u2", "<i4", ">i2", ">u2", ">i4")
            elif Item.get("Pixel_Dtypes"):
                Keys = (*Keys, "|i1", "|u1", "<i2", "<u2", ">i2", ">u2")
            if Item["Kind"] == "span":
                Keys = ("bytearray",)
            elif "Byte_Copy" in Item:
                Keys = (*Keys, "bytearray")
            Choices[By_Name[Item["Probe"]]] = {Key: [(65536, Number), (2048, Number), (0, Number)] for Key in Keys}
        Eligible = [Item for Item in Eligible if Item["Probe"] in By_Name]
        if not Eligible:
            continue
        with _Workspace() as Build:
            Sources = Build / "Sources"
            Sources.mkdir()
            Relative = Path("Probe_" + Variant + ".pyx")
            Code = _Generate(Reference, Threaded, (), Choices, None, Prepared)
            (Sources / Relative).write_text(Code + (_Team_Probe if Threaded else ""), encoding="utf-8")
            shutil.copy2(Sources / Relative, Folder / Relative)
            try:
                Binary = _Build(Build, [Relative], Folder, Mode, Version, False, Threaded)[0]
                for Item in Eligible:
                    Modules[Item["Probe"]][Variant] = str(Binary)
                Log = Build.parent / "Logs" / (Build.name + ".log")
                if Log.is_file():
                    shutil.copy2(Log, Folder / ("Probe_" + Variant + ".log"))
                Builds[Variant] = dict(Status="built", Log=str(Log))
            except (OSError, RuntimeError) as Error:
                Builds[Variant] = dict(Status="compilation failed", Reason=str(Error))
                if len(Items) > 1 and "Cython generation failed for" in str(Error):
                    Definitions = {Node.name: ast.unparse(Node) for Node in Prepared[3].body if isinstance(Node, ast.FunctionDef)}
                    Isolated = {}
                    for Item in Eligible:
                        Name = Item["Probe"]
                        Individual = Folder / Variant / Name
                        Individual.mkdir(parents=True)
                        Single = Individual / "Reference.py"
                        Imports = ("import socket\n" if Item["Kind"] == "receive" else "") + (f"import numpy as {Item['NumPy_Alias']}\n" if Item.get("NumPy_Alias") else "")
                        Imports += '\n'.join(Item.get('Math_Imports', ())) + '\n'
                        Single.write_text(Imports + Definitions[Name] + "\n", encoding="utf-8")
                        Outcome = {}
                        Retry = _Probe_Builds(Single, [Item], Individual, Mode, Version, Outcome, (Variant,), Elide_Temporaries)
                        Isolated[Name] = Outcome.get(Variant, {"Status": "unsupported"})
                        if Variant in Retry[Name]:
                            Modules[Name][Variant] = Retry[Name][Variant]
                    Builds[Variant].update(Status="retried per item", Items=Isolated)
    return Modules

cdef dict _Measure_Item(list Command, object Folder, dict Item, dict Candidates, double Gain):
    Request = Folder / (Item["Probe"] + ".json")
    Request.with_suffix(".result").unlink(missing_ok=True)
    Request.write_text(json.dumps(dict(Item=Item, Modules=Candidates, Gain=Gain)), encoding="utf-8")
    Package_Root = str(Path(__file__).resolve().parent.parent)
    Worker = "import sys; sys.path.insert(0, sys.argv[1]); from pathlib import Path; from PyCeler.Selection_Worker import _Run; _Run(Path(sys.argv[2]))"
    Budget = Item.get("Tuning", {}).get("Budget_Seconds", 30)
    try:
        Process = subprocess.run([*Command, "-I", "-B", "-c", Worker, Package_Root, str(Request)], cwd=Folder, capture_output=True,
                                 text=True, errors="replace", timeout=Budget + 5)
    except subprocess.TimeoutExpired:
        if not Request.with_suffix(".result").is_file():
            raise
        Result = json.loads(Request.with_suffix(".result").read_text(encoding="utf-8"))
        Result["Worker_Budget"]["Hard_Timeout"] = True
        Result["Worker_Budget"]["Process_Limit_Seconds"] = Budget + 5
        return Result
    if Process.returncode:
        raise RuntimeError(Process.stderr[-2000:] or f"Worker exited with {Process.returncode}")
    return json.loads(Request.with_suffix(".result").read_text(encoding="utf-8"))

cdef void _Selection_Report(dict Report) except *:
    Counts = {}
    for Item in Report["Items"]:
        Selected = any(Mode for Bands in Item.get("Dispatch", {}).values() for Bound, Mode in Bands)
        Cases = Item.get("Cases", [])
        Validation = [Status for Case in Cases for Name, Status in Case.get("Validation", {}).items() if Name != "Python"]
        if Selected:
            Status = "native_selected"
        elif Item.get("Reason") == "No native candidate built":
            Status = "no_native_candidate_built"
        elif Item.get("Probe_Error") or "Inconclusive" in Item.get("Reason", "") or any(Case.get("Validation", {}).get("Python", "").startswith("inconclusive") for Case in Cases):
            Status = "inconclusive"
        elif any(Value.startswith("invalid") for Value in Validation):
            Status = "validation_failed"
        elif Validation and not any(Value == "valid" for Value in Validation):
            Status = "unsupported_inputs"
        else:
            Status = "python_selected"
        Item["Status"] = Status
        Item["Runtime_Fallback"] = "Runtime input, binding, environment and arithmetic guards still apply; this report records isolated probes, not later application calls."
        if "Summary" in Item:
            Item["Summary"]["Status"] = Status
        Counts[Status] = Counts.get(Status, 0) + 1
    Report["Status"] = "no_candidates" if not Report["Items"] else "native_selected" if Counts.get("native_selected") else "python_selected"
    Report["Summary"] = dict(Candidate_Regions=len(Report["Items"]), Native_Selected_Regions=Counts.get("native_selected", 0),
                             Skipped_Loops=len(Report["Skipped"]), Candidate_Builds=len(Report["Builds"]), Outcomes=Counts,
                             Scope="Candidate validation and selection; final module compilation is a separate operation.")

cdef dict _Unmeasured_Report(object File, tuple Prepared):
    from dataclasses import asdict
    Text, Findings, Edits, Tree = Prepared
    Eligible = []
    Covered = set()
    for Line, Edit in sorted(Edits.items()):
        Names, Node, Function, Plan = Edit
        Loops = Plan.get("Loops", [Node]) if Plan is not None else [Node]
        Covered.update(Loop.lineno for Loop in Loops)
        Eligible.append(dict(Function=Plan.get("Scope", Function.name) if Plan is not None else Function.name,
                             Line=Line, End_Line=Node.end_lineno, Kind=Plan.get("Kind", "array") if Plan is not None else "array",
                             Status="unmeasured", Transformations=Plan.get("Transformations", []) if Plan is not None else []))
    Skipped = [dict(Function=Finding.Function, Line=Finding.Line, End_Line=Finding.End_Line, Reason=Finding.Reason,
                    Action="Keep original Python loop", Diagnostics=[Diagnostic._As_Dict() for Diagnostic in Finding.Diagnostics])
               for Finding in Findings if Finding.Line not in Covered]
    return dict(Format="PyCeler selection 1", Source=str(File), Status="measurement_disabled", Measurement=False,
                Findings=[asdict(Finding) for Finding in Findings], Eligible_Regions=Eligible, Items=Eligible, Skipped=Skipped, Builds={},
                Fallback_Contract="Unsupported Python source and guard fallbacks execute as CPython code; native Cython input and Convert=False retain Cython semantics.",
                Summary=dict(Candidate_Regions=len(Eligible), Native_Selected_Regions=0, Skipped_Loops=len(Skipped), Candidate_Builds=0,
                             Scope="Static analysis only; eligible candidates were not behaviorally validated or timed"))

cdef tuple _Select_Items(object File, tuple Prepared, object Folder, object Mode, object Version, bint Parallel, double Gain, object Workloads=None, object Cache=False, bint Elide_Temporaries=False, object Tuning=None, bint Profile=False):
    Text, Findings, Edits, Tree = Prepared
    Choices, Items, Definitions, Builds = {}, [], [], {}
    Workloads = _Normalize_Workloads(Workloads)
    Tuning = _Normalize_Tuning(Tuning)
    Finding_By_Line = {Finding.Line: Finding for Finding in Findings}
    for Line, Edit in sorted(Edits.items()):
        Item, Definition = _Probe_Item(Line, Edit, Parallel)
        Diagnostics = { (Diagnostic.Code, Diagnostic.Line, Diagnostic.Column): Diagnostic._As_Dict()
                        for Loop_Line in Item["Loop_Lines"] if Loop_Line in Finding_By_Line for Diagnostic in Finding_By_Line[Loop_Line].Diagnostics }
        Item["Diagnostics"] = list(Diagnostics.values())
        Item["Profile"] = Profile
        if Tuning:
            Item["Tuning"] = Tuning
            for Candidate, Option in (("OpenMP", "Threads"), ("Tiled", "Tiles")):
                if Candidate in Item["Eligible"] and Tuning[Option]:
                    Item["Eligible"].remove(Candidate)
                    Item["Eligible"].extend(Candidate + "_" + str(Value) for Value in Tuning[Option])
        Workload = Workloads.get(Item["Function"] + ":" + str(Line), Workloads.get(Item["Function"]))
        if Workload is not None:
            Item["Representative_Workload"] = Workload
        Items.append(Item)
        Definitions.append(Definition)
    Covered = {Line for Item in Items for Line in Item["Loop_Lines"]}
    Skipped = [dict(Function=Finding.Function, Line=Finding.Line, End_Line=Finding.End_Line, Reason=Finding.Reason, Action="Keep original loop",
                    Diagnostics=[Diagnostic._As_Dict() for Diagnostic in Finding.Diagnostics]) for Finding in Findings if Finding.Line not in Covered]
    Report = dict(Format="PyCeler selection 1", Source=str(File), Minimum_Speedup=Gain, Build_Mode=Mode, Items=Items, Skipped=Skipped, Builds=Builds,
                  Fallback_Contract="Python-source conversion preserves unsupported code and guarded fallbacks as CPython code. Native .pyx/.pxi input and Convert=False retain Cython compilation semantics.")
    if not Items:
        _Selection_Report(Report)
        return Choices, None, Report
    Command, Floor = _Interpreter(Mode, Version)
    Report["Python_Target"] = Floor
    Context = None
    try:
        Context = _Cache_Context(File, Mode, Floor, Parallel, Gain, Workloads, Cache, Elide_Temporaries, Text, dict(Tuning=Tuning, Profile=Profile))
        Cached = _Cache_Read(Context)
        if Cached is not None:
            return Cached
    except (OSError, RuntimeError) as Error:
        Report["Cache"] = dict(Status="unavailable", Reason=str(Error))
    if Context is not None:
        Report["Cache"] = dict(Status="miss", Key=Context[1], Directory=str(Context[0] / Context[1]))
    elif Cache and "Cache" not in Report:
        Report["Cache"] = dict(Status="unavailable", Reason="Compiler identity, source snapshot or selected interpreter cannot be verified in this environment")
    Reference = Folder / "Reference.py"
    Imports = "import socket\n" if any(Item["Kind"] == "receive" for Item in Items) else ""
    Imports += "".join(f"import numpy as {Alias}\n" for Alias in sorted({Item["NumPy_Alias"] for Item in Items if "NumPy_Alias" in Item}))
    Imports += '\n'.join(sorted({Import for Item in Items for Import in Item.get('Math_Imports', ())})) + '\n'
    Reference.write_text(Imports + "\n\n".join(Definitions) + "\n", encoding="utf-8")
    Variants = tuple(_Candidate_Order({Candidate for Item in Items for Candidate in Item["Eligible"]}))
    Modules = _Probe_Builds(Reference, Items, Folder, Mode, Version, Builds, Variants, Elide_Temporaries)
    Environment = None
    for Item in Items:
        Candidates = Modules[Item["Probe"]].copy()
        if len(Candidates) == 1:
            Item.update(Cases=[], Fallback="Python", Reason="No native candidate built")
            continue
        Failures = (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired)
        try:
            Result = _Measure_Item(Command, Folder, Item, Candidates, Gain)
        except Failures as Error:
            Item["Probe_Error"] = str(Error)
            if not any(Name.startswith("OpenMP") for Name in Candidates) or "Serial" not in Candidates:
                Item.update(Cases=[], Fallback="Python", Reason="Inconclusive isolated probe")
                continue
            Candidates = {Name: Value for Name, Value in Candidates.items() if not Name.startswith("OpenMP")}
            try:
                Result = _Measure_Item(Command, Folder, Item, Candidates, Gain)
            except Failures as Serial_Error:
                Item.update(Cases=[], Fallback="Python", Reason="Inconclusive serial probe: " + str(Serial_Error))
                continue
        if Environment is None:
            Environment = Result["Environment"].copy()
        else:
            for Key in ("NumPy", "OpenMP_Settings"):
                if Result["Environment"].get(Key) is not None:
                    Environment[Key] = Result["Environment"][Key]
        Item.update(Cases=Result["Cases"], OpenMP_Team=Result["Threads"], OpenMP_Teams=Result.get("Teams", {}), Import_Errors=Result["Import_Errors"],
                    Worker_Budget=Result.get("Worker_Budget", {}), Fallback="Python")
        Table = _Selection_Table(Result["Cases"], Gain, "Representative_Workload" in Item)
        Item["Coverage"] = {Key: dict(Minimum_Measured=min((Case["Size"] for Case in Result["Cases"] if Case["Key"] == Key and Case["Timings"]), default=None),
            Maximum_Measured=max((Case["Size"] for Case in Result["Cases"] if Case["Key"] == Key and Case["Timings"]), default=None),
            Native_Size_Ceiling=max(Case["Size"] for Case in Result["Cases"] if Case["Key"] == Key) if "Representative_Workload" in Item else None,
            Extrapolates="Representative_Workload" not in Item) for Key in Table}
        if "Representative_Workload" in Item:
            Item["Dispatch_Validation"] = "Every measured shape and distribution in each band must support promotion; holdouts do not define bands; larger unmeasured sizes use Python"
        else:
            Item["Dispatch_Validation"] = "Synthetic workload bands extrapolate above the largest probe, including with tuning; arithmetic and input guards remain active. Performance at larger sizes is unmeasured; supply production Workloads for bounded dispatch."
        Item["Dispatch"] = Table
        for Case in Result["Cases"]:
            Selected = next((Mode for Bound, Mode in Table.get(Case["Key"], ()) if Case["Size"] >= Bound), 0)
            Case["Dispatch_Winner"] = _Candidate_Name(Selected)
        Choices[Item["Line"]] = Table
    for Item in Items:
        _Explain_Selection(Item)
    Report["Environment"] = Environment
    Report["Measured_Priorities"] = sorted([dict(Function=Item["Function"], Line=Item["Line"],
        Largest_Python_Median_Ns=max((Case["Timings"]["Python"]["Median_Ns"] for Case in Item.get("Cases", []) if "Python" in Case["Timings"]), default=0)) for Item in Items], key=lambda Value: -Value["Largest_Python_Median_Ns"])
    _Selection_Report(Report)
    try:
        _Cache_Write(Context, Choices, Environment, Report, Folder)
    except OSError as Error:
        Report["Cache"] = dict(Status="write failed", Reason=str(Error))
    return Choices, Environment, Report
