import ast
import copy
from .Fast_Math import _Fast_Math_Kernel
from .Math_Maps import _Module_Constant_Kernel, _Module_Constant_Anchor
from .Numeric_Region_Emitter import _Numeric_Compute
from .Numeric_Fills import _Fill_Kernel
from .Numeric_Contracts import _Builtin_Guards
from .Region_Parallel import _Numeric_Worker, _Numeric_Parallel
from .Region_Diagnostics import _Region_Guards
from .Common_Scopes import _Scope_Error_Declaration
from .Helper_Kernel import _Helper_Kernel, _Helper_Guards, _Region_Roots, _Global_Bindings
from .Iterator_Kernel import _Iterator_Kernel, _Iterator_Source
# Assemble list-region guards, native workers and publication/continuation source.
def _Numeric_Region_Kernel(Plan, Line, Filename, Measured, Template, Parallel=False):
    Parallel = Parallel and Plan.get("Parallel", False)
    Original_Template = Template
    if Plan['Math'].get('Global_Roots'):
        Template = Template.replace('FAST_PREFIXBindings(Namespace)', 'FAST_PREFIXBindings(Namespace, Source_Globals)')
    Prefix = f"_Pyceler_Fast_{Line}_"
    Numeric = f"_Pyceler_Numeric_{Line}_"
    Buffer_Names = tuple(Plan["Buffers"])
    Guards = []
    Guards.extend(_Builtin_Guards(Plan.get('Builtins', ()), Prefix))
    Guards.extend(_Helper_Guards(Plan, Line))
    for Name in (*Plan["Names"], *_Region_Roots(Plan)):
        Guards.extend([f"if {Name!r} not in Namespace:", "    return None"])
    for Name in Plan["Written"]:
        Guards.extend([f"Previous = Namespace.get({Name!r})", f"if not ({Numeric}Float(Previous) or {Numeric}Integer(Previous) or {Numeric}Boolean(Previous) or Previous is None):", "    return None"])
    Guards.extend(f"Inputs[{Index}] = 0.0\nOrigins[{Index}] = 0" for Index in range(len(Plan["Slots"])))
    for Name in Plan["Inputs"]:
        Slot = Plan["Slots"].index(Name)
        if Plan["Input_Types"][Name] == "integer":
            Guards.extend([f"if not {Numeric}Integer(Namespace[{Name!r}]) or not -1125899906842624 <= Namespace[{Name!r}] <= 1125899906842624:", "    return None"])
        elif Name in Plan.get('Real_Inputs', ()):
            Guards.extend([f"if not ({Numeric}Float(Namespace[{Name!r}]) or {Numeric}Integer(Namespace[{Name!r}]) and -1125899906842624 <= Namespace[{Name!r}] <= 1125899906842624):", "    return None"])
        else:
            Guards.extend([f"if not {Numeric}Float(Namespace[{Name!r}]):", "    return None"])
        Guards.extend([f"Inputs[{Slot}] = Namespace[{Name!r}]", f"if not {Prefix}Finite(Inputs[{Slot}]):", "    return None"])
    if Plan["Math"]["Backend_Requirements"]:
        Guards.extend([f"if not {Prefix}Erf_Backend_Eligible:", "    return None"])
    Replacements = dict(REQUIRED_GUARDS="\n".join(Guards), BUFFER_COUNT=str(len(Buffer_Names)), RANK_COUNT=str(max(Value[1] for Value in Plan["Buffers"].values())), SLOT_COUNT=str(len(Plan["Slots"])), BUFFER_NAMES=repr(Buffer_Names), BUFFER_DIMENSIONS=repr(tuple(Plan["Buffers"][Name][1] for Name in Buffer_Names)), BUFFER_READS=repr(tuple(Name in Plan["Read_Buffers"] for Name in Buffer_Names)), BUFFER_INTEGER_OUTPUTS=repr(tuple(Plan["Writes"].get(Name) == "integer" for Name in Buffer_Names)), REQUIRED_SLOTS=repr(tuple(Plan["Slots"].index(Name) for Name in Plan["Written"])), NUMERIC_COMPUTE=f"_Pyceler_Numeric_Compute_{Line}", CONSTANT_PREFIX=f"_Pyceler_Module_Constants_{Line}_", OUTER_INDEX=repr(Plan["Index"]), WRITTEN_NAMES=repr(Plan["Written"]), OBSERVED_NAMES=repr(tuple(dict.fromkeys((*Plan["Names"], *Plan["Written"])))), NUMERIC_PREFIX=Numeric, FAST_PREFIX=Prefix)
    Replacements["GLOBAL_BINDINGS"] = repr(_Global_Bindings(Plan))
    Replacements['DYNAMIC_IDENTITY'] = repr(Plan.get('Dynamic_Identity', False))
    Outputs = Plan.get('Live_Outputs', Plan['Written'])
    Replacements['WRITTEN_NAMES'] = repr(Outputs)
    Replacements["REQUIRED_SLOTS"] = repr(tuple(Plan["Slots"].index(Name) for Name in Outputs if Name not in Plan["Carry"]))
    Replacements["BUFFER_BOOLEAN_OUTPUTS"] = repr(tuple(Plan["Writes"].get(Name) == "boolean" for Name in Buffer_Names))
    Replacements["BUFFER_WRITES"] = repr(tuple(Name in Plan["Writes"] for Name in Buffer_Names))
    Replacements['BUFFER_SHAPE_ONLY'] = repr(tuple(Name in Plan.get('Shape_Only', ()) for Name in Buffer_Names))
    Replacements["INTEGER_READS"] = repr(Plan["Read_Kind"] == "integer")
    Replacements["BLOCK_SIZE"] = "128" if any(isinstance(Loop, ast.While) for Loop in Plan["Loops"]) else "B.len(Span) or 1"
    Replacements['RECOVERABLE_FAILURES'] = repr('Iterator' not in Plan and not any(isinstance(Loop, ast.While) for Loop in Plan['Loops']))
    Carry = []
    for Name in Plan["Carry"]:
        Slot = Plan["Slots"].index(Name)
        Value = ("<long long>" if Plan["Input_Types"][Name] == "integer" else "") + f"Inputs[{Slot}]"
        Carry.append(f"if Prefix_Assigned[{Slot}]:")
        if Plan.get('Dynamic_Identity'):
            Carry.extend([f'    if Origins[{Slot}] == 0:', '        return None', f'    Value = {Value}', f'    if Origins[{Slot}] > 0:', f'        Value = Boxed_Values.setdefault(Origins[{Slot}], Value)', f'    Carry_Updates[{Name!r}] = Value'])
        else:
            Carry.append(f"    Carry_Updates[{Name!r}] = {Value}")
    Replacements["CARRY_UPDATES"] = "\n".join(Carry) or "pass"
    Replacements["POLICY_GUARD"] = "Mode = _Pyceler_Choose((B.len(Whole),), True, Policy) if Policy is not None else 2\nif Mode == 0:\n    return None" if Measured else "Mode = 2"
    if Measured and 'Selection_Key' in Plan:
        Replacements['POLICY_GUARD'] = f"Mode = _Pyceler_Choose((B.len(Whole),), True, {{'int': Policy.get({Plan['Selection_Key']!r}, ())}}) if Policy is not None else 2\nif Mode == 0:\n    return None"
    Replacements["PARALLEL_COMPUTE"] = _Numeric_Parallel(Plan, Line) if Parallel else "pass"
    Replacements["RECHECK_BUILTINS"] = "\n".join([*_Builtin_Guards(Plan.get("Builtins", ()), Prefix), *_Helper_Guards(Plan, Line)]) or "pass"
    for Name, Value in Replacements.items():
        Template = Template.replace(Name, Value.replace("\n", "\n    ") if Name in ("REQUIRED_GUARDS", "POLICY_GUARD") else Value.replace("\n", "\n        ") if Name in ("CARRY_UPDATES", "RECHECK_BUILTINS") else Value.replace("\n", "\n            ") if Name == "PARALLEL_COMPUTE" else Value)
    Final = copy.deepcopy(Plan["Loops"][0])
    Template = _Region_Guards(Template, Line)
    Final.iter = ast.parse(f"range({Plan['Index']}, {Plan['Index']} + 1)", mode="eval").body
    Body = ast.unparse(ast.fix_missing_locations(ast.Module(body=Final.body if 'Iterator' in Plan else [Final], type_ignores=[])))
    Lines = [f"from cpython.pyport cimport PY_SSIZE_T_MAX as {Numeric}Size_Max", _Module_Constant_Kernel(Line), _Fast_Math_Kernel(Plan["Math"], Line, Parallel=Parallel, Preamble=True), f"from cpython.float cimport PyFloat_CheckExact as {Numeric}Float", f"from cpython.long cimport PyLong_CheckExact as {Numeric}Integer, PyLong_AsLongLongAndOverflow as {Numeric}Long_Value", f"from cpython.bool cimport PyBool_Check as {Numeric}Boolean", f"from cpython.list cimport PyList_CheckExact as {Numeric}List", f"from cpython.number cimport PyNumber_Power as {Numeric}Power", f"from libc.string cimport memcpy as {Numeric}Copy, memset as {Numeric}Clear", f"cdef object {Numeric}Body = compile({Body!r}, {Filename!r}, 'exec', dont_inherit=True)", f"cdef double {Prefix}Python_Power(double Base, int Exponent, bint* Valid) except? -1:", "    try:", f"        Value = {Numeric}Power(Base, Exponent, None)", f"        if not {Numeric}Float(Value) or not {Prefix}Finite(Value):", "            Valid[0] = False", "            return 0.0", "        return Value", "    except (ArithmeticError, ValueError):", "        Valid[0] = False", "        return 0.0", _Numeric_Compute(Plan, Line, Parallel), _Numeric_Worker(Plan, Line) if Parallel else "", Template]
    Fill = _Fill_Kernel(Plan, Line)
    if Fill:
        Marker = "    Objects = [Namespace[Name] for Name in "
        Position = Lines[-1].index(Marker)
        Lines[-1] = Lines[-1][:Position] + f"    Filled = {Numeric}Fill(Namespace, Span, Policy, Whole)\n    if Filled is not None:\n        return Filled\n" + Lines[-1][Position:]
        Lines.insert(-2, Fill)
    Result = _Scope_Error_Declaration(Numeric) + "\n" + _Helper_Kernel(Plan, Line) + "\n" + "\n".join(Lines) + "\n" + _Iterator_Kernel(Plan, Line)
    if 'Selection_Key' in Plan:
        Result += f'\ncdef bint {Numeric}Storage(tuple Objects):\n    for Value in Objects:\n        if not {Numeric}List(Value):\n            return False\n    return True\n'
    if "Alternate" in Plan:
        Alternate = str(Line) + "_Integer"
        Result = Result.replace(Numeric + "Try(", Numeric + "Float_Try(")
        Result += _Numeric_Region_Kernel(Plan["Alternate"], Alternate, Filename, Measured, Original_Template, Parallel)
        Parameters = "dict Namespace, object Span, object Whole, object Binding, object Length_Binding, object Policy, object Source_Code, dict Source_Globals, list Recovery"
        Arguments = "Namespace, Span, Whole, Binding, Length_Binding, Policy, Source_Code, Source_Globals, Recovery"
        Name = Plan["Read_Buffers"][0]
        Result += f"\ncdef object {Numeric}Try({Parameters}):\n    Value = Namespace.get({Name!r})\n    for Depth in range({Plan['Buffers'][Name][1]}):\n        if not {Numeric}List(Value) or not Value:\n            return None\n        Value = Value[0]\n    if {Numeric}Integer(Value) or {Numeric}Boolean(Value):\n        return _Pyceler_Numeric_{Alternate}_Try({Arguments})\n    return {Numeric}Float_Try({Arguments})\n"
    return Result

