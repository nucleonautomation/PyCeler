import io
import json
import re
import subprocess
import sys
import tokenize
from dataclasses import replace
from pathlib import Path
from .Native_Build import _Build, _Interpreter, _Temporary_Workspace
from .Runtime_Resources import _Resource

def _Plans(Text, File=None):
    try:
        Tokens = list(tokenize.generate_tokens(io.StringIO(Text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return []
    if File is not None and Path(File).with_suffix(".pxd").is_file():
        return []
    if any(Value.start[1] == 0 and Value.string in ("@", "include", "cimport", "cdef", "ctypedef", "DEF", "IF") for Value in Tokens) or any(Value.string == "cimport" for Value in Tokens):
        return []
    Significant = [Value for Value in Tokens if Value.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)]
    if any(Value.string == "range" and (Index == 0 or Significant[Index - 1].string != "in") for Index, Value in enumerate(Significant)):
        return []
    Ignored = (tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT, tokenize.ENDMARKER)
    Pattern = (r"def (?P<Name>\w+) \( (?P<Type>int|long long|float|double) \[ : : 1 \] (?P<Buffer>\w+)"
               r"(?: , (?P=Type) (?P<Scalar>\w+))? \) : cdef Py_ssize_t (?P<Index>\w+) "
               r"for (?P=Index) in range \( (?P=Buffer) \. shape \[ 0 \] \) : (?P=Buffer) \[ (?P=Index) \] = (?P<Value>\w+)"
               r"(?: return(?: None)?)?")
    Lines = Text.splitlines()
    Result = []
    for Position, Token in enumerate(Tokens):
        if Token.type != tokenize.NAME or Token.string != "def" or Token.start[1] != 0:
            continue
        if Token.start[0] > 1 and Lines[Token.start[0] - 2].lstrip().startswith("@"):
            continue
        Depth, Entered, Stop = 0, False, Position
        for Stop in range(Position, len(Tokens)):
            Current = Tokens[Stop]
            if Current.type == tokenize.INDENT:
                Depth += 1
                Entered = True
            elif Current.type == tokenize.DEDENT:
                Depth -= 1
                if Entered and Depth == 0:
                    break
        Body = [Value for Value in Tokens[Position:Stop] if Value.type not in Ignored]
        Match = re.fullmatch(Pattern, " ".join(Value.string for Value in Body))
        if Match is None:
            continue
        Plan = Match.groupdict()
        Names = [Plan["Buffer"], Plan["Index"], *([Plan["Scalar"]] if Plan["Scalar"] else [])]
        if len(set(Names)) != len(Names) or set(Names) & {"range", "None"} or Plan["Value"] not in ("0", Plan["Scalar"]):
            continue
        Start, End = Token.start[0], Body[-1].end[0]
        if not Lines[Start - 1].rstrip().endswith("):"):
            continue
        Plan.update(Start=Start, End=End, Loop=next(Value.start[0] for Value in Body if Value.string == "for"),
                    Definition="\n".join(Lines[Start - 1:End]), Dtype={"int": "int32", "long long": "int64", "float": "float32", "double": "float64"}[Plan["Type"]])
        Result.append(Plan)
    return Result

def _Findings(Findings, Plans):
    Lines = {Plan["Loop"] for Plan in Plans}
    return [replace(Item, Classification="Native_Contiguous_Fill", Change="Guarded native bounds-check elimination",
                    Reason="A typed contiguous fill visits indices zero through shape[0]-1; serial bounds-check elimination preserves assignments and exceptions. Native selection compares with unchanged Cython.",
                    Transformations=("native_bounds_elimination",)) if Item.Line in Lines else Item for Item in Findings]

def _Header(Prefix, Environment):
    Match = "True" if Environment is None else f"{Prefix}Environment() == {Environment!r}"
    return ("from cython cimport boundscheck as " + Prefix + "Bounds, wraparound as " + Prefix + "Wrap\n"
            "cdef extern from \"Python.h\":\n    char " + Prefix + "Range_Type \"PyRange_Type\"\n" +
            _Resource("Selection_Environment.py").replace("_Pyceler_", Prefix) + "\n"
            "cdef bint " + Prefix + "Local = " + Match + "\n"
            "cdef bint " + Prefix + "Bindings():\n    import builtins as B\n"
            "    Value = globals().get('range', B.range)\n"
            "    return <void*>Value == <void*>&" + Prefix + "Range_Type\n")

def _Function(Plan, Prefix, Bands):
    Lines = Plan["Definition"].splitlines()
    Arguments = Plan["Buffer"] + (", " + Plan["Scalar"] if Plan["Scalar"] else "")
    Signature = Lines[0][len("def " + Plan["Name"]):]
    Original = Prefix + "Original_" + Plan["Name"]
    Optimized = Prefix + "Optimized_" + Plan["Name"]
    Body = ["    return" if Line.strip() in ("return", "return None") else Line for Line in Lines[1:]]
    Conditions = []
    for Index, (Low, Mode) in enumerate(Bands):
        if Mode != 1:
            continue
        High = Bands[Index - 1][0] if Index else None
        Conditions.append(f"Size >= {Low}" + (f" and Size < {High}" if High is not None else ""))
    Condition = " or ".join("(" + Value + ")" for Value in Conditions) or "False"
    return "\n".join([f"cdef void {Original}{Signature}", *Body,
                       f"@{Prefix}Bounds(False)", f"@{Prefix}Wrap(False)", f"cdef void {Optimized}{Signature}", *Body,
                       Lines[0], f"    if {Plan['Buffer']} is not None and {Prefix}Local and {Prefix}Bindings():",
                       f"        Size = {Plan['Buffer']}.shape[0]", f"        if {Condition}:", f"            {Optimized}({Arguments})", "            return",
                       f"    {Original}({Arguments})"])

def _Generate_Native(Text, Plans, Choices, Environment):
    Prefix = "_Pyceler_Native_"
    while Prefix in Text:
        Prefix += "X"
    Lines = Text.splitlines()
    Active = []
    for Plan in reversed(Plans):
        Bands = Choices.get(Plan["Start"], [])
        if not any(Mode for Low, Mode in Bands):
            continue
        Active.append(Plan)
        Lines[Plan["Start"] - 1:Plan["End"]] = [_Function(Plan, Prefix, Bands)]
    if not Active:
        return Text
    Lines.insert(min(Plan["Start"] for Plan in Active) - 1, _Header(Prefix, Environment))
    return "\n".join(Lines) + "\n"

def _Measure_Native(Request):
    import numpy as Numpy
    from .Selection_Worker import _Load, _Observe, _Time
    from .Selection_Policy import _Selection_Table
    from .Selection_Environment import _Pyceler_Environment
    Spec = json.loads(Request.read_text(encoding="utf-8"))
    Original, Native = (_Load(Path(Value)) for Value in Spec["Modules"])
    Results = []
    for Plan in Spec["Plans"]:
        Functions = {"Python": getattr(Original, Plan["Name"]), "Serial": getattr(Native, Plan["Name"])}
        Cases = []
        for Size in (0, 1, 16, 127, 2048, 8193, 65536):
            Values = Numpy.zeros(Size, dtype=Plan["Dtype"])
            Args = (Values, *([2] if Plan["Scalar"] else []))
            Expected = _Observe(Functions["Python"], Args)[0]
            Valid = _Observe(Functions["Serial"], Args)[0] == Expected
            Timings = _Time(Functions, Args, Size, Spec["Gain"]) if Valid else {}
            Cases.append(dict(Key=Plan["Dtype"], Size=Size, Holdout=Size in (0, 1, 127, 8193),
                              Validation={"Python": "valid", "Serial": "valid" if Valid else "invalid: behavior differs"}, Timings=Timings))
        Table = _Selection_Table(Cases, Spec["Gain"])
        for Case in Cases:
            Case["Validation"]["Original_Cython"] = Case["Validation"].pop("Python")
            if "Python" in Case["Timings"]:
                Case["Timings"]["Original_Cython"] = Case["Timings"].pop("Python")
            for Timing in Case["Timings"].values():
                Timing["Speedup_Vs_Original_Cython"] = Timing.pop("Speedup_Vs_Python")
        Results.append(dict(Function=Plan["Name"], Line=Plan["Loop"], Start=Plan["Start"], Cases=Cases,
                            Dispatch=Table.get(Plan["Dtype"], []), Baseline="Original_Cython", Transformations=["native_bounds_elimination"]))
    Request.with_suffix(".result").write_text(json.dumps(dict(Items=Results, Environment=_Pyceler_Environment()), indent=2), encoding="utf-8")

def _Convert_Native(File, Text, Folder, Mode, Version, Select, Gain, Cache):
    Plans = _Plans(Text, File)
    Report = dict(Format="PyCeler selection 1", Source=str(File), Status="Native Cython source retained", Baseline="Original_Cython", Items=[], Builds={})
    if not Plans:
        return Text, Report
    Choices = {Plan["Start"]: [(0, 1)] for Plan in Plans}
    if not Select:
        Report.update(Status="Unmeasured guarded native candidates", Items=[dict(Function=Plan["Name"], Line=Plan["Loop"], Transformations=["native_bounds_elimination"]) for Plan in Plans])
        return _Generate_Native(Text, Plans, Choices, None), Report
    Command, Floor = _Interpreter(Mode, Version)
    try:
        Modules = []
        Definitions = "\n\n".join(Plan["Definition"] for Plan in Plans)
        Isolated = _Plans(Definitions)
        for Variant in ("Original", "Optimized"):
            with _Temporary_Workspace(Folder) as Stage:
                Sources = Stage / "Sources"
                Sources.mkdir()
                Relative = Path("Native_" + Variant + ".pyx")
                Code = Definitions if Variant == "Original" else _Generate_Native(Definitions, Isolated, {Plan["Start"]: [(0, 1)] for Plan in Isolated}, None)
                (Sources / Relative).write_text(Code, encoding="utf-8")
                Modules.append(str(_Build(Stage, [Relative], Folder, Mode, Floor, False, False, Cache=Cache)[0]))
                Report["Builds"][Variant] = dict(Status="built")
        Request = Folder / "Native_Request.json"
        Request.write_text(json.dumps(dict(Modules=Modules, Plans=Plans, Gain=Gain)), encoding="utf-8")
        Program = "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from PyCeler.Native_Optimizer import _Measure_Native; _Measure_Native(Path(sys.argv[2]))"
        Result = subprocess.run([*Command, "-I", "-B", "-c", Program, str(Path(__file__).resolve().parent.parent), str(Request)], capture_output=True, text=True, timeout=90)
        if Result.returncode:
            raise RuntimeError(Result.stderr[-2000:])
        Measured = json.loads(Request.with_suffix(".result").read_text(encoding="utf-8"))
        Report.update(Measured, Status="Measured native candidates")
        Choices = {Item["Start"]: Item["Dispatch"] for Item in Measured["Items"]}
        return _Generate_Native(Text, Plans, Choices, Measured["Environment"]), Report
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as Error:
        Report.update(Status="Native optimization unavailable; original source retained", Reason=str(Error))
        return Text, Report
