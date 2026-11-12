include "Map_Generator.pxi"
include "Region_Generator.pxi"
include "Structural_Generator.pxi"
include "Numeric_Generator.pxi"
include "Scalar_Region_Generator.pxi"
include "Dispatch_Instrumentation.pxi"
include "Python_Module.pxi"

cdef str _Tuned_Kernel(str Code, int Count):
    Names = re.findall(r"(?m)^cdef (?:inline )?\w+ (_Pyceler_\w+)\(", Code)
    for Name in sorted(Names, key=len, reverse=True):
        Code = re.sub(r"\b" + re.escape(Name) + r"\b", Name + f"_Team_{Count}", Code)
    Lines = [Line.replace("nogil=True", f"nogil=True, num_threads={Count}") if "_Pyceler_Prange(" in Line else Line for Line in Code.splitlines()]
    return "\n".join(Lines).replace("_Pyceler_Max_Threads()", str(Count))

cdef str _Generate(object File, bint Parallel, tuple Members, object Choices=None, object Environment=None, object Prepared=None):
    Text, Findings, Edits, Tree = Prepared if Prepared is not None else _Plan(File, Parallel)
    Lines = Text.split("\n")
    for Index in range(min(2, len(Lines))):
        if re.match(r"^[ \t\f]*#", Lines[Index]):
            Lines[Index] = re.sub(r"(coding[:=]\s*)[-\w.]+", r"\g<1>utf-8", Lines[Index], count=1)
    Prefix = "_Pyceler_"
    while Prefix in Text:
        Prefix += "X"
    Map_Kernels = []
    Math_Kernels = []
    Scalar_Kernels = []
    Has_Scalar_Regions = False
    Has_Module_Scalars = False
    Specials = []
    Streams = []
    Structures = []
    Numerics = []
    Has_Spans = False
    Regions = []
    Has_Clear = False
    Tuned_Clear = set()
    Has_Parallel = False
    Has_Parallel_Scalar = False
    Tables = []
    Has_Scalar_Sizing = False
    Future_Features = tuple(Alias.name for Statement in Tree.body if isinstance(Statement, ast.ImportFrom) and Statement.module == '__future__' for Alias in Statement.names)
    for Line in sorted(Edits, reverse=True):
        Names, Node, Function, Plan = Edits[Line]
        Region = Plan is not None and Plan.get("Region", False)
        Kind = Plan.get("Kind") if Plan is not None else None
        Arguments = ", ".join(Names)
        Table = None if Choices is None else Choices.get(Line, {})
        Codes = {Mode for Rows in Table.values() for Size, Mode in Rows} if Table else set()
        Modes = {4 if Code >= 10000 else 2 if Code >= 100 else Code for Code in Codes}
        Native = Table is None or bool(Modes & {1, 2, 3, 4})
        if Kind == 'math_map' and not Native:
            continue
        if Kind == "module_scalar":
            if not Native:
                continue
            Has_Module_Scalars = True
            Has_Scalar_Regions = True
            Has_Parallel_Scalar |= Plan['Module_Reduction'] is not None
            Threads = Parallel and (Table is None or 2 in Modes) and Plan['Module_Reduction'] is not None
            Has_Parallel |= Threads
            Scalar_Kernels.append(_Module_Scalar_Kernel(Plan, Line, Threads, str(File), Prefix, Table is not None, Future_Features))
            Policy = 'None'
            if Table is not None:
                Tables.append(f'{Prefix}Table_{Line} = {Table!r}')
                Policy = f'{Prefix}Table_{Line}'
            Indent = Lines[Line - 1][:len(Lines[Line - 1]) - len(Lines[Line - 1].lstrip(' \t'))]
            Replacement = [Indent + Text for Text in _Module_Constant_Anchor(Node, Line, Prefix).splitlines()]
            Replacement.append(f'{Indent}{Prefix}Module_Run_{Line}({Prefix}Module_Namespace(), {ast.unparse(Node.iter)}, {Threads}, {Policy}, {Prefix}Module_Constants_{Line}.__code__)')
            Replacement.extend(Indent + Text for Statement in Node.orelse for Text in ast.unparse(Statement).splitlines())
            Lines[Line - 1:Node.end_lineno] = Replacement
            continue
        if Kind == "scalar_region":
            if not Native:
                continue
            Has_Scalar_Regions = True
            Scalar_Kernels.append(_Scalar_Region_Kernel(Plan, Line))
            if Table is not None:
                Tables.append(f"{Prefix}Table_{Line} = {Table!r}")
            Indent = Lines[Line - 1][:len(Lines[Line - 1]) - len(Lines[Line - 1].lstrip(" \t"))]
            Replacement = _Scalar_Region_Source(Plan, Node, Line, Prefix, Table)
            Lines[Line - 1:Node.end_lineno] = [Indent + Value for Value in Replacement.splitlines()]
            continue
        Threads = Parallel and (Table is None or 2 in Modes) and Kind not in ("receive", "span") and (Kind != 'math_map' or bool(Plan.get('Fast_Math'))) and (Kind != "scalar" or bool(Plan.get("Parallel_Reduction")))
        Has_Parallel |= Threads
        if not Native:
            Helper = ""
        elif Plan is None or Plan.get("Clear"):
            Has_Clear = True
            Helper = Prefix + "Clear"
        elif Kind in ("stencil", "count", "projection", "row_selection"):
            if Kind == "stencil":
                Specials.append(_Stencil_Kernel(Plan, Line, Threads))
            elif Kind == "projection":
                Specials.append(_Projection_Kernel(Plan, Line, Threads))
            elif Kind == "row_selection":
                Specials.append(_Row_Selection_Kernel(Plan, Line, Threads))
            else:
                Specials.append(_Count_Kernel(Plan, Line, Threads))
            Helper = f"{Prefix}Special_{Line}"
        elif Kind == "span":
            Has_Spans = True
            Helper = Prefix + ("Copy_Span" if Plan["Mode"] == "copy" else ("Fill_Tail" if len(Names) == 2 else "Fill_Span"))
        elif Kind == "receive":
            Streams.append(_Receive_Kernel(Plan, Line))
            Helper = f"{Prefix}Special_{Line}"
        elif Kind == "structural":
            Structures.append(_Structural_Kernel(Plan, Line, Threads))
            Helper = f"{Prefix}Structure_{Line}"
        elif Kind == "median":
            Numerics.append(_Median_Kernel(Plan, Line, Threads))
            Helper = f"{Prefix}Median_{Line}"
        elif Kind == 'math_map':
            Math_Kernels.append(_Math_Map_Kernel(Plan, Line, Threads))
            Helper = f'{Prefix}Math_Map_{Line}'
        elif Plan.get("Kind") == "scalar":
            Scalar_Kernels.append(_Scalar_Kernel(Plan, Line, Threads))
            Has_Parallel_Scalar |= bool(Plan.get("Parallel_Reduction"))
            Helper = f"{Prefix}Scalar_{Line}"
        else:
            Map_Kernels.append(_Map_Kernel(Plan, Line, Threads, Choices is not None))
            Helper = f"{Prefix}Map_{Line}"
        Counts = sorted(Code - 100 for Code in Codes if 100 <= Code < 10000) if Threads and Kind != 'math_map' else []
        if Counts:
            if Plan is None or Plan.get("Clear"):
                Tuned_Clear.update(Counts)
            else:
                Collection = Scalar_Kernels if Kind == "scalar" else Structures if Kind == "structural" else Numerics if Kind == "median" else Specials if Kind in ("stencil", "count", "projection", "row_selection") else Map_Kernels
                Kernel = Collection[-1]
                Collection.extend(_Tuned_Kernel(Kernel, Count) for Count in Counts)
        Start = Line if Plan is None else Plan["Start"]
        First = Lines[Start - 1]
        Indent = First[:len(First) - len(First.lstrip(" \t"))]
        Baseline = f"{Prefix}Original_{Line}"
        if Region:
            Original = ast.unparse(Plan["Probe"])
            Region_Name = f"{Prefix}Region_{Line}"
            Assignment = Plan["Result"] + " = " if "Result" in Plan else ""
            Lines[Start - 1:Node.end_lineno] = [f"{Indent}{Assignment}{Region_Name}({Arguments})"]
            Indent = "    "
        else:
            Original = ast.get_source_segment(Text, Function)
            Baseline_Value = f'{Prefix}Baseline({Original!r}, {Function.name}, {File.name!r})'
            if Kind == 'math_map':
                Pool = f'{Prefix}Math_Literals_{Line}'
                Pool_Source = f'{Pool} = {_Math_Map_Constant_Source(Plan)}'
                Baseline_Value = f'{Prefix}Math_Baseline_{Line}({Baseline_Value}, {Pool})'
                Lines.insert(Function.end_lineno, Pool_Source + '\n' + f'cdef object {Baseline} = {Baseline_Value}')
            else:
                Lines.insert(Function.end_lineno, f'cdef object {Baseline} = {Baseline_Value}')
        Inner = Indent + ("\t" if "\t" in Indent else "    ")
        Body = []
        Scalar = Plan is not None and Plan.get("Kind") == "scalar"
        Flag = "True"
        if Table is not None and Native:
            if Kind == "receive":
                Probe = f"({Plan['Key']},)"
            elif Scalar:
                Has_Scalar_Sizing = True
                Probe = _Scalar_Size_Probe(Plan, Names, Prefix)
            else:
                Probe = Names[0] if Plan is None else Plan.get("Key", Plan["Output"])
            Tables.append(f"{Prefix}Table_{Line} = {Table!r}")
            Choice = f"{Prefix}Choice_{Line}"
            Customized = any(Code >= 100 for Code in Codes)
            Configuration = f"{Prefix}Configuration_{Line}" if Customized else Choice
            Scan = ", " + Names[int(Plan["Indirect"])] if Kind == "projection" else ""
            Minimum = min((Bound for Rows in Table.values() for Bound, Mode in Rows if Mode), default=0)
            Scan = Scan or ", None"
            Body.append(f"{Indent}{Configuration} = {Prefix}Choose({Probe}, {Scalar or Kind == 'receive'}, {Prefix}Table_{Line}{Scan}, {Minimum})")
            if Customized:
                Body.append(f"{Indent}{Choice} = 4 if {Configuration} >= 10000 else 2 if {Configuration} >= 100 else {Configuration}")
            Body.extend([f"{Indent}if not {Choice}:", f"{Inner}return {Baseline}({Arguments})"])
            Flag = f"{Choice} == 2"
        Kernel_Names = Plan.get("Kernel_Names", Names) if Plan is not None else Names
        if Native and Plan is not None and Plan.get("Dimension_Args") and Kind != "structural":
            Tests = [f"{Prefix}Extent({Plan['Output']}, {Axis}, {Name})" for Name, Axis in Plan["Dimension_Args"].items()]
            Body.extend([f"{Indent}if not (" + " and ".join(Tests) + "):", f"{Inner}return {Baseline}({Arguments})"])
        if Native:
            Parameters = [*Kernel_Names, Baseline]
            if not Scalar:
                Parameters.append((Choice if Table is not None else ("2" if Threads else "3")) if Kind == "structural" else (Flag if Threads else "False"))
            elif Threads:
                Parameters.append(Flag)
            if Kind == 'math_map':
                Parameters.append(f'({Configuration} - 100 if 100 <= {Configuration} < 10000 else 0)' if Table is not None and Customized else '0')
            if Kind == "stencil":
                Parameters.append(f"{Choice} == 4" if Table is not None else "False")
                Parameters.append(f"({Configuration} - 10000 if {Configuration} >= 10000 else 32)" if Table is not None else "32")
            Call = Helper + "(" + ", ".join(Parameters) + ")"
        Call_Start = len(Body)
        if not Native:
            Body.append(f"{Indent}return {Baseline}({Arguments})")
        elif Scalar or Kind in ("stencil", "count", "receive", "span", "projection", "row_selection", "structural", "median", "math_map"):
            Body.append(f"{Indent}return {Call}")
        else:
            Body.extend([f"{Indent}if not {Call}:", f"{Inner}return {Baseline}({Arguments})"])
        if Counts:
            Calls = Body[Call_Start:]
            del Body[Call_Start:]
            for Index, Count in enumerate(Counts):
                Keyword = "if" if Index == 0 else "elif"
                Body.append(f"{Indent}{Keyword} {Configuration} == {100 + Count}:")
                Body.extend("    " + Value.replace(Helper + "(", Helper + f"_Team_{Count}(") for Value in Calls)
            Body.append(f"{Indent}else:")
            Body.extend("    " + Value for Value in Calls)
        if Region:
            if Native and Kind not in ("stencil", "count", "span", "projection", "row_selection"):
                Body.append(f"    return {Plan['Output']}")
            Regions.append(f"cdef object {Baseline} = {Prefix}Baseline({Original!r}, {Prefix}Context, {File.name!r}, {Function.name!r})\n" +
                           f"cdef object {Region_Name}({', '.join('object ' + Name for Name in Names)}):\n" + "\n".join(Body))
        else:
            End = Function.end_lineno if not Native else Node.end_lineno
            Lines[Start - 1:End] = Body
    Header = []
    if Has_Module_Scalars:
        Header.append(_Resource('Module_Runtime.pxi.in').replace('_Pyceler_', Prefix))
    if Has_Scalar_Regions:
        Header.append(_Resource("Scalar_Region_Runtime.pxi.in").replace("_Pyceler_", Prefix).replace("REGION_FILENAME", repr(File.name)))
    if Has_Scalar_Sizing:
        Header.append(_Scalar_Sizing_Runtime.replace("_Pyceler_", Prefix))
    if Tables:
        Runtime = _Resource("Selection_Runtime.pxi.in")
        Fingerprint = _Resource("Selection_Environment.py")
        Match = "True" if Environment is None else f"{Prefix}Environment() == {Environment['Host']!r}"
        Numpy_Check = "" if Environment is None or Environment["NumPy"] is None else f" or {Prefix}Builtins.getattr(Numpy, '__version__', None) != {Environment['NumPy']!r}"
        Header.extend([Fingerprint.replace("_Pyceler_", Prefix), Runtime.replace("_Pyceler_", Prefix).replace("ENVIRONMENT_MATCH", Match).replace("NUMPY_CHECK", Numpy_Check).replace("THREAD_BASELINE", repr(Environment.get("OpenMP_Settings")) if Has_Parallel and Environment else "None").replace("THREAD_CURRENT", f"[{Prefix}Max_Threads(), {Prefix}Dynamic()]" if Has_Parallel else "None"), *Tables])
    if Scalar_Kernels:
        Header.append(f"from builtins import ArithmeticError as {Prefix}ArithmeticError\nclass {Prefix}Overflow({Prefix}ArithmeticError):\n    pass")
    if Regions:
        Header.extend([f"def {Prefix}Context():\n    pass", *reversed(Regions)])
    if Members:
        Loader = _Resource("Package_Loader.pxi.in")
        Package = File.parent.name
        Aliases = {Package: _Member_Alias(Package, Members)} if Package in Members else {}
        Header.append(Loader.replace("_Pyceler_", Prefix).replace("MEMBER_NAMES", repr(Members)).replace("MEMBER_ALIASES", repr(Aliases)))
    if not Edits:
        return _Python_Module("\n".join(Lines), "\n".join(Header), File, Prefix)
    Imports = "from cython.parallel cimport prange as _Pyceler_Prange" if Has_Parallel else ""
    if Has_Parallel:
        Imports += "\nfrom openmp cimport omp_in_parallel as _Pyceler_In_Parallel, omp_get_max_threads as _Pyceler_Max_Threads, omp_get_num_threads as _Pyceler_Reduction_Team, omp_get_dynamic as _Pyceler_Dynamic"
    Common = _Resource("Kernel_Common.pxi.in")
    Parts = [Common.replace("KERNEL_IMPORT", Imports)]
    Parts.extend(reversed(Math_Kernels))
    if Has_Clear:
        Clear = _Resource("Clear_Kernel.pxi.in")
        Chunk = "1 + (Size - 1) // _Pyceler_Max_Threads()" if Choices is not None else "65536"
        Kernel = Clear.replace("    KERNEL_BODY", _Parallel_Body.replace("CHUNK_BYTES", Chunk) if Has_Parallel else "    _Pyceler_Memset(&Data[0], 0, Size)")
        Parts.append(Kernel)
        Parts.extend(_Tuned_Kernel(Kernel, Count) for Count in sorted(Tuned_Clear))
    if Map_Kernels or Structures or Numerics:
        Parts.append(_Resource("Map_Runtime.pxi.in"))
        Parts.extend(reversed(Map_Kernels))
        Parts.extend(reversed(Numerics))
    if Structures:
        Parts.extend(reversed(Structures))
    if Specials:
        Parts.append(_Resource("Region_Runtime.pxi.in"))
        Parts.extend(reversed(Specials))
    if Streams:
        Parts.append(_Resource("Stream_Runtime.pxi.in"))
        Parts.extend(reversed(Streams))
    if Has_Spans:
        Parts.append(_Resource("Span_Runtime.pxi.in"))
    if Scalar_Kernels:
        Parts.append(_Resource("Scalar_Runtime.pxi.in"))
        if Has_Parallel_Scalar:
            Parts.append(_Resource("Scalar_Parallel_Runtime.pxi.in"))
        Parts.extend(reversed(Scalar_Kernels))
    Native_Source = "\n".join(Header) + "\n" + _Native_Prefix("\n".join(Parts), Prefix)
    return _Python_Module("\n".join(Lines), Native_Source, File, Prefix)

