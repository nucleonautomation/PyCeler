import ast
import math
from .Array_Expressions import _Array_Emit, _Array_Emitted_Tag
from .Buffer_Indices import _Buffer_Offset, _Buffer_Coordinate
from .Common_Calls import _Helper_Expression, _Helper_Emit
from .Native_Observers import _Monitoring_Kernel
# Lower supported numeric expressions with exact operation order, domain guards and explicit libm contracts.
_Fast_Math_Version = 4
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
# The IR describes semantics, not just C syntax; unsupported operations keep their ordinary path.
def _Fast_Expression(Node, Plan, Bindings, Inputs, Calls):
    if isinstance(Node, ast.Name) and Node.id in Plan.get('Helper_Parameters', {}):
        return Plan['Helper_Parameters'][Node.id]
    if isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id in Plan.get('Helpers', {}) and Node.func.id not in Plan.get('Helper_Parameters', {}):
        return _Helper_Expression(Node, Plan, Bindings, Inputs, Calls, _Fast_Expression, _Fast_Unsupported)
    if isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id == 'abs' and 'abs' in Plan.get('Builtins', ()) and not Node.keywords and len(Node.args) == 1:
        Value, Kind = _Fast_Expression(Node.args[0], Plan, Bindings, Inputs, Calls)
        return ('absolute', Value), 'integer' if Kind == 'boolean' else Kind
    if Plan.get('Array_Region') and isinstance(Node, ast.Call) and not Node.keywords:
        if (getattr(Node, 'lineno', 0), getattr(Node, 'col_offset', 0)) in Plan['Random']:
            return ('array_random',), 'float'
        if isinstance(Node.func, ast.Name) and Node.func.id in Plan['Builtins']:
            Values = [_Fast_Expression(Value, Plan, Bindings, Inputs, Calls) for Value in Node.args]
            if Node.func.id in ('int', 'float') and len(Values) == 1:
                return ('array_cast_' + Node.func.id, Values[0][0]), 'integer' if Node.func.id == 'int' else 'float'
            if Node.func.id in ('min', 'max') and len(Values) >= 2:
                Kinds = {Kind for Value, Kind in Values}  # Only a uniform operand kind can be inferred before runtime dtype guards.
                return ('array_' + Node.func.id, *(Value for Value, Kind in Values)), next(iter(Kinds)) if len(Kinds) == 1 else 'float'
            raise _Fast_Unsupported()
    if Plan.get('Array_Region') and isinstance(Node, ast.BinOp) and isinstance(Node.op, ast.FloorDiv):
        Left, Left_Kind = _Fast_Expression(Node.left, Plan, Bindings, Inputs, Calls)
        Right, Right_Kind = _Fast_Expression(Node.right, Plan, Bindings, Inputs, Calls)
        if Left_Kind not in ('integer', 'boolean') or Right_Kind not in ('integer', 'boolean'):  # Floor division here has Python-integer semantics; arbitrary float division is a different contract.
            raise _Fast_Unsupported()
        return ('array_floor_divide', Left, Right), 'integer'
    if Plan.get("Numeric_Region") and isinstance(Node, ast.Subscript):
        Coordinates, Root = [], Node
        while isinstance(Root, ast.Subscript):
            Coordinates.insert(0, Root.slice)
            Root = Root.value
        if not isinstance(Root, ast.Name) or Root.id not in Plan["Buffers"]:
            raise _Fast_Unsupported()
        Slot, Dimensions, Kind = Plan["Buffers"][Root.id]
        if len(Coordinates) != Dimensions:
            raise _Fast_Unsupported()
        Values = [_Fast_Expression(Value, Plan, Bindings, Inputs, Calls) for Value in Coordinates]
        if any(Type != 'integer' and not (Plan.get('Array_Region') and Type == 'float') for Value, Type in Values):
            raise _Fast_Unsupported()
        return ("buffer", Slot, tuple(('array_index', Value) if Type != 'integer' else Value for Value, Type in Values)), Kind
    if Plan.get("Numeric_Region") and isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id == "len" and len(Node.args) == 1 and not Node.keywords:
        Argument = Node.args[0]
        Coordinates = []
        while isinstance(Argument, ast.Subscript):
            Coordinates.insert(0, Argument.slice)
            Argument = Argument.value
        if isinstance(Argument, ast.Name) and Argument.id in Plan["Buffers"]:
            Slot, Dimensions, Kind = Plan["Buffers"][Argument.id]
            if len(Coordinates) < Dimensions:
                Values = [_Fast_Expression(Value, Plan, Bindings, Inputs, Calls) for Value in Coordinates]
                if all(Type == 'integer' or Plan.get('Array_Region') and Type == 'float' for Value, Type in Values):
                    return ("dimension_path", Slot, tuple(('array_index', Value) if Type != 'integer' else Value for Value, Type in Values)), "integer"
        raise _Fast_Unsupported()
    if Plan.get("Numeric_Region") and isinstance(Node, ast.BinOp) and isinstance(Node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
        Left, Left_Kind = _Fast_Expression(Node.left, Plan, Bindings, Inputs, Calls)
        Right, Right_Kind = _Fast_Expression(Node.right, Plan, Bindings, Inputs, Calls)
        if isinstance(Node.op, ast.Pow):
            try:
                Exponent = ast.literal_eval(Node.right)
            except (ValueError, TypeError):
                raise _Fast_Unsupported()
            if Left_Kind != "float" or type(Exponent) is not int or not -256 <= Exponent <= 256:
                raise _Fast_Unsupported()
            return ("python_power", Left, Exponent), "float"
        Operator = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}[type(Node.op)]
        Kind = "integer" if Left_Kind in ("integer", "boolean") and Right_Kind in ("integer", "boolean") and Operator != "/" else "float"
        return ("checked_integer" if Kind == "integer" else "arithmetic", Operator, Left, Right), Kind
    if isinstance(Node, ast.Name) and Node.id in Plan.get("Local_Types", {}):
        return ("local", Plan["Local_Slots"].index(Node.id)), Plan["Local_Types"][Node.id]
    if isinstance(Node, ast.IfExp):
        Test = _Fast_Test(Node.test, Plan, Bindings, Inputs, Calls)
        Yes, Yes_Kind = _Fast_Expression(Node.body, Plan, Bindings, Inputs, Calls)
        No, No_Kind = _Fast_Expression(Node.orelse, Plan, Bindings, Inputs, Calls)
        if Yes_Kind != No_Kind:
            raise _Fast_Unsupported()
        return ("conditional", Test, Yes, No), Yes_Kind
    if isinstance(Node, ast.Subscript) and isinstance(Node.value, ast.Name):
        Positions = Node.slice.elts if isinstance(Node.slice, ast.Tuple) else (Node.slice,)
        Coordinates = tuple(Position.id if isinstance(Position, ast.Name) else None for Position in Positions)
        if Node.value.id in Plan["Names"] and Node.value.id != Plan["Output"] and Coordinates == tuple(Plan["Indices"]):
            if Node.value.id not in Inputs:
                Inputs.append(Node.value.id)
            return ("input", Inputs.index(Node.value.id)), "numpy"
    if isinstance(Node, ast.Constant) and type(Node.value) in (int, float):
        if type(Node.value) is float and math.isfinite(Node.value) or type(Node.value) is int and abs(Node.value) <= 2**53:
            return ("literal", Node.value if Plan.get('Array_Region') else float(Node.value)), "float" if type(Node.value) is float else "integer"
    if Plan.get("Numeric_Region") and isinstance(Node, ast.Constant) and type(Node.value) is bool:
        return ("literal", Node.value if Plan.get('Array_Region') else float(Node.value)), "boolean"
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

