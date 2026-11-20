import ast
import copy
from .Fast_Math import _Fast_Call_Contracts, _Fast_Statements, _Fast_Emit_Program, _Fast_Math_Kernel, _Fast_Unsupported
# Extract supported scalar math operations and retain observer, binding and floating-point guards.
def _Fresh(Node):
    if isinstance(Node, ast.IfExp):
        return _Fresh(Node.body) and _Fresh(Node.orelse)
    if isinstance(Node, ast.Call):
        return True
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.UAdd):
        return _Fresh(Node.operand)
    if isinstance(Node, ast.BinOp) or isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.USub):
        return any(isinstance(Part, (ast.Name, ast.Call)) for Part in ast.walk(Node))
    return False

def _Flow(Statements, Defined, Fresh, Inputs, Written, Roots, Index):
    for Node in Statements:
        if isinstance(Node, ast.If):
            Values = [Node.test]
        elif isinstance(Node, ast.Assign) and len(Node.targets) == 1 and isinstance(Node.targets[0], ast.Name):
            Target, Value = Node.targets[0].id, Node.value
            Values = [Value]
        elif isinstance(Node, ast.AugAssign) and isinstance(Node.target, ast.Name):
            Target = Node.target.id
            Value = ast.BinOp(left=ast.Name(id=Target, ctx=ast.Load()), op=Node.op, right=Node.value)
            Values = [Value]
        elif isinstance(Node, ast.Pass):
            continue
        else:
            raise _Fast_Unsupported()
        for Value in Values:
            for Part in ast.walk(Value):
                if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Load) and Part.id not in Defined | Roots and Part.id not in Inputs:
                    Inputs.append(Part.id)
        if isinstance(Node, ast.If):
            Yes, No = Defined.copy(), Defined.copy()
            Yes_Fresh, No_Fresh = Fresh.copy(), Fresh.copy()
            _Flow(Node.body, Yes, Yes_Fresh, Inputs, Written, Roots, Index)
            _Flow(Node.orelse, No, No_Fresh, Inputs, Written, Roots, Index)
            Defined.update(Yes & No)
            Fresh.intersection_update(Yes_Fresh & No_Fresh)
            Fresh.update(Yes_Fresh & No_Fresh)
        else:
            if Target in Roots | {Index, "range"}:
                raise _Fast_Unsupported()
            Defined.add(Target)
            if Target not in Written:
                Written.append(Target)
            if _Fresh(Value):
                Fresh.add(Target)
            else:
                Fresh.discard(Target)

def _Scalar_Math_Plan(Function, Loop, Available, Scope):
    if not isinstance(Loop, ast.For) or not isinstance(Loop.target, ast.Name):
        return None
    Call = Loop.iter
    if not isinstance(Call, ast.Call) or not isinstance(Call.func, ast.Name) or Call.func.id != "range" or Call.keywords or not 1 <= len(Call.args) <= 3:
        return None
    try:
        Step = ast.literal_eval(Call.args[2]) if len(Call.args) == 3 else 1
    except (ValueError, TypeError):
        return None
    if type(Step) is not int or Step == 0 or abs(Step) > 2**31 - 1:
        return None
    Index, Bindings = Loop.target.id, {}
    for Node in ast.walk(ast.Module(body=Loop.body, type_ignores=[])):
        if isinstance(Node, ast.Call):
            Target = Node.func
            if isinstance(Target, ast.Attribute) and isinstance(Target.value, ast.Name):
                Root, Name, Binding = Target.value.id, Target.attr, None
            elif isinstance(Target, ast.Name):
                Root, Name, Binding = Target.id, Target.id, Target.id
            else:
                return None
            Contract = _Fast_Call_Contracts.get(Name)
            if Contract is None or Contract["Return"] != "float" or Root in Bindings and Bindings[Root] != Binding:
                return None
            Bindings[Root] = Binding
    if not Bindings or Index in Bindings or Index == "range":
        return None
    Inputs, Written, Defined, Fresh = [], [], {Index}, set()
    try:
        _Flow(Loop.body, Defined, Fresh, Inputs, Written, set(Bindings), Index)
        if not Written or not set(Inputs) <= Available or not set(Written) <= Defined & Fresh or "range" in Inputs:
            return None
        Context = dict(Local_Types={Name: "float" for Name in Inputs}, Local_Slots=[*Inputs, Index], Names=(), Indices=(Index,), Output="", Result_Name="")
        Context["Local_Types"][Index] = "integer"
        Calls = set()
        Program = _Fast_Statements(Loop.body, Context, Bindings, [], Calls)
        if any(Context["Local_Types"].get(Name) != "float" for Name in Written):
            return None
    except _Fast_Unsupported:
        return None
    Stop, Begin = "_Pyceler_Stop", "_Pyceler_Begin"
    Used = set(Inputs) | set(Written) | {Index}
    while Stop in Used:
        Stop += "_X"
    while Begin in Used:
        Begin += "_X"
    Names = (Stop, Begin, *Inputs)
    Outputs = (*Written, Index)
    Protected = tuple(Name for Name in Outputs if Name in Available and Name not in Inputs)
    if isinstance(Function, ast.FunctionDef) and not any(isinstance(Node, ast.Global) for Node in Function.body):
        Inside = set(ast.walk(Loop))
        Uncertain = {Node.id for Node in ast.walk(Function) if Node not in Inside and isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Store)}
        if (set(Outputs) & Uncertain) - Available:
            return None
    Definition = ast.parse(f"def _Pyceler_Probe({', '.join(Names)}):\n    pass").body[0]
    Candidate = copy.deepcopy(Loop)
    Candidate.iter = ast.parse(f"range({Begin}, {Stop}, {Step})", mode="eval").body
    Candidate.orelse = []
    Definition.body = [ast.parse(f"{Index} = {Begin}").body[0], Candidate, ast.parse("return (" + ", ".join(Outputs) + ",)").body[0]]
    Math = dict(Functions=tuple(sorted({Name for Root, Name, Module in Calls})), Bindings=tuple(sorted(Calls)), Program=Program, Slots=Context["Local_Slots"],
                Backend_Requirements=tuple(sorted({_Fast_Call_Contracts[Name]["Backend"] for Root, Name, Module in Calls if _Fast_Call_Contracts[Name]["Backend"]})))
    Imports = tuple("import math as " + Root if Binding is None else "from math import " + Binding + " as " + Root for Root, Binding in Bindings.items())
    return dict(Kind="scalar_region", Scalar_Math=Math, Math_Imports=Imports, Output_Guards=Protected, Names=Names, Inputs=tuple(Inputs), Outputs=Outputs, Index=Index, Slots={}, Temporaries=[], Lines=[],
                Loops=[Loop], Start=Loop.lineno, Region=True, Scope=Scope, Period=None, Step=Step, Reporting=None, Statements=Loop.body, Size_Arguments=(0,),
                Transformations=("Ordered scalar math recurrence", "Guarded native float64 calls"), Probe=ast.fix_missing_locations(Definition))