cdef str _Parallel_Body = """    cdef Py_ssize_t Block, Offset, Length, Chunk, Chunks
    if not Allow_Threads:
        _Pyceler_Memset(&Data[0], 0, Size)
        return True
    Chunk = CHUNK_BYTES
    Chunks = 1 + (Size - 1) // Chunk
    if Chunks == 1:
        _Pyceler_Memset(&Data[0], 0, Size)
        return True
    from threading import current_thread, main_thread
    if current_thread() is not main_thread() or _Pyceler_In_Parallel():
        _Pyceler_Memset(&Data[0], 0, Size)
    else:
        for Block in _Pyceler_Prange(Chunks, schedule="static", nogil=True):
            Offset = Block * Chunk
            Length = Size - Offset if Size - Offset < Chunk else Chunk
            _Pyceler_Memset(&Data[Offset], 0, Length)"""

cdef tuple _Prepare(object Source_Path, object Output_Directory, str Kind):
    Source, Root, Files = _Inputs(Source_Path)
    if Output_Directory is None:
        Output = Source.parent / (Source.stem + "_" + Kind)
    else:
        Output = Path(Output_Directory).resolve()
    if Source.is_dir() and (Output.is_relative_to(Source) or Source.is_relative_to(Output)):
        raise ValueError("Choose a separate output tree for a source directory")
    return Source, Root, Files, Output