def _Fast_Test(Node, Plan, Bindings, Inputs, Calls):
    if isinstance(Node, ast.Compare) and len(Node.ops) == 1:
        Operators = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
        Operator = Operators.get(type(Node.ops[0]))
        if Operator is None:
            raise _Fast_Unsupported()
        Left = _Fast_Expression(Node.left, Plan, Bindings, Inputs, Calls)[0]
        Right = _Fast_Expression(Node.comparators[0], Plan, Bindings, Inputs, Calls)[0]
        return "compare", Operator, Left, Right
    if isinstance(Node, ast.BoolOp):
        Values = [_Fast_Test(Value, Plan, Bindings, Inputs, Calls) for Value in Node.values]
        Result = Values[-1]
        for Value in reversed(Values[:-1]):
            Result = ("conditional", Value, Result, ("literal", 0.0)) if isinstance(Node.op, ast.And) else ("conditional", Value, ("literal", 1.0), Result)
        return Result
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, ast.Not):
        return "compare", "==", _Fast_Test(Node.operand, Plan, Bindings, Inputs, Calls), ("literal", 0.0)
    Value = _Fast_Expression(Node, Plan, Bindings, Inputs, Calls)[0]
    return "compare", "!=", Value, ("literal", 0.0)

def _Fast_Statements(Statements, Plan, Bindings, Inputs, Calls):
    Program = []
    for Statement in Statements:
        if isinstance(Statement, ast.If):
            Test = _Fast_Test(Statement.test, Plan, Bindings, Inputs, Calls)
            Yes = dict(Plan, Local_Types=dict(Plan["Local_Types"]))
            No = dict(Plan, Local_Types=dict(Plan["Local_Types"]))
            Yes_Program = _Fast_Statements(Statement.body, Yes, Bindings, Inputs, Calls)
            No_Program = _Fast_Statements(Statement.orelse, No, Bindings, Inputs, Calls)
            Plan["Local_Types"] = {Name: Kind for Name, Kind in Yes["Local_Types"].items() if No["Local_Types"].get(Name) == Kind}
            Program.append(("if", Test, Yes_Program, No_Program))
            continue
        if isinstance(Statement, ast.Pass):
            continue
        if isinstance(Statement, ast.Assign) and len(Statement.targets) == 1:
            Target, Expression = Statement.targets[0], Statement.value
        elif isinstance(Statement, ast.AugAssign) and isinstance(Statement.target, ast.Name):
            Target = Statement.target
            Expression = ast.BinOp(left=ast.Name(id=Target.id, ctx=ast.Load()), op=Statement.op, right=Statement.value)
        else:
            raise _Fast_Unsupported()
        if isinstance(Target, ast.Name):
            Name = Target.id
        elif isinstance(Target, ast.Subscript) and isinstance(Target.value, ast.Name) and Target.value.id == Plan["Output"]:
            Positions = Target.slice.elts if isinstance(Target.slice, ast.Tuple) else (Target.slice,)
            if tuple(Position.id if isinstance(Position, ast.Name) else None for Position in Positions) != tuple(Plan["Indices"]):
                raise _Fast_Unsupported()
            Name = Plan["Result_Name"]
        else:
            raise _Fast_Unsupported()
        Value, Kind = _Fast_Expression(Expression, Plan, Bindings, Inputs, Calls)
        if Name not in Plan["Local_Slots"]:
            Plan["Local_Slots"].append(Name)
        Plan["Local_Types"][Name] = Kind
        Program.append(("store", Plan["Local_Slots"].index(Name), Value))
    return tuple(Program)