def _Numeric_Region_Source(Plan, Node, Line, Prefix, Table, Prepared_Span=None):
    if 'Iterator' in Plan:
        return _Iterator_Source(Plan, Node, Line, Prefix, Table)
    Rows, Block, Result = (f"{Prefix}Numeric_{Name}_{Line}" for Name in ("Rows", "Block", "Result"))
    Roots = _Region_Roots(Plan)
    Names = tuple(dict.fromkeys((*Plan["Names"], *Plan["Output_Guards"])))
    Globals = f"{Prefix}Module_Constants_{Line}.__globals__"
    Pairs = [repr(Name) + ": " + Name for Name in Names]
    Pairs.extend(repr(Root) + ": " + (Root if Root in Plan["Local_Bindings"] else f"{Globals}.get({Plan.get('Global_Names', {}).get(Root, Root)!r})") for Root in Roots)
    Used_Length = any(isinstance(Part, ast.Name) and Part.id == 'len' and isinstance(Part.ctx, ast.Load) for Part in ast.walk(Node))
    Captured_Length = Used_Length and 'len' in Plan.get('Captured_Inputs', ())
    if Captured_Length and 'len' not in Names:
        Pairs.append("'len': len")
    Length = 'len' if Used_Length else f'{Prefix}Python_Builtins.len'
    Namespace = f"{Prefix}Module_Namespace()" if Plan["Module"] else "{" + ", ".join(Pairs) + "}"
    Policy = f"{Prefix}Table_{Line}" if Table is not None else "None"
    Recovery = f'{Prefix}Numeric_Recovery_{Line}'
    Extra = ', ' + Recovery if Recovery else ''
    Lines = [_Module_Constant_Anchor(Node, Line, Prefix), f"{Rows} = {ast.unparse(Node.iter) if Prepared_Span is None else Prepared_Span}"]
    if Recovery:
        Lines.append(f'{Recovery} = [0, 0]')
    Lines.append(f"for {Block} in {Prefix}Numeric_{Line}_Blocks({Rows}{Extra}):")
    Indent = '    '
    if Plan.get('Captured_Inputs'):
        Local = f'{Prefix}Numeric_Namespace_{Line}'
        Lines.extend(['    try:', f'        {Local} = {Namespace}', f'    except {Prefix}Numeric_{Line}_Name_Error:', f'        {Result} = None', '    else:'])
        Namespace, Indent = Local, '        '
        if Captured_Length:
            Length = Local + "['len']"
    Lines.extend([f"{Indent}{Result} = {Prefix}Numeric_{Line}_Try({Namespace}, {Block}, {Rows}, range, {Length}, {Policy}, {Prefix}Module_Constants_{Line}.__code__, {Globals}{Extra})", f"    if {Result} is None:"])
    if Recovery:
        Lines.extend([f'        if 0 < {Recovery}[0] < {Prefix}Python_Builtins.len({Block}):', '            continue'])
    Fallback = copy.deepcopy(Node)
    Fallback.iter = ast.Name(id=Block, ctx=ast.Load())
    Lines.extend("        " + Text for Text in ast.unparse(Fallback).splitlines())
    if not Plan["Module"]:
        Outputs = Plan.get('Live_Outputs', Plan['Written'])
        Assignment = ', '.join(Outputs) + (',' if len(Outputs) == 1 else '') + ' = ' + Result if Outputs else 'pass'
        Lines.extend(['    else:', '        ' + Assignment])
    return "\n".join(Lines)