cdef void _Insert_Header(list Lines, object Tree, str Content) except *:
    Header = None
    for Position, Node in enumerate(Tree.body):
        if Position == 0 and isinstance(Node, ast.Expr) and isinstance(Node.value, ast.Constant) and isinstance(Node.value.value, str):
            Header = Node
        elif isinstance(Node, ast.ImportFrom) and Node.module == "__future__":
            Header = Node
        else:
            break
    Insert = 0
    if Header is not None:
        Insert = Header.end_lineno
        Encoded = Lines[Insert - 1].encode("utf-8")
        Tail = Encoded[Header.end_col_offset:].decode("utf-8").lstrip()
        if Tail.startswith(";"):
            Lines[Insert - 1] = Encoded[:Header.end_col_offset].decode("utf-8")
            Lines.insert(Insert, Tail[1:].lstrip())
    Lines.insert(Insert, Content)

cdef tuple _Convert_Files(object Root, list Files, object Staging, object OpenMP, bint Link, bint Select, object Mode, object Version, double Gain,
                          object Workloads=None, object Cache=False, bint Elide_Temporaries=False, object Tuning=None, bint Profile=False):
    import shutil
    from .Source_Inputs import _Stage_Dependencies
    if OpenMP is not None and type(OpenMP) is not bool:
        raise ValueError("OpenMP must be None, True or False")
    if not math.isfinite(Gain) or Gain < 1:
        raise ValueError("Minimum_Speedup must be finite and at least 1")
    Tuning = _Normalize_Tuning(Tuning)
    if not Select and (Tuning or Profile):
        raise ValueError("Tuning and Profile require measured selection")
    if Mode == "auto":
        Mode = "abi" if sys.version_info >= (3, 11) else "simple"
    _Interpreter(Mode, Version)
    Parallel = OpenMP is not False if Select else OpenMP is True
    Relative_Paths = []
    Reports = []
    Supporting = _Stage_Dependencies(Root, Files, Staging)
    Groups = {}
    if Link:
        for File in Files:
            if File.stem != "__init__":
                Groups.setdefault(File.parent, []).append(File.stem)
    for File in Files:
        Relative = File.relative_to(Root)
        if File.suffix == ".py":
            Relative = Relative.with_suffix(".pyx")
        Target = Staging / Relative
        Target.parent.mkdir(parents=True, exist_ok=True)
        Members = tuple(Groups.get(File.parent, ())) if File.name == "__init__.py" else ()
        Prepared = _Plan(File, Parallel, Elide_Temporaries)
        if File.suffix != ".py":
            from .Native_Optimizer import _Convert_Native
            with _Temporary_Workspace(Staging) as Folder:
                Native_Text, Report = _Convert_Native(File, Prepared[0], Folder, Mode, Version, Select, Gain, Cache)
            if Tuning or Profile:
                Report["Options"] = dict(Tuning="Not applicable to serial native bounds elimination", Profile="Native baseline and candidate call timings are reported; Python profiling applies to Python inputs")
            if Native_Text == Prepared[0]:
                shutil.copy2(File, Target)
            else:
                Target.write_text(Native_Text, encoding="utf-8")
            Report_Path = Relative.with_suffix(".selection.json")
            Active = {Item["Line"] for Item in Report["Items"]}
            Report["Skipped"] = [dict(Function=Item.Function, Line=Item.Line, End_Line=Item.End_Line,
                               Source=Item.Source, Reason=Item.Reason, Action=Item.Change) for Item in Prepared[1] if Item.Line not in Active]
            (Staging / Report_Path).write_text(json.dumps(Report, indent=2), encoding="utf-8")
            Reports.append(Report_Path)
            Relative_Paths.append(Relative)
            continue
        Choices = Environment = None
        if Select:
            with _Temporary_Workspace(Staging) as Folder:
                Choices, Environment, Report = _Select_Items(File, Prepared, Folder, Mode, Version, Parallel, Gain, Workloads, Cache, Elide_Temporaries, Tuning, Profile)
            Report_Path = Relative.with_suffix(".selection.json")
            (Staging / Report_Path).write_text(json.dumps(Report, indent=2), encoding="utf-8")
            Reports.append(Report_Path)
        else:
            Report = _Unmeasured_Report(File, Prepared)
            Report_Path = Relative.with_suffix(".selection.json")
            (Staging / Report_Path).write_text(json.dumps(Report, indent=2), encoding="utf-8")
            Reports.append(Report_Path)
        Target.write_text(_Generate(File, Parallel, Members, Choices, Environment, Prepared), encoding="utf-8")
        Relative_Paths.append(Relative)
    return Relative_Paths, Reports, Supporting