def _Fast_Math_Plan(Plan):
    Dimensions = len(Plan["Indices"])
    if Dimensions < 1 or len(Plan["Loops"]) != Dimensions or Plan["Scalars"]:
        return None
    if Dimensions > 1 and tuple(Axis for Name, Axis in Plan.get("Bounds", ())) != tuple(range(Dimensions)):
        return None
    Loop = Plan["Loops"][-1]
    Inputs, Calls, Program = [], set(), []
    Result_Name = "_Pyceler_Output"
    while Result_Name in (*Plan["Names"], *Plan["Locals"], *Plan["Indices"]):
        Result_Name += "_X"
    Context = dict(Plan, Local_Types={}, Local_Slots=[], Result_Name=Result_Name)
    Bindings = _Fast_Imports(Plan)
    try:
        Program = _Fast_Statements(Loop.body, Context, Bindings, Inputs, Calls)
        if Result_Name not in Context["Local_Types"]:
            return None
        Expression = ("local", Context["Local_Slots"].index(Result_Name))
    except _Fast_Unsupported:
        return None
    if not Calls or not Inputs or set(Inputs) | {Plan["Output"]} != set(Plan["Names"]):
        return None
    return dict(Version=_Fast_Math_Version, Names=tuple(Plan["Names"]), Inputs=tuple(Inputs), Output=Plan["Output"], Expression=Expression,
                Program=tuple(Program), Local_Count=len(Context["Local_Slots"]), Dimensions=Dimensions,
                Bindings=tuple(sorted(Calls)), Functions=tuple(sorted({Name for Root, Name, Module in Calls})), Chunk=4096,
                Call_Contracts=tuple((Name, _Fast_Call_Contracts[Name]["Arity"], _Fast_Call_Contracts[Name]["Return"], _Fast_Call_Contracts[Name]["Strategy"]) for Name in sorted({Name for Root, Name, Module in Calls})),
                Backend_Requirements=tuple(sorted({_Fast_Call_Contracts[Name]["Backend"] for Root, Name, Module in Calls if _Fast_Call_Contracts[Name]["Backend"] is not None})),
                Contract="Thin libm float64 calls with validated finite domains, exact original bindings, disjoint buffers, ordered continuation and bounded observer checks")