def _Scalar_Math_Kernel(Plan, Line, Module=False):
    Math = Plan["Scalar_Math"]
    Prefix = f"_Pyceler_Fast_{Line}_"
    Slots = Math["Slots"]
    Work, Variables = [], ["L" + str(Index) for Index in range(len(Slots))]
    _Fast_Emit_Program(Math["Program"], Work, Variables, Math["Functions"], Prefix)
    Types = [f"from cpython.float cimport PyFloat_CheckExact as {Prefix}Exact_Float", f"from cpython.long cimport PyLong_CheckExact as {Prefix}Exact_Integer", f"from cpython.bool cimport PyBool_Check as {Prefix}Boolean"]
    Lines = [_Fast_Math_Kernel(Math, Line, Preamble=True), *Types, f"@{Prefix}Division(True)", f"cdef inline bint {Prefix}Step(double* State, bint* Valid, int* Error) noexcept nogil:"]
    for Start, Type in (("L", "double"), ("T", "volatile double")):
        Group = [Name for Name in Variables if Name.startswith(Start)]
        if Group:
            Lines.append("    cdef " + Type + " " + ", ".join(Group))
    Lines.extend(f"    L{Index} = State[{Index}]" for Index in range(len(Slots)))
    Lines.extend(Text.replace("return 0.0", "return False") for Text in Work)
    Lines.extend(f"    State[{Slots.index(Name)}] = L{Slots.index(Name)}" for Name in Plan["Outputs"] if Name != Plan["Index"])
    Lines.append("    return True")
    Name = f"_Pyceler_Module_Span_{Line}" if Module else f"_Pyceler_Scalar_Region_{Line}"
    Guards = [] if Module else [f"object G{Index}" for Index in range(len(Plan["Output_Guards"]))]
    Parameters = ", ".join([*(f"object A{Index}" for Index in range(len(Plan["Names"]))), "dict Namespace", *Guards])
    Lines.extend([f"cdef object {Name}({Parameters}):", "    import builtins as B", f"    cdef double State[{len(Slots)}]", "    cdef _Pyceler_Int Cursor, Begin, Stop, Last", "    cdef bint Valid = True", "    cdef int Flags", "    cdef int* Error", f"    cdef {Prefix}Environment Saved", f"    cdef {Prefix}Exception_State Prepared", f"    global {Prefix}Native_Elements, {Prefix}Last_Team"])
    if not Module:
        Lines.extend(["    global _Pyceler_Region_Attempts", "    _Pyceler_Region_Attempts += 1"])
    for Position, Output in enumerate(Plan["Outputs"] if Module else Plan["Output_Guards"]):
        Value = f"Namespace.get({Output!r})" if Module else f"G{Position}"
        Lines.extend([f"    Previous = {Value}", f"    if not ({Prefix}Exact_Float(Previous) or {Prefix}Exact_Integer(Previous) or {Prefix}Boolean(Previous) or Previous is None):", "        return None"])
    Lines.extend([f"    if not {Prefix}Exact_Integer(A0) or not {Prefix}Exact_Integer(A1) or not -9007199254740992 <= A0 <= 9007199254740992 or not -9007199254740992 <= A1 <= 9007199254740992:", "        return None", "    Stop, Begin = A0, A1"])
    Step = Plan["Step"]
    Lines.extend([f"    if Begin {'>=' if Step > 0 else '<='} Stop or abs(Stop - Begin) > 65536 * {abs(Step)}:", "        return None"])
    if Math["Backend_Requirements"]:
        Lines.extend([f"    if not {Prefix}Erf_Backend_Eligible:", "        return None"])
    Lines.extend([f"    if not {Prefix}Exclusive() or not {Prefix}Bindings(Namespace):", "        return None"])
    Lines.extend(f"    State[{Index}] = 0.0" for Index in range(len(Slots)))
    for Position, Input in enumerate(Plan["Inputs"], 2):
        Lines.extend([f"    if not {Prefix}Exact_Float(A{Position}):", "        return None", f"    State[{Slots.index(Input)}] = A{Position}", f"    if not {Prefix}Finite(State[{Slots.index(Input)}]):", "        return None"])
    Lines.append(f"    Error = {Prefix}Error_Address()")
    Lines.extend([f"    if {Prefix}Get_Environment(&Saved) != 0:", "        return None", "    Cursor = Begin", f"    while Cursor {'<' if Step > 0 else '>'} Stop:", "        Last = Cursor", f"        State[{Slots.index(Plan['Index'])}] = Cursor", f"        if not {Prefix}Step(State, &Valid):", "            break", f"        Cursor += {Step}", f"    Flags = {Prefix}Test_Exceptions({Prefix}All_Exceptions)", f"    {Prefix}Set_Environment(&Saved)", "    if not Valid:", "        return None", f"    if Flags and {Prefix}Prepare_Exceptions(Flags, &Prepared) != 0:", "        return None", f"    Result = ({', '.join('Last' if Name == Plan['Index'] else 'State[' + str(Slots.index(Name)) + ']' for Name in Plan['Outputs'])},)", "    if Flags:", f"        {Prefix}Set_Exceptions(&Prepared, Flags)", f"    {Prefix}Native_Elements += (Cursor - Begin) // ({Step})", f"    {Prefix}Last_Team = 1", "    return Result"])
    return ("\n".join(Lines) + "\n").replace("Step(State, &Valid)", "Step(State, &Valid, Error)")