def Convert(Source_Path, Output_Directory=None, *, OpenMP=None, Select=True, Minimum_Speedup=1.10, Mode="abi", Python_Version=None,
            Workloads=None, Cache=False, Elide_Temporaries=False, Tuning=None, Profile=False):
    if type(Elide_Temporaries) is not bool:
        raise ValueError("Elide_Temporaries must be True or False")
    if type(Profile) is not bool:
        raise ValueError("Profile must be True or False")
    Source, Root, Files, Output = _Prepare(Source_Path, Output_Directory, "Cython")
    if Source.is_file() and (Output / Source.relative_to(Root).with_suffix(".pyx" if Source.suffix == ".py" else Source.suffix)).resolve() == Source:
        raise ValueError("Choose a separate output directory to preserve the original source")
    with _Workspace() as Stage:
        Paths, Reports, Supporting = _Convert_Files(Root, Files, Stage, OpenMP, False, Select, Mode, Python_Version, Minimum_Speedup,
                                                   Workloads, Cache, Elide_Temporaries, Tuning, Profile)
        Results = _Publish(Stage, Output, Paths + Reports + Supporting, Report_Sources=Paths)[:len(Paths)]
    return Results[0] if Source.is_file() else Results

def Compile(Source_Path, Output_Directory=None, *, Mode="abi", Python_Version=None, Link=False, OpenMP=None, Select=True, Minimum_Speedup=1.10,
            Convert=True, Workloads=None, Cache=False, Elide_Temporaries=False, Tuning=None, Profile=False):
    from .Source_Inputs import _Stage_Compile_Sources
    if type(Convert) is not bool:
        raise ValueError("Convert must be True or False")
    if type(Elide_Temporaries) is not bool:
        raise ValueError("Elide_Temporaries must be True or False")
    if type(Profile) is not bool:
        raise ValueError("Profile must be True or False")
    Tuning = _Normalize_Tuning(Tuning)
    if not Convert and (Workloads is not None or Elide_Temporaries or Tuning or Profile):
        raise ValueError("Workloads, Elide_Temporaries, Tuning and Profile require conversion; compile-only does not analyze or measure candidates")
    Source, Root, Files, Output = _Prepare(Source_Path, Output_Directory, "Native")
    if Source.is_file() and Output == Source.parent:
        raise ValueError("Choose a separate native output directory to avoid shadowing the original module")
    with _Workspace() as Stage:
        if Convert:
            Paths, Reports, Supporting = _Convert_Files(Root, Files, Stage / "Sources", OpenMP, Link, Select, Mode, Python_Version, Minimum_Speedup,
                                                       Workloads, Cache, Elide_Temporaries, Tuning, Profile)
            for Index, Relative in enumerate(Paths):
                if Relative.suffix == ".pxi":
                    Wrapper = Relative.with_suffix(".pyx")
                    (Stage / "Sources" / Wrapper).write_text("include " + json.dumps(Relative.name) + "\n", encoding="utf-8")
                    Paths[Index] = Wrapper
        else:
            Paths, Supporting = _Stage_Compile_Sources(Root, Files, Stage / "Sources")
            Reports = []
        Package_Loaders = not Convert or any(File.name == "__init__.pyx" for File in Files)
        if Cache is not False and Cache is not None:
            Results = _Build(Stage, Paths, Output, Mode, Python_Version, Link, OpenMP, Reports, Package_Loaders=Package_Loaders, Cache=Cache)
        elif Package_Loaders:
            Results = _Build(Stage, Paths, Output, Mode, Python_Version, Link, OpenMP, Reports, Package_Loaders=True)
        else:
            Results = _Build(Stage, Paths, Output, Mode, Python_Version, Link, OpenMP, Reports)
    return Results[0] if Source.is_file() else Results