# Do not reorder floating operations or omit guards merely because a C expression can be emitted.
def _Fast_Emit(Node, Lines, Variables, Functions, Prefix):
    Kind = Node[0]
    if Kind == 'native_value':
        return Node[1]
    if Kind == 'helper':
        return _Helper_Emit(Node, Lines, Variables, Functions, Prefix, _Fast_Emit, _Array_Emitted_Tag)
    if Kind.startswith('array_'):
        return _Array_Emit(Node, Lines, Variables, Functions, Prefix, _Fast_Emit)
    if Kind == "input":
        return "X" + str(Node[1])
    if Kind == "local":
        return "L" + str(Node[1])
    if Kind == "literal":
        return repr(float(Node[1]))
    if Kind == "dimension":
        return f"Shapes[{Node[1]}][{Node[2]}]"
    Target = "T" + str(len(Variables))
    Variables.append(Target)
    if Kind == 'dimension_path':
        for Axis, Coordinate in enumerate(Node[2]):
            Value = _Fast_Emit(Coordinate, Lines, Variables, Functions, Prefix)
            _Buffer_Coordinate(Node[1], Axis, Value, Lines)
        Lines.append(f'    {Target} = Shapes[{Node[1]}][{len(Node[2])}]')
    elif Kind == "conditional":
        Test = _Fast_Emit(Node[1], Lines, Variables, Functions, Prefix)
        Lines.append(f"    if {Test}:")
        for Keyword, Branch in ((None, Node[2]), ("else:", Node[3])):
            if Keyword:
                Lines.append("    " + Keyword)
            Branch_Lines = []
            Value = _Fast_Emit(Branch, Branch_Lines, Variables, Functions, Prefix)
            Lines.extend("    " + Line for Line in Branch_Lines)
            Lines.append(f"        {Target} = {Value}")
    elif Kind == "compare":
        Left = _Fast_Emit(Node[2], Lines, Variables, Functions, Prefix)
        Right = _Fast_Emit(Node[3], Lines, Variables, Functions, Prefix)
        Lines.append(f"    {Target} = 1.0 if {Left} {Node[1]} {Right} else 0.0")
    elif Kind == 'absolute':
        Operand = _Fast_Emit(Node[1], Lines, Variables, Functions, Prefix)
        Lines.append(f'    {Target} = {Prefix}fabs({Operand})')
    elif Kind in ("negative", "integer_negative"):
        Operand = _Fast_Emit(Node[1], Lines, Variables, Functions, Prefix)
        Value = f"0.0 if {Operand} == 0.0 else -{Operand}" if Kind == "integer_negative" else f"-{Operand}"
        Lines.append(f"    {Target} = {Value}")
    elif Kind == "buffer":
        Coordinates = [_Fast_Emit(Value, Lines, Variables, Functions, Prefix) for Value in Node[2]]
        Offset = _Buffer_Offset(Node[1], Coordinates, Lines)
        Lines.append(f"    {Target} = Buffers[{Node[1]}][{Offset}]")
    elif Kind == "python_power":
        Value = _Fast_Emit(Node[1], Lines, Variables, Functions, Prefix)
        Lines.append(f"    {Target} = {Prefix}Python_Power({Value}, {Node[2]}, Valid)")
        Lines.extend(["    if not Valid[0]:", "        return 0.0"])
    elif Kind in ("arithmetic", "checked_integer"):
        Left = _Fast_Emit(Node[2], Lines, Variables, Functions, Prefix)
        Right = _Fast_Emit(Node[3], Lines, Variables, Functions, Prefix)
        if Node[1] == "/":
            Lines.extend([f"    if {Right} == 0.0:", "        Valid[0] = False", "        return 0.0"])
        Lines.append(f"    {Target} = {Left} {Node[1]} {Right}")
        Lines.extend([f"    if not {Prefix}Finite({Target}):", "        Valid[0] = False", "        return 0.0"])
        if Kind == "checked_integer":
            Lines.extend([f"    if {Target} < -1125899906842624.0 or {Target} > 1125899906842624.0:", "        Valid[0] = False", "        return 0.0"])
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
                Lines.extend([f"    if not {Prefix}Finite({Argument}) or ({Argument} == 0.0 and {Prefix}signbit({Argument})):", "        Valid[0] = False", "        return 0.0"])
            if Contract["Strategy"] == "Binary_Nonzero_Remainder":
                Lines.extend([f"    if {Operands[1]} == 0.0:", "        Valid[0] = False", "        return 0.0"])
        if Contract["Strategy"] == "Classifier":
            Lines.append(f"    {Target} = 1.0 if {Prefix}{Name}({Operand}) else 0.0")
        else:
            Lines.append("    Error[0] = 0")
            Value = f"({Operand} if {Operand} == 0.0 else {Prefix}log1p({Operand}))" if Name == "log1p" else f"{Prefix}{Name}({', '.join(Operands)})"
            Lines.append(f"    {Target} = {Value}")
            Lines.extend([f"    if not {Prefix}Finite({Target}) or (Error[0] != 0 and not (Error[0] == {Prefix}ERANGE and {Prefix}fabs({Target}) < 1.5)):",
                          "        Valid[0] = False", "        return 0.0"])
            if Contract["Strategy"] == "Binary_Nonzero_Remainder":
                Lines.extend([f"    if {Target} == 0.0:", "        Valid[0] = False", "        return 0.0"])
    return Target

