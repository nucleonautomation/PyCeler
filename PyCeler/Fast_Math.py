import ast
import math

_Fast_Math_Version = 3
_Fast_Unary = frozenset(("sqrt", "cbrt", "sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "exp", "exp2", "expm1", "log", "log10", "log1p", "fabs", "isfinite", "isinf", "isnan", "erf", "erfc"))
_Fast_Binary = frozenset(("copysign", "fmod"))
_Fast_Call_Contracts = {Name: dict(Arity=1, Inputs=("numpy", "float", "integer", "boolean"), Return="boolean" if Name in ("isfinite", "isinf", "isnan") else "float",
                                    Strategy="Classifier" if Name in ("isfinite", "isinf", "isnan") else "Unary_Libm", Backend="Runtime_CPython_Libm_Erf" if Name in ("erf", "erfc") else None) for Name in _Fast_Unary}
_Fast_Call_Contracts.update({Name: dict(Arity=2, Inputs=("numpy", "float", "integer", "boolean"), Return="float", Strategy="Binary_Nonzero_Remainder" if Name == "fmod" else "Binary_Libm", Backend=None) for Name in _Fast_Binary})
_Fast_Excluded = dict(log2="The supported interpreter/platform union has not qualified this wrapper against native log2.",
                      gamma="CPython uses a dedicated algorithm.", lgamma="CPython uses a dedicated algorithm.",
                      hypot="CPython uses an accuracy-specific algorithm.", fsum="CPython uses an accuracy-specific algorithm.",
                      remainder="CPython uses a dedicated IEEE remainder algorithm.")

class _Fast_Unsupported(Exception):
    pass

def _Fast_Erf_Backend_Source(Prefix):
    return "\n".join([f"def {Prefix}Erf_Backend(Version):", "    try:",
                      "        return Version.startswith(('3.12.', '3.13.', '3.14.')) and 'PyPy' not in Version and 'Graal' not in Version",
                      "    except Exception:", "        return False"])

def _Fast_Imports(Plan):
    Bindings = {}
    for Text in Plan["Math_Imports"]:
        Node = ast.parse(Text).body[0]
        if isinstance(Node, ast.Import):
            for Alias in Node.names:
                if Alias.name == "math":
                    Bindings[Alias.asname or Alias.name] = None
        elif isinstance(Node, ast.ImportFrom) and Node.module == "math":
            for Alias in Node.names:
                Bindings[Alias.asname or Alias.name] = Alias.name
    return Bindings

def _Fast_Expression(Node, Plan, Bindings, Inputs, Calls):
    if isinstance(Node, ast.Subscript) and isinstance(Node.value, ast.Name) and isinstance(Node.slice, ast.Name):
        if Node.value.id in Plan["Names"] and Node.value.id != Plan["Output"] and Node.slice.id == Plan["Indices"][0]:
            if Node.value.id not in Inputs:
                Inputs.append(Node.value.id)
            return ("input", Inputs.index(Node.value.id)), "numpy"
    if isinstance(Node, ast.Constant) and type(Node.value) in (int, float):
        if type(Node.value) is float and math.isfinite(Node.value) or type(Node.value) is int and abs(Node.value) <= 2**53:
            return ("literal", float(Node.value)), "float" if type(Node.value) is float else "integer"
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, (ast.UAdd, ast.USub)):
        Value, Kind = _Fast_Expression(Node.operand, Plan, Bindings, Inputs, Calls)
        if Kind == "numpy":
            raise _Fast_Unsupported()
        if Kind == "boolean":
            Kind = "integer"
        Operation = "integer_negative" if Kind == "integer" else "negative"
        return ((Operation, Value) if isinstance(Node.op, ast.USub) else Value), Kind
    if isinstance(Node, ast.Call) and not Node.keywords:
        if isinstance(Node.func, ast.Name) and Node.func.id in Bindings:
            Root, Name = Node.func.id, Bindings[Node.func.id]
        elif isinstance(Node.func, ast.Attribute) and isinstance(Node.func.value, ast.Name) and Node.func.value.id in Bindings and Bindings[Node.func.value.id] is None:
            Root, Name = Node.func.value.id, Node.func.attr
        else:
            raise _Fast_Unsupported()
        Contract = _Fast_Call_Contracts.get(Name)
        if Contract is None or len(Node.args) != Contract["Arity"]:
            raise _Fast_Unsupported()
        Arguments = []
        for Argument in Node.args:
            Value, Kind = _Fast_Expression(Argument, Plan, Bindings, Inputs, Calls)
            if Kind not in Contract["Inputs"]:
                raise _Fast_Unsupported()
            Arguments.append(Value)
        Calls.add((Root, Name, Bindings[Root] is None))
        return ("call", Name, tuple(Arguments)), Contract["Return"]
    if isinstance(Node, ast.BinOp) and isinstance(Node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        Left, Left_Kind = _Fast_Expression(Node.left, Plan, Bindings, Inputs, Calls)
        Right, Right_Kind = _Fast_Expression(Node.right, Plan, Bindings, Inputs, Calls)
        if "numpy" in (Left_Kind, Right_Kind) or "float" not in (Left_Kind, Right_Kind):
            raise _Fast_Unsupported()
        Operator = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}[type(Node.op)]
        return ("arithmetic", Operator, Left, Right), "float"
    raise _Fast_Unsupported()

def _Fast_Math_Plan(Plan):
    if len(Plan["Loops"]) != 1 or len(Plan["Indices"]) != 1 or Plan["Scalars"] or Plan["Locals"]:
        return None
    Loop = Plan["Loops"][0]
    if len(Loop.body) != 1 or not isinstance(Loop.body[0], ast.Assign) or len(Loop.body[0].targets) != 1:
        return None
    Statement = Loop.body[0]
    Target = Statement.targets[0]
    if not isinstance(Target, ast.Subscript) or not isinstance(Target.value, ast.Name) or Target.value.id != Plan["Output"]:
        return None
    if not isinstance(Target.slice, ast.Name) or Target.slice.id != Plan["Indices"][0]:
        return None
    Inputs, Calls = [], set()
    try:
        Expression, Kind = _Fast_Expression(Statement.value, Plan, _Fast_Imports(Plan), Inputs, Calls)
    except _Fast_Unsupported:
        return None
    if not Calls or not Inputs or set(Inputs) | {Plan["Output"]} != set(Plan["Names"]):
        return None
    return dict(Version=_Fast_Math_Version, Names=tuple(Plan["Names"]), Inputs=tuple(Inputs), Output=Plan["Output"], Expression=Expression,
                Bindings=tuple(sorted(Calls)), Functions=tuple(sorted({Name for Root, Name, Module in Calls})), Chunk=4096,
                Call_Contracts=tuple((Name, _Fast_Call_Contracts[Name]["Arity"], _Fast_Call_Contracts[Name]["Return"], _Fast_Call_Contracts[Name]["Strategy"]) for Name in sorted({Name for Root, Name, Module in Calls})),
                Backend_Requirements=tuple(sorted({_Fast_Call_Contracts[Name]["Backend"] for Root, Name, Module in Calls if _Fast_Call_Contracts[Name]["Backend"] is not None})),
                Contract="Thin libm float64 calls with validated finite domains, exact original bindings, disjoint buffers, ordered continuation and bounded observer checks")

def _Fast_Emit(Node, Lines, Variables, Functions, Prefix):
    Kind = Node[0]
    if Kind == "input":
        return "X" + str(Node[1])
    if Kind == "literal":
        return repr(Node[1])
    Target = "T" + str(len(Variables))
    Variables.append(Target)
    if Kind in ("negative", "integer_negative"):
        Operand = _Fast_Emit(Node[1], Lines, Variables, Functions, Prefix)
        Value = f"0.0 if {Operand} == 0.0 else -{Operand}" if Kind == "integer_negative" else f"-{Operand}"
        Lines.append(f"    {Target} = {Value}")
    elif Kind == "arithmetic":
        Left = _Fast_Emit(Node[2], Lines, Variables, Functions, Prefix)
        Right = _Fast_Emit(Node[3], Lines, Variables, Functions, Prefix)
        if Node[1] == "/":
            Lines.extend([f"    if {Right} == 0.0:", "        Valid[0] = False", "        return 0.0"])
        Lines.append(f"    {Target} = {Left} {Node[1]} {Right}")
        Lines.extend([f"    if not {Prefix}isfinite({Target}):", "        Valid[0] = False", "        return 0.0"])
    else:
        Name = Node[1]
        Contract = _Fast_Call_Contracts[Name]
        Operands = []
        for Argument in Node[2]:
            Value = _Fast_Emit(Argument, Lines, Variables, Functions, Prefix)
            Operand = "T" + str(len(Variables))
            Variables.append(Operand)
            Lines.append(f"    {Operand} = {Value}")
            Operands.append(Operand)
        Operand = Operands[0]
        Domain = {"sqrt": f"{Operand} < 0.0", "asin": f"{Operand} < -1.0 or {Operand} > 1.0", "acos": f"{Operand} < -1.0 or {Operand} > 1.0",
                  "acosh": f"{Operand} < 1.0", "atanh": f"{Operand} <= -1.0 or {Operand} >= 1.0", "log": f"{Operand} <= 0.0",
                  "log10": f"{Operand} <= 0.0", "log1p": f"{Operand} <= -1.0"}.get(Name)
        if Domain:
            Lines.extend([f"    if {Domain}:", "        Valid[0] = False", "        return 0.0"])
        if Contract["Arity"] == 2:
            for Argument in Operands:
                Lines.extend([f"    if not {Prefix}isfinite({Argument}) or ({Argument} == 0.0 and {Prefix}signbit({Argument})):", "        Valid[0] = False", "        return 0.0"])
            if Contract["Strategy"] == "Binary_Nonzero_Remainder":
                Lines.extend([f"    if {Operands[1]} == 0.0:", "        Valid[0] = False", "        return 0.0"])
        if Contract["Strategy"] == "Classifier":
            Lines.append(f"    {Target} = 1.0 if {Prefix}{Name}({Operand}) else 0.0")
        else:
            Lines.append(f"    {Prefix}Reset_Errno()")
            Value = f"({Operand} if {Operand} == 0.0 else {Prefix}log1p({Operand}))" if Name == "log1p" else f"{Prefix}{Name}({', '.join(Operands)})"
            Lines.append(f"    {Target} = {Value}")
            Lines.extend([f"    if not {Prefix}isfinite({Target}) or ({Prefix}Read_Errno() != 0 and not ({Prefix}Read_Errno() == {Prefix}ERANGE and {Prefix}fabs({Target}) < 1.5)):",
                          "        Valid[0] = False", "        return 0.0"])
            if Contract["Strategy"] == "Binary_Nonzero_Remainder":
                Lines.extend([f"    if {Target} == 0.0:", "        Valid[0] = False", "        return 0.0"])
    return Target

def _Fast_Math_Kernel(Plan, Line, Parallel=False):
    Prefix = f"_Pyceler_Fast_{Line}_"
    Functions = sorted(set(Plan["Functions"]) | {"isfinite", "isinf", "isnan", "fabs", "signbit"})
    Lines = ["from libc.math cimport " + ", ".join(Name + " as " + Prefix + Name for Name in Functions),
             f"from libc.stdlib cimport malloc as {Prefix}Allocate, free as {Prefix}Free",
             "from libc.stdint cimport uintptr_t as " + Prefix + "Address", "from cython cimport boundscheck as " + Prefix + "Bounds, wraparound as " + Prefix + "Wrap, cdivision as " + Prefix + "Division",
             "from libc.errno cimport ERANGE as " + Prefix + "ERANGE",
             'cdef extern from "Python.h":', f'    int {Prefix}Signals "PyErr_CheckSignals"() except -1',
             'cdef extern from "fenv.h":', f'    int {Prefix}Nearest "FE_TONEAREST"', f'    int {Prefix}Rounding "fegetround"() noexcept nogil',
             f'    ctypedef struct {Prefix}Environment "fenv_t":', '        pass',
             f'    int {Prefix}Get_Environment "fegetenv"({Prefix}Environment*) noexcept nogil', f'    int {Prefix}Set_Environment "fesetenv"(const {Prefix}Environment*) noexcept nogil',
             f'    ctypedef struct {Prefix}Exception_State "fexcept_t":', '        pass', f'    int {Prefix}All_Exceptions "FE_ALL_EXCEPT"',
             f'    int {Prefix}Test_Exceptions "fetestexcept"(int) noexcept nogil', f'    int {Prefix}Set_Exceptions "fesetexceptflag"(const {Prefix}Exception_State*, int) noexcept nogil',
             'cdef extern from *:', '    """', '    #include <errno.h>',
             f'    static void {Prefix}Reset_Errno(void) {{ errno = 0; }}', f'    static int {Prefix}Read_Errno(void) {{ return errno; }}',
             f'    static int {Prefix}Prepare_Exceptions(int Flags, fexcept_t* Prepared) {{',
             '        fenv_t Saved;', '        int Result;', '        if (feholdexcept(&Saved) != 0) return -1;', '        Result = feraiseexcept(Flags);',
             '        if (Result == 0) Result = fegetexceptflag(Prepared, Flags);', '        if (fesetenv(&Saved) != 0) return -1;', '        return Result;', '    }',
             '    """', f'    void {Prefix}Reset_Errno() noexcept nogil', f'    int {Prefix}Read_Errno() noexcept nogil',
             f'    int {Prefix}Prepare_Exceptions(int, {Prefix}Exception_State*) noexcept nogil']
    if Parallel:
        Lines.extend(["from cython.parallel cimport prange as " + Prefix + "Prange", "from openmp cimport omp_get_num_threads as " + Prefix + "Team_Size, omp_get_max_threads as " + Prefix + "Max_Threads, omp_in_parallel as " + Prefix + "In_Parallel"])
    if "Runtime_CPython_Libm_Erf" in Plan.get("Backend_Requirements", ()):
        Lines.extend(['cdef extern from "Python.h":', f'    const char* {Prefix}Runtime_Version "Py_GetVersion"()', _Fast_Erf_Backend_Source(Prefix), f'cdef bint {Prefix}Erf_Backend_Eligible = {Prefix}Erf_Backend((<bytes>{Prefix}Runtime_Version()).decode("ascii"))'])
    Lines.extend(["import math as " + Prefix + "Math", "import types as " + Prefix + "Types", "import builtins as " + Prefix + "Builtins",
                  "import sys as " + Prefix + "System", "import signal as " + Prefix + "Signal", "import threading as " + Prefix + "Threading",
                  f"cdef tuple {Prefix}Functions = tuple(getattr({Prefix}Math, Name, None) for Name in {Plan['Functions']!r})",
                  f"cdef unsigned long long {Prefix}Native_Elements = 0, {Prefix}Parallel_Elements = 0", f"cdef int {Prefix}Last_Team = 0",
                  f"def {Prefix}Stats():", f"    return dict(Native_Elements={Prefix}Native_Elements, Parallel_Elements={Prefix}Parallel_Elements, Team={Prefix}Last_Team)",
                  f"cdef bint {Prefix}Exclusive():", f"    S = {Prefix}System", f"    G = {Prefix}Signal", f"    T = {Prefix}Threading",
                  f"    if {Prefix}Rounding() != {Prefix}Nearest or T.current_thread() is not T.main_thread() or len(S._current_frames()) != 1 or S.gettrace() is not None or S.getprofile() is not None:",
                  "        return False", "    for Number in G.valid_signals():", "        Handler = G.getsignal(Number)",
                  "        if Handler is not None and Handler is not G.SIG_DFL and Handler is not G.SIG_IGN and Handler is not G.default_int_handler:", "            return False", "    return True",
                  f"cdef bint {Prefix}Bindings(dict Namespace):", "    cdef object Function, Module"])
    for Position, Name in enumerate(Plan["Functions"]):
        Lines.extend([f"    Function = {Prefix}Functions[{Position}]", f"    if {Prefix}Builtins.type(Function) is not {Prefix}Types.BuiltinFunctionType or Function.__self__ is not {Prefix}Math or Function.__name__ != {Name!r}:", "        return False",
                      f"    if {Prefix}Builtins.getattr({Prefix}Math, {Name!r}, None) is not Function:", "        return False"])
    for Root, Name, Module in Plan["Bindings"]:
        Position = Plan["Functions"].index(Name)
        Test = f"Namespace.get({Root!r}) is not {Prefix}Math" if Module else f"Namespace.get({Root!r}) is not {Prefix}Functions[{Position}]"
        Lines.extend(["    if " + Test + ":", "        return False"])
    Lines.append("    return True")
    Evaluation, Variables = [], []
    Result = _Fast_Emit(Plan["Expression"], Evaluation, Variables, Functions, Prefix)
    Parameters = ", ".join([*("double X" + str(Index) for Index in range(len(Plan["Inputs"]))), "bint* Valid"])
    Lines.extend([f"@{Prefix}Division(True)", f"cdef inline double {Prefix}Value({Parameters}) noexcept nogil:"])
    if Variables:
        Lines.append("    cdef volatile double " + ", ".join(Variables))
    for Index in range(len(Plan["Inputs"])):
        Lines.extend([f"    if not {Prefix}isfinite(X{Index}) or (X{Index} == 0.0 and {Prefix}signbit(X{Index})):", "        Valid[0] = False", "        return 0.0"])
    Lines.extend(Evaluation)
    Lines.append("    return " + Result)
    Source_Slots = [Plan["Names"].index(Name) for Name in Plan["Inputs"]]
    Output_Slot = Plan["Names"].index(Plan["Output"])
    Input_Parameters = [f"const double[::1] I{Index}" for Index in range(len(Source_Slots))]
    Value_Call = f"{Prefix}Value(" + ", ".join([*(f"I{Index}[Position]" for Index in range(len(Source_Slots))), "&Valid"]) + ")"
    Lines.extend([f"@{Prefix}Bounds(False)", f"@{Prefix}Wrap(False)", f"cdef bint {Prefix}Evaluate({', '.join([*Input_Parameters, 'double* Scratch', 'Py_ssize_t Begin', 'Py_ssize_t End', 'Py_ssize_t Offset', 'const ' + Prefix + 'Environment* Environment', 'int* Exceptions'])}) noexcept nogil:",
                  "    cdef bint Valid = True", "    cdef Py_ssize_t Position", f"    cdef {Prefix}Environment Previous", f"    {Prefix}Get_Environment(&Previous)", f"    {Prefix}Set_Environment(Environment)",
                  "    for Position in range(Begin, End):", "        Scratch[Position - Offset] = " + Value_Call, "        if not Valid:", "            break",
                  f"    Exceptions[0] = {Prefix}Test_Exceptions({Prefix}All_Exceptions)", f"    {Prefix}Set_Environment(&Previous)", "    return Valid"])
    Lines.extend([f"@{Prefix}Bounds(False)", f"@{Prefix}Wrap(False)", f"cdef void {Prefix}Commit(double* Scratch, double[::1] Output, Py_ssize_t Begin, Py_ssize_t End) noexcept nogil:",
                  "    cdef Py_ssize_t Position", "    for Position in range(Begin, End):", "        Output[Position] = Scratch[Position - Begin]"])
    Lines.extend([f"cdef Py_ssize_t _Pyceler_Fast_Math_{Line}(tuple Args, object Baseline, object Iterator, bint Allow_Threads, int Thread_Count) except -1:",
                  "    import numpy as N", "    import builtins as B", "    cdef dict Namespace = Baseline.__globals__", "    cdef Py_ssize_t Size, Done = 0, End, Part, Parts",
                  f"    cdef bint Checks[{Plan['Chunk']}]", "    cdef bint Valid, Used_Parallel", f"    cdef int Exceptions[{Plan['Chunk']}]", "    cdef int Flags", "    cdef double* Scratch = NULL",
                  "    cdef object Array", f"    cdef {Prefix}Address Output_Begin, Output_End, Input_Begin, Input_End", f"    cdef {Prefix}Environment Environment", f"    cdef {Prefix}Exception_State Prepared",
                  "    cdef double[::1] Output", f"    global {Prefix}Native_Elements, {Prefix}Parallel_Elements, {Prefix}Last_Team"])
    for Index in range(len(Source_Slots)):
        Lines.append(f"    cdef const double[::1] I{Index}")
    if Parallel:
        Lines.extend(["    cdef int Team[1]", "    cdef int Workers"])
    if "Runtime_CPython_Libm_Erf" in Plan.get("Backend_Requirements", ()):
        Lines.extend([f"    if not {Prefix}Erf_Backend_Eligible:", "        return 0"])
    Lines.extend([f"    if len(Args) != {len(Plan['Names'])} or B.type(Iterator) is not B.range or Iterator.start != 0 or Iterator.step != 1:", "        return 0",
                  "    for Array in Args:", "        if B.type(Array) is not N.ndarray or Array.ndim != 1 or Array.dtype != N.dtype('float64') or Array.dtype.metadata is not None or not Array.flags.c_contiguous or not Array.flags.aligned:", "            return 0",
                  f"    if not Args[{Output_Slot}].flags.writeable:", "        return 0", f"    Size = Args[{Output_Slot}].shape[0]",
                  "    if Iterator.stop != Size or any(Array.shape[0] != Size for Array in Args):", "        return 0", "    if Size == 0:", "        return 0",
                  f"    Output = Args[{Output_Slot}]", f"    Output_Begin = <{Prefix}Address>&Output[0]", "    Output_End = Output_Begin + Size * sizeof(double)"])
    for Index, Slot in enumerate(Source_Slots):
        Lines.extend([f"    I{Index} = Args[{Slot}]", f"    Input_Begin = <{Prefix}Address>&I{Index}[0]", "    Input_End = Input_Begin + Size * sizeof(double)",
                      "    if Input_Begin < Output_End and Output_Begin < Input_End:", "        return 0"])
    View_Args = ", ".join(f"I{Index}" for Index in range(len(Source_Slots)))
    Lines.extend([f"    Scratch = <double*>{Prefix}Allocate({Plan['Chunk']} * sizeof(double))", "    if Scratch == NULL:", "        return 0", "    try:", "        while Done < Size:",
                  f"            if not {Prefix}Exclusive() or not {Prefix}Bindings(Namespace):", "                return Done",
                  f"            End = min(Size, Done + {Plan['Chunk']})", f"            if {Prefix}Get_Environment(&Environment) != 0:", "                return Done",
                  "            Used_Parallel = False", "            Parts = 1"])
    Evaluate_Call = f"{Prefix}Evaluate({View_Args}, Scratch, Done, End, Done, &Environment, &Exceptions[0])"
    if Parallel:
        Lines.extend([f"            if Allow_Threads and not {Prefix}In_Parallel():", "                Used_Parallel = True", "                Team[0] = 1",
                      f"                Workers = Thread_Count if Thread_Count > 0 else {Prefix}Max_Threads()", "                Parts = min(End - Done, Workers)",
                      f"                for Part in {Prefix}Prange(Parts, nogil=True, schedule='static', num_threads=Workers):",
                      "                    if Part == 0:", f"                        Team[0] = {Prefix}Team_Size()",
                      f"                    Checks[Part] = {Prefix}Evaluate({View_Args}, Scratch, Done + (End - Done) * Part // Parts, Done + (End - Done) * (Part + 1) // Parts, Done, &Environment, &Exceptions[Part])",
                      "            else:", "                with nogil:", "                    Checks[0] = " + Evaluate_Call])
    else:
        Lines.extend(["            with nogil:", "                Checks[0] = " + Evaluate_Call])
    Lines.extend(["            Valid = True", "            Flags = 0", "            for Part in range(Parts):", "                Valid = Valid and Checks[Part]", "                Flags |= Exceptions[Part]",
                  f"            if not Valid or not {Prefix}Exclusive() or not {Prefix}Bindings(Namespace) or not Args[{Output_Slot}].flags.writeable:", "                return Done",
                  f"            if Flags and {Prefix}Prepare_Exceptions(Flags, &Prepared) != 0:", "                return Done", f"            {Prefix}Commit(Scratch, Output, Done, End)",
                  "            if Flags:", f"                {Prefix}Set_Exceptions(&Prepared, Flags)"])
    if Parallel:
        Lines.extend(["            if Used_Parallel:", f"                {Prefix}Parallel_Elements += End - Done", f"                {Prefix}Last_Team = Team[0]",
                      "                _Pyceler_Dispatch_Event('Execution', 'native_parallel', Team[0])", "            else:", f"                {Prefix}Last_Team = 1", "                _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)"])
    else:
        Lines.extend([f"            {Prefix}Last_Team = 1", "            _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)"])
    Lines.extend([f"            {Prefix}Native_Elements += End - Done", "            Done = End", f"            {Prefix}Signals()", "            with nogil:", "                pass", "        return Done", "    finally:", f"        {Prefix}Free(Scratch)"])
    return "\n".join(Lines) + "\n"
