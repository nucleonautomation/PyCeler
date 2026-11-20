import ast
import copy
from .Fast_Math import _Fast_Math_Kernel
from .Math_Maps import _Module_Constant_Kernel
from .Numeric_Region_Emitter import _Emit
from .Numeric_Contracts import _Builtin_Guards
from .Region_Parallel import _Parallel_Bounds
from .Region_Diagnostics import _Region_Guards
from .Common_Scopes import _Scope_Error_Declaration
from .Helper_Kernel import _Helper_Kernel, _Helper_Guards, _Region_Roots, _Global_Bindings
from .Iterator_Kernel import _Iterator_Kernel
from .Array_Scalars import _Array_Scalar_Kernel, _Array_Scalar_Types
from .Direct_Source import _Namespace_Block
# Assemble typed ndarray workers, runtime guards and explicit continuation code from an array plan.
def _Array_Compute(Plan, Line):
    Prefix, Numeric = f'_Pyceler_Fast_{Line}_', f'_Pyceler_Numeric_{Line}_'
    Variables = ['L' + str(Index) for Index in range(len(Plan['Slots']))]
    Work, Cursors = [], []
    _Emit(Plan['Program'], Work, Variables, Plan['Math']['Functions'], Prefix, Cursors, '        ', True)
    Parameters = 'double** Buffers, unsigned char** Changed, Py_ssize_t** Shapes, Py_ssize_t** Strides, unsigned char* Buffer_Kinds, int* Output_Kinds, double* Inputs, unsigned char* Scalar_Kinds, double* Random_Values, Py_ssize_t Random_Limit, Py_ssize_t Random_Position, Py_ssize_t* Random_Consumed, Py_ssize_t Begin, Py_ssize_t End, Py_ssize_t Step, unsigned char* Assigned, bint* Valid'
    Lines = [f'cdef double {Prefix}Array_Cast(double Value, int Kind, bint* Valid) noexcept nogil:', '    if Kind == 1:', '        Value = <float>Value', '    elif Kind == 3:', '        Value = 1.0 if Value != 0.0 else 0.0', '    elif Kind >= 10:', '        if Value < -1125899906842624.0 or Value > 1125899906842624.0:', '            Valid[0] = False', '            return 0.0', '        Value = <long long>Value', '        if (Kind == 11 and (Value < -128 or Value > 127)) or (Kind == 12 and (Value < -32768 or Value > 32767)) or (Kind == 14 and (Value < -2147483648.0 or Value > 2147483647.0)) or (Kind == 21 and (Value < 0 or Value > 255)) or (Kind == 22 and (Value < 0 or Value > 65535)) or (Kind == 24 and (Value < 0 or Value > 4294967295.0)) or (Kind == 28 and Value < 0):', '            Valid[0] = False', f'    if not {Prefix}Finite(Value):', '        Valid[0] = False', '    return Value', f'@{Prefix}Division(True)', f'cdef double {Numeric}Compute({Parameters}) noexcept nogil:', '    cdef Py_ssize_t Outer', '    cdef unsigned int Ticks', f'    cdef int* Error = {Prefix}Error_Address()']
    for Start, Type in (('L', 'double'), ('T', 'volatile double'), ('K', 'unsigned char')):
        Group = [Name for Name in Variables if Name.startswith(Start)]
        if Group:
            Lines.append('    cdef ' + Type + ' ' + ', '.join(Group))
    if Cursors:
        Lines.append('    cdef Py_ssize_t ' + ', '.join(Cursors))
    Lines.extend(f'    L{Index} = Inputs[{Index}]' for Index in range(len(Plan['Slots'])))
    Index = Plan['Slots'].index(Plan['Index'])
    Lines.extend([*[f'    Assigned[{Slot}] = 0' for Slot in range(len(Plan['Slots']))], '    Random_Consumed[0] = Random_Position', '    Outer = Begin', '    while (Step > 0 and Outer < End) or (Step < 0 and Outer > End):', '        Ticks = 0', f'        L{Index} = Outer', '        Outer += Step', f'        Assigned[{Index}] = 1', f'        Scalar_Kinds[{Index}] = 4', *Work])
    Lines.extend(f'    Inputs[{Index}] = L{Index}' for Index in range(len(Plan['Slots'])))
    Lines.append('    return 1.0')
    Storage = [f'cdef inline void {Prefix}Array_Store(double* Output, Py_ssize_t Position, double Value, int Kind, bint Raw) noexcept nogil:', '    if not Raw:', '        Output[Position] = Value', '        return']
    Types = {1: 'float', 2: 'double', 3: 'unsigned char', 11: 'signed char', 12: 'short', 14: 'int', 18: 'long long', 21: 'unsigned char', 22: 'unsigned short', 24: 'unsigned int', 28: 'unsigned long long'}
    for Kind, Type in Types.items():
        Storage.extend([f'    if Kind == {Kind}:', f'        (<{Type}*>Output)[Position] = <{Type}>Value', '        return'])
    Lines = [_Array_Scalar_Kernel(Prefix), f'from libc.math cimport pow as {Prefix}Array_Power_Double, powf as {Prefix}Array_Power_Float', *Storage, *Lines]
    Worker_Parameters = Parameters.replace('Py_ssize_t* Random_Consumed, ', '').replace('unsigned char* Assigned, bint* Valid', f'const {Prefix}Environment* Saved, int* Flags')
    Lines.extend([f'cdef bint {Numeric}Worker({Worker_Parameters}) noexcept nogil:', f'    cdef double Local_Inputs[{len(Plan["Slots"])}]', f'    cdef unsigned char Local_Kinds[{len(Plan["Slots"])}]', f'    cdef unsigned char Assigned[{len(Plan["Slots"])}]', '    cdef bint Valid = True', '    cdef Py_ssize_t Slot, Random_Consumed', f'    cdef {Prefix}Environment Previous', f'    {Prefix}Get_Environment(&Previous)', f'    {Prefix}Set_Environment(Saved)', f'    {Numeric}Clear_Exceptions({Prefix}All_Exceptions)', f'    for Slot in range({len(Plan["Slots"])}):', '        Local_Inputs[Slot] = Inputs[Slot]', '        Local_Kinds[Slot] = Scalar_Kinds[Slot]', f'    {Numeric}Compute(Buffers, Changed, Shapes, Strides, Buffer_Kinds, Output_Kinds, Local_Inputs, Local_Kinds, Random_Values, Random_Limit, Random_Position, &Random_Consumed, Begin, End, Step, Assigned, &Valid)', f'    Flags[0] = {Prefix}Test_Exceptions({Prefix}All_Exceptions)', f'    {Prefix}Set_Environment(&Previous)', '    return Valid'])
    return '\n'.join(Lines) + '\n'