def _Fast_Emit_Program(Program, Lines, Variables, Functions, Prefix, Indent="    "):
    for Instruction in Program:
        Work = []
        Value = _Fast_Emit(Instruction[2] if Instruction[0] == "store" else Instruction[1], Work, Variables, Functions, Prefix)
        Lines.extend(Indent + Line[4:] for Line in Work)
        if Instruction[0] == "store":
            Lines.append(f"{Indent}L{Instruction[1]} = {Value}")
        else:
            Lines.append(f"{Indent}if {Value}:")
            _Fast_Emit_Program(Instruction[2], Lines, Variables, Functions, Prefix, Indent + "    ")
            Lines.append(Indent + "else:")
            _Fast_Emit_Program(Instruction[3], Lines, Variables, Functions, Prefix, Indent + "    ")
    if not Program:
        Lines.append(Indent + "pass")

def _Fast_Math_Kernel(Plan, Line, Parallel=False, Preamble=False):
    Prefix = f"_Pyceler_Fast_{Line}_"
    Dimensions = Plan.get("Dimensions", 1)
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
             'cdef extern from *:', '    """', '    #include <errno.h>', '    #include <stdint.h>', '    #include <string.h>',
             f'    static inline int* {Prefix}Error_Address(void) {{ return &errno; }}',
             f'    static inline int {Prefix}Finite(double Value) {{', '        uint64_t Bits;', '        memcpy(&Bits, &Value, sizeof(Bits));',
             '        return (Bits & UINT64_C(0x7ff0000000000000)) != UINT64_C(0x7ff0000000000000);', '    }',
             f'    static int {Prefix}Prepare_Exceptions(int Flags, fexcept_t* Prepared) {{',
             '        fenv_t Saved;', '        int Result;', '        if (feholdexcept(&Saved) != 0) return -1;', '        Result = feraiseexcept(Flags);',
             '        if (Result == 0) Result = fegetexceptflag(Prepared, Flags);', '        if (fesetenv(&Saved) != 0) return -1;', '        return Result;', '    }',
             '    """', f'    int* {Prefix}Error_Address() noexcept nogil', f'    bint {Prefix}Finite(double) noexcept nogil',
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
                  f"    if {Prefix}Rounding() != {Prefix}Nearest or T.current_thread() is not T.main_thread() or len(S._current_frames()) != 1 or S.gettrace() is not None or S.getprofile() is not None or not {Prefix}Monitoring_Code():",
                  "        return False", "    for Number in G.valid_signals():", "        Handler = G.getsignal(Number)",
                  "        if Handler is not None and Handler is not G.SIG_DFL and Handler is not G.SIG_IGN and Handler is not G.default_int_handler:", "            return False", "    return True",
                  f"cdef bint {Prefix}Bindings(dict Namespace{', dict Source_Globals' if Plan.get('Global_Roots') else ''}):", "    cdef object Function, Module"])
    for Position, Name in enumerate(Plan["Functions"]):
        Lines.extend([f"    Function = {Prefix}Functions[{Position}]", f"    if {Prefix}Builtins.type(Function) is not {Prefix}Types.BuiltinFunctionType or Function.__self__ is not {Prefix}Math or Function.__name__ != {Name!r}:", "        return False",
                      f"    if {Prefix}Builtins.getattr({Prefix}Math, {Name!r}, None) is not Function:", "        return False"])
    for Root, Name, Module in Plan["Bindings"]:
        Position = Plan["Functions"].index(Name)
        Value = f"Source_Globals.get({Plan['Global_Roots'][Root]!r})" if Root in Plan.get('Global_Roots', {}) else f"Namespace.get({Root!r})"
        Test = f"{Value} is not {Prefix}Math" if Module else f"{Value} is not {Prefix}Functions[{Position}]"
        Lines.extend(["    if " + Test + ":", "        return False"])
    Lines.append("    return True")
    Lines.append(_Monitoring_Kernel(Prefix))
    if Preamble:
        return "\n".join(Lines) + "\n"
    Evaluation, Variables = [], ["L" + str(Index) for Index in range(Plan.get("Local_Count", 0))]
    _Fast_Emit_Program(Plan.get("Program", ()), Evaluation, Variables, Functions, Prefix)
    Result = _Fast_Emit(Plan["Expression"], Evaluation, Variables, Functions, Prefix)
    Parameters = ", ".join([*("double X" + str(Index) for Index in range(len(Plan["Inputs"]))), "bint* Valid", "int* Error"])
    Lines.extend([f"@{Prefix}Division(True)", f"cdef inline double {Prefix}Value({Parameters}) noexcept nogil:"])
    for Start, Type in (("L", "double"), ("T", "volatile double")):
        Group = [Name for Name in Variables if Name.startswith(Start)]
        if Group:
            Lines.append("    cdef " + Type + " " + ", ".join(Group))
    for Index in range(len(Plan["Inputs"])):
        Lines.extend([f"    if not {Prefix}Finite(X{Index}) or (X{Index} == 0.0 and {Prefix}signbit(X{Index})):", "        Valid[0] = False", "        return 0.0"])
    Lines.extend(Evaluation)
    Lines.append("    return " + Result)
    Source_Slots = [Plan["Names"].index(Name) for Name in Plan["Inputs"]]
    Output_Slot = Plan["Names"].index(Plan["Output"])
    Input_Parameters = [f"const double[::1] I{Index}" for Index in range(len(Source_Slots))]
    Value_Call = f"{Prefix}Value(" + ", ".join([*(f"I{Index}[Position]" for Index in range(len(Source_Slots))), "&Valid", "Error"]) + ")"
    Lines.extend([f"@{Prefix}Bounds(False)", f"@{Prefix}Wrap(False)", f"cdef bint {Prefix}Evaluate({', '.join([*Input_Parameters, 'double* Scratch', 'Py_ssize_t Begin', 'Py_ssize_t End', 'Py_ssize_t Offset', 'const ' + Prefix + 'Environment* Environment', 'int* Exceptions'])}) noexcept nogil:",
                  "    cdef bint Valid = True", "    cdef Py_ssize_t Position", f"    cdef int* Error = {Prefix}Error_Address()", f"    cdef {Prefix}Environment Previous", f"    {Prefix}Get_Environment(&Previous)", f"    {Prefix}Set_Environment(Environment)",
                  "    for Position in range(Begin, End):", "        Scratch[Position - Offset] = " + Value_Call, "        if not Valid:", "            break",
                  f"    Exceptions[0] = {Prefix}Test_Exceptions({Prefix}All_Exceptions)", f"    {Prefix}Set_Environment(&Previous)", "    return Valid"])
    Lines.extend([f"@{Prefix}Bounds(False)", f"@{Prefix}Wrap(False)", f"cdef void {Prefix}Commit(double* Scratch, double[::1] Output, Py_ssize_t Begin, Py_ssize_t End) noexcept nogil:",
                  "    cdef Py_ssize_t Position", "    for Position in range(Begin, End):", "        Output[Position] = Scratch[Position - Begin]"])
    Lines.extend([f"cdef Py_ssize_t _Pyceler_Fast_Math_{Line}(tuple Args, object Baseline, object Iterator, bint Allow_Threads, int Thread_Count) except -1:",
                  "    import numpy as N", "    import builtins as B", "    cdef dict Namespace = Baseline.__globals__", "    cdef Py_ssize_t Size, Done = 0, End, Part, Parts, Width, Batch",
                  f"    cdef bint Checks[{Plan['Chunk']}]", "    cdef bint Valid, Used_Parallel", f"    cdef int Exceptions[{Plan['Chunk']}]", "    cdef int Flags", "    cdef double* Scratch = NULL",
                  "    cdef object Array", f"    cdef {Prefix}Address Output_Begin, Output_End, Input_Begin, Input_End", f"    cdef {Prefix}Environment Environment", f"    cdef {Prefix}Exception_State Prepared",
                  "    cdef double[::1] Output", f"    global {Prefix}Native_Elements, {Prefix}Parallel_Elements, {Prefix}Last_Team"])
    for Index in range(len(Source_Slots)):
        Lines.append(f"    cdef const double[::1] I{Index}")
    if Parallel:
        Lines.extend(["    cdef int Team[1]", "    cdef int Workers"])
    if "Runtime_CPython_Libm_Erf" in Plan.get("Backend_Requirements", ()):
        Lines.extend([f"    if not {Prefix}Erf_Backend_Eligible:", "        return 0"])
    if Dimensions > 1:
        Lines.extend(["    if Namespace.get('range', Baseline.__builtins__.get('range')) is not B.range:", "        return 0"])
    Lines.extend([f"    if len(Args) != {len(Plan['Names'])} or B.type(Iterator) is not B.range or Iterator.start != 0 or Iterator.step != 1:", "        return 0",
                  "    for Array in Args:", f"        if B.type(Array) is not N.ndarray or Array.ndim != {Dimensions} or Array.dtype != N.dtype('float64') or Array.dtype.metadata is not None or not Array.flags.c_contiguous or not Array.flags.aligned:", "            return 0",
                  f"    if not Args[{Output_Slot}].flags.writeable:", "        return 0", f"    Size = Args[{Output_Slot}].size",
                  f"    if Iterator.stop != Args[{Output_Slot}].shape[0] or any(Array.shape != Args[{Output_Slot}].shape for Array in Args):", "        return 0", "    if Size == 0:", "        return 0",
                  f"    Width = Size // Args[{Output_Slot}].shape[0]", f"    Batch = max(Width, ({Plan['Chunk']} // Width) * Width)",
                  f"    Output = Args[{Output_Slot}].reshape(-1)", f"    Output_Begin = <{Prefix}Address>&Output[0]", "    Output_End = Output_Begin + Size * sizeof(double)"])
    for Index, Slot in enumerate(Source_Slots):
        Lines.extend([f"    I{Index} = Args[{Slot}].reshape(-1)", f"    Input_Begin = <{Prefix}Address>&I{Index}[0]", "    Input_End = Input_Begin + Size * sizeof(double)",
                      "    if Input_Begin < Output_End and Output_Begin < Input_End:", "        return 0"])
    View_Args = ", ".join(f"I{Index}" for Index in range(len(Source_Slots)))
    Lines.extend([f"    Scratch = <double*>{Prefix}Allocate(Batch * sizeof(double))", "    if Scratch == NULL:", "        return 0", "    try:", "        while Done < Size:",
                  f"            if not {Prefix}Exclusive() or not {Prefix}Bindings(Namespace):", "                return Done // Width",
                  "            End = Done + min(Size - Done, Batch)", f"            if {Prefix}Get_Environment(&Environment) != 0:", "                return Done // Width",
                  "            Used_Parallel = False", "            Parts = 1"])
    Evaluate_Call = f"{Prefix}Evaluate({View_Args}, Scratch, Done, End, Done, &Environment, &Exceptions[0])"
    if Parallel:
        Lines.extend([f"            if Allow_Threads and not {Prefix}In_Parallel():", "                Used_Parallel = True", "                Team[0] = 1",
                      f"                Workers = Thread_Count if Thread_Count > 0 else {Prefix}Max_Threads()", f"                Parts = min(End - Done, Workers, {Plan['Chunk']})",
                      f"                for Part in {Prefix}Prange(Parts, nogil=True, schedule='static', num_threads=Workers):",
                      "                    if Part == 0:", f"                        Team[0] = {Prefix}Team_Size()",
                      f"                    Checks[Part] = {Prefix}Evaluate({View_Args}, Scratch, Done + (End - Done) * Part // Parts, Done + (End - Done) * (Part + 1) // Parts, Done, &Environment, &Exceptions[Part])",
                      "            else:", "                with nogil:", "                    Checks[0] = " + Evaluate_Call])
    else:
        Lines.extend(["            with nogil:", "                Checks[0] = " + Evaluate_Call])
    Lines.extend(["            Valid = True", "            Flags = 0", "            for Part in range(Parts):", "                Valid = Valid and Checks[Part]", "                Flags |= Exceptions[Part]",
                  f"            if not Valid or not {Prefix}Exclusive() or not {Prefix}Bindings(Namespace) or not Args[{Output_Slot}].flags.writeable:", "                return Done // Width",
                  f"            if Flags and {Prefix}Prepare_Exceptions(Flags, &Prepared) != 0:", "                return Done // Width", f"            {Prefix}Commit(Scratch, Output, Done, End)",
                  "            if Flags:", f"                {Prefix}Set_Exceptions(&Prepared, Flags)"])
    if Parallel:
        Lines.extend(["            if Used_Parallel:", f"                {Prefix}Parallel_Elements += End - Done", f"                {Prefix}Last_Team = Team[0]",
                      "                _Pyceler_Dispatch_Event('Execution', 'native_parallel', Team[0])", "            else:", f"                {Prefix}Last_Team = 1", "                _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)"])
    else:
        Lines.extend([f"            {Prefix}Last_Team = 1", "            _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)"])
    Lines.extend([f"            {Prefix}Native_Elements += End - Done", "            Done = End", f"            {Prefix}Signals()", "            with nogil:", "                pass", "        return Done // Width", "    finally:", f"        {Prefix}Free(Scratch)"])
    return "\n".join(Lines) + "\n"