def _Scalar_Math_Module_Kernel(Plan, Line, Filename, Prefix, Measured, Future_Features, Constant_Kernel):
    Template = f"_Pyceler_Math_Region_{Line}_"
    Fallback = copy.deepcopy(Plan["Loops"][0])
    Fallback.orelse = []
    Fallback.iter = ast.Name(id=Prefix + "Module_Iterator", ctx=ast.Load())
    Text = ast.unparse(ast.fix_missing_locations(Fallback))
    Lines = [Constant_Kernel, _Scalar_Math_Kernel(Plan, Line, True), f"import builtins as {Template}Builtins", f"import __future__ as {Template}Future", f"cdef int {Template}Flags = 0"]
    Lines.extend(f"{Template}Flags |= {Template}Future.{Name}.compiler_flag" for Name in Future_Features)
    Lines.extend([f"cdef object {Template}Fallback = {Template}Builtins.compile({Text!r}, {Filename!r}, 'exec', flags={Template}Flags, dont_inherit=True)", f"cdef void _Pyceler_Module_Run_{Line}(object Namespace, object Iterator, bint Allow_Threads, object Policy, object Source_Code) except *:", "    import builtins as B", "    global _Pyceler_Module_Native, _Pyceler_Module_Fallbacks, _Pyceler_Module_Team", "    Fallback = None", f"    Ranged = _Pyceler_Region_Range(Iterator, {Plan['Step']})", "    for Block in _Pyceler_Module_Blocks(Iterator, B.len(Iterator) if Ranged else None):", "        Result = None"])
    Guard = " and ".join(f"{Name!r} in Namespace" for Name in Plan["Inputs"]) or "True"
    if Measured:
        Guard += " and (Policy is None or _Pyceler_Choose((B.len(Block),), True, Policy))"
    Args = ", ".join(["Block.stop", "Block.start", *(f"Namespace[{Name!r}]" for Name in Plan["Inputs"]), "Namespace"])
    Lines.extend([f"        if Ranged and {Guard}:", f"            Result = _Pyceler_Module_Span_{Line}({Args})", "        if Result is None:", "            if Fallback is None:", f"                Pool = _Pyceler_Module_Constants_{Line}_Pool(Source_Code)", f"                Fallback = _Pyceler_Module_Constants_{Line}_Code({Template}Fallback, Pool)", "            _Pyceler_Module_Fallbacks += 1", "            _Pyceler_Dispatch_Event('Execution', 'python_fallback', 0)", "            _Pyceler_Module_Python_Block(Namespace, Block, Fallback)", "        else:"])
    Lines.extend(f"            Namespace[{Name!r}] = Result[{Position}]" for Position, Name in enumerate(Plan["Outputs"]))
    Lines.extend(["            _Pyceler_Module_Native += 1", "            _Pyceler_Module_Team = 1", "            _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)", "            _Pyceler_Module_Checkpoint()"])
    return "\n".join(Lines) + "\n"