def _Array_Region_Kernel(Plan, Line, Filename, Measured, Parallel, Template):
    Prefix, Numeric = f'_Pyceler_Fast_{Line}_', f'_Pyceler_Numeric_{Line}_'
    Names = tuple(Plan['Buffers'])
    if Plan['Math'].get('Global_Roots'):
        Template = Template.replace('FAST_PREFIXBindings(Namespace)', 'FAST_PREFIXBindings(Namespace, Source_Globals)')
    Guards = _Helper_Guards(Plan, Line)
    for Name in (*Plan['Names'], *_Region_Roots(Plan)):
        Guards.extend([f'if {Name!r} not in Namespace:', '    return None'])
    for Name in Plan['Written']:
        Guards.extend([f'Previous = Namespace.get({Name!r})', 'if B.type(Previous) not in (int, float, bool, N.float32, N.float64, N.int64, N.int32) and Previous is not None:', '    return None'])
    for Name in Plan['Builtins']:
        if Name == 'abs':
            Guards.extend(_Builtin_Guards((Name,), Prefix))
            continue
        Guards.extend([f'if Source_Globals.get({Name!r}, getattr(B, {Name!r})) is not getattr(B, {Name!r}):', '    return None'])
        if Name in ('min', 'max'):
            Guards.extend([f'if B.type(B.{Name}) is not FAST_PREFIXTypes.BuiltinFunctionType or B.{Name}.__self__ is not B or B.{Name}.__name__ != {Name!r}:', '    return None'])
        else:
            Guards.extend([f'if B.{Name} is not B.type({"1" if Name == "int" else "1.0"}):', '    return None'])
    Guards.extend(f'Inputs[{Index}] = 0.0\nScalar_Kinds[{Index}] = 0' for Index in range(len(Plan['Slots'])))
    for Name in Plan['Inputs']:
        Slot = Plan['Slots'].index(Name)
        if Plan['Input_Types'][Name] == 'integer':
            Guards.extend([f'if B.type(Namespace[{Name!r}]) is not int or not -1125899906842624 <= Namespace[{Name!r}] <= 1125899906842624:', '    return None'])
            Guards.append(f'Scalar_Kinds[{Slot}] = 4')
        else:
            Guards.extend([f'Scalar_Kinds[{Slot}] = {Prefix}Scalar_Kind(Namespace[{Name!r}], N)', f'if Scalar_Kinds[{Slot}] == 255:', '    return None', f'if Scalar_Kinds[{Slot}] >= 3 and not -1125899906842624 <= Namespace[{Name!r}] <= 1125899906842624:', '    return None'])
            if Plan['Pure_Scalars']:
                Guards.extend([f'if Scalar_Kinds[{Slot}] != 0:', '    return None'])
        Guards.extend([f'Inputs[{Slot}] = Namespace[{Name!r}]', f'if not {Prefix}Finite(Inputs[{Slot}]):', '    return None'])
    for Name, Width in Plan['Array_Rows'].items():
        Guards.extend([f'if B.type(Namespace[{Name!r}]) is not N.ndarray or Namespace[{Name!r}].ndim != 2 or Namespace[{Name!r}].shape[1] != {Width}:', '    return None'])
    Carry = []
    for Name in Plan['Carry']:
        Slot = Plan['Slots'].index(Name)
        Value = f'{Prefix}Scalar_Box(Inputs[{Slot}], Scalar_Kinds[{Slot}], N)'
        Carry.extend([f'if Prefix_Assigned[{Slot}]:', f'    Carry_Updates[{Name!r}] = {Value}'])
    Final = copy.deepcopy(Plan['Original'])
    Final.iter = ast.parse(f"range({Plan['Index']}, {Plan['Index']} + 1)", mode='eval').body
    Body = ast.unparse(ast.fix_missing_locations(ast.Module(body=Final.body if 'Iterator' in Plan else [Final], type_ignores=[])))
    Replacements = dict(BUFFER_COUNT=str(len(Names)), SLOT_COUNT=str(len(Plan['Slots'])), RANK_COUNT=str(max(Value[1] for Value in Plan['Buffers'].values())), RANDOM_COUNT=str(Plan['Random_Count']), RANDOM_DYNAMIC=repr(Plan['Random_Dynamic']), RANDOM_ROOT=repr(Plan['Random_Roots'][0] if Plan['Random_Roots'] else ''), RANDOM_RANGES=repr(Plan['Random_Ranges']), BUFFER_NAMES=repr(Names), BUFFER_DIMENSIONS=repr(tuple(Plan['Buffers'][Name][1] for Name in Names)), BUFFER_READS=repr(tuple(Name in Plan['Read_Buffers'] for Name in Names)), BUFFER_WRITES=repr(tuple(Name in Plan['Writes'] for Name in Names)), REQUIRED_GUARDS='\n'.join(Guards), CARRY_UPDATES='\n'.join(Carry) or 'pass', REQUIRED_SLOTS=repr(tuple(Plan['Slots'].index(Name) for Name in Plan['Written'] if Name not in Plan['Carry'])), OUTER_INDEX=repr(Plan['Index']), WRITTEN_NAMES=repr(Plan['Written']), OBSERVED_NAMES=repr(tuple(dict.fromkeys((*Plan['Names'], *Plan['Written'])))), GLOBAL_BINDINGS=repr(tuple((Root, Plan.get('Global_Names', {}).get(Root, Root)) for Root, Name, Module in Plan['Math']['Bindings'] if Root not in Plan['Local_Bindings'])), CONSTANT_PREFIX=f'_Pyceler_Module_Constants_{Line}_', NUMERIC_PREFIX=Numeric, FAST_PREFIX=Prefix)
    Replacements['GLOBAL_BINDINGS'] = repr(_Global_Bindings(Plan))
    Replacements['BUFFER_SHAPE_ONLY'] = repr(tuple(Name in Plan.get('Shape_Only', ()) for Name in Names))
    Replacements['SCALAR_TYPE_NAMES'] = repr(tuple(_Array_Scalar_Types.values()))
    Range_Blocks = []
    Range_Names = []
    for Position, Expression in enumerate(Plan['Random_Ranges']):
        Name = Numeric + 'Random_Range_' + str(Position)
        Range_Names.append(Name)
        Range_Blocks.append(_Namespace_Block(Name, Expression, 'eval'))
    Replacements['RANDOM_RANGES'] = '(' + ', '.join(Range_Names) + (',' if Range_Names else '') + ')'
    Replacements['FLAT_REGION'] = repr(len(Plan['Loops']) == 1)
    Replacements['RECOVERABLE_TAIL'] = repr('Iterator' not in Plan)
    Outputs = Plan.get('Live_Outputs', Plan['Written'])  # Dead temporaries can finish natively; observable locals need original continuation semantics.
    Replacements['NATIVE_COMPLETE'] = repr(not Plan['Module'] and not Outputs and not Plan['Carry'] and not Plan['Random_Count'] and 'Iterator' not in Plan)
    Replacements['WRITTEN_NAMES'] = repr(Outputs)
    Replacements['REQUIRED_SLOTS'] = repr(tuple(Plan['Slots'].index(Name) for Name in Outputs if Name not in Plan['Carry']))
    Replacements['RECHECK_BUILTINS'] = '\n'.join([*_Builtin_Guards(Plan['Builtins'], Prefix), *_Helper_Guards(Plan, Line)]) or 'pass'
    Replacements['POLICY_GUARD'] = 'Mode = _Pyceler_Choose((B.len(Whole),), True, Policy) if Policy is not None else 2\nif Mode == 0:\n    return None' if Measured else 'Mode = 2'
    if Measured and 'Selection_Output' in Plan:
        Replacements['POLICY_GUARD'] = f"Mode = _Pyceler_Choose(Namespace.get({Plan['Selection_Output']!r}), False, Policy) if Policy is not None else 2\nif Mode == 0:\n    return None"
    Arguments = 'Buffers, Changed, Shapes, Strides, Buffer_Kinds, Output_Kinds, Inputs, Scalar_Kinds'
    Parallel_Code = [f'if {Plan["Parallel"]!r} and Mode != 1 and B.len(Span) >= 3 and Work_Size >= 4096 and not {Prefix}In_Parallel():', '    Parallel_OK = True', *('    ' + Row for Row in _Parallel_Bounds(Plan)), '    if Parallel_OK:', f'        Workers = min(8, {Prefix}Max_Threads()) if Mode < 100 else Mode - 100', '        Parts = min(Workers, B.len(Span) - 1, 256)', '        Team[0] = 1', f"        for Part in {Prefix}Prange(Parts, nogil=True, schedule='static', num_threads=Workers):", '            if Part == 0:', f'                Team[0] = {Prefix}Team_Size()', f'            Checks[Part] = {Numeric}Worker({Arguments}, Random_Values, Random_Total, Random_Per_Outer * ((Count - 1) * Part // Parts), Begin + Step * ((B.len(Span) - 1) * Part // Parts), Begin + Step * ((B.len(Span) - 1) * (Part + 1) // Parts), Step, &Saved, &Exceptions[Part])', '        Used_Parallel = True', '        for Part in range(Parts):', '            Valid = Valid and Checks[Part]', '            Flags |= Exceptions[Part]']
    Parallel_Code = [Row.replace('B.len(Span) - 1', 'Native_Count').replace('Count - 1', 'Native_Count') for Row in Parallel_Code]
    Replacements['PARALLEL_COMPUTE'] = '\n'.join(Parallel_Code) if Parallel else 'pass'
    if 'Selection_Output' in Plan:
        Reads = tuple(Index for Index, Name in enumerate(Names) if Name in Plan['Read_Buffers'])
        Template += f'\ncdef bint {Numeric}Storage(tuple Objects):\n    import builtins as B\n    N = {Prefix}System.modules.get("numpy")\n    if N is None:\n        return False\n    Single = False\n    for Slot, Value in B.enumerate(Objects):\n        if B.type(Value) is not N.ndarray:\n            return False\n        if Slot in {Reads!r}:\n            if Value.dtype.kind != "f" or Value.dtype.itemsize not in (4, 8):\n                return False\n            Single = Single or Value.dtype.itemsize == 4\n    return Single if {Plan["Single_Only"]!r} else True\n'
    for Name, Value in Replacements.items():
        Template = Template.replace(Name, Value.replace('\n', '\n    ') if Name in ('REQUIRED_GUARDS', 'POLICY_GUARD', 'CARRY_UPDATES', 'RECHECK_BUILTINS') else Value.replace('\n', '\n        ') if Name == 'PARALLEL_COMPUTE' else Value)
    for Name, Value in Replacements.items():
        if Name not in ('REQUIRED_GUARDS', 'POLICY_GUARD', 'CARRY_UPDATES', 'RECHECK_BUILTINS', 'PARALLEL_COMPUTE'):
            Template = Template.replace(Name, Value)
    Template = _Region_Guards(Template, Line)
    Faults = ['cdef extern from \"fenv.h\":', f'    int {Numeric}Clear_Exceptions \"feclearexcept\"(int) noexcept nogil', f'    int {Numeric}Invalid \"FE_INVALID\"', f'    int {Numeric}Divide \"FE_DIVBYZERO\"', f'    int {Numeric}Overflow \"FE_OVERFLOW\"', f'    int {Numeric}Underflow \"FE_UNDERFLOW\"']
    return '\n'.join([_Scope_Error_Declaration(Numeric), _Helper_Kernel(Plan, Line), *Faults, _Module_Constant_Kernel(Line), _Fast_Math_Kernel(Plan['Math'], Line, Parallel=Parallel, Preamble=True), *Range_Blocks, f'cdef object {Numeric}Body = compile({Body!r}, {Filename!r}, "exec", dont_inherit=True)', _Array_Compute(Plan, Line), Template, _Iterator_Kernel(Plan, Line)])
