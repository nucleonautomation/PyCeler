from .Fast_Math import _Fast_Emit
from .Array_Expressions import _Array_Emitted_Tag
from .Numeric_Identity import _Identity_Emit
from .Buffer_Indices import _Buffer_Offset
# Emit ordered statements from region IR, retaining loop control and bounded progress checks.
def _Value(Node, Lines, Variables, Functions, Prefix, Indent):
    Work = []
    Value = _Fast_Emit(Node, Work, Variables, Functions, Prefix)
    Lines.extend(Indent + Line[4:] for Line in Work)
    return Value

def _Tick(Lines, Indent):
    Lines.extend([Indent + "Ticks += 1", Indent + "if Ticks > 1048576:", Indent + "    Valid[0] = False", Indent + "    return 0.0"])
# Preserve statement order and final locals when translating region instructions into native code.
def _Emit(Program, Lines, Variables, Functions, Prefix, Cursors, Indent, Array=False, Identity=False):
    for Instruction in Program:
        Kind = Instruction[0]
        if Kind == "store":
            Value = _Value(Instruction[2], Lines, Variables, Functions, Prefix, Indent)
            Lines.extend([f"{Indent}L{Instruction[1]} = {Value}", f"{Indent}Assigned[{Instruction[1]}] = 1"])
            if Array:
                Lines.append(f'{Indent}Scalar_Kinds[{Instruction[1]}] = {_Array_Emitted_Tag(Instruction[2], Value)}')
            if Identity:  # Object-origin tracking is needed for list values even when numeric values agree.
                _Identity_Emit(Instruction[3], f'Origins[{Instruction[1]}]', Lines, Indent)
        elif Kind == "write":
            Value = _Value(Instruction[3], Lines, Variables, Functions, Prefix, Indent)
            Saved = "T" + str(len(Variables))
            Variables.append(Saved)
            Lines.append(f"{Indent}{Saved} = {Value}")
            Coordinates = [_Value(Node, Lines, Variables, Functions, Prefix, Indent) for Node in Instruction[2]]
            Offset = _Buffer_Offset(Instruction[1], Coordinates, Lines, Indent)
            if Array:
                Lines.extend([f'{Indent}{Saved} = {Prefix}Array_Cast({Saved}, Output_Kinds[{Instruction[1]}], Valid)', f'{Indent}if not Valid[0]:', Indent + '    return 0.0', f'{Indent}{Prefix}Array_Store(Buffers[{Instruction[1]}], {Offset}, {Saved}, Output_Kinds[{Instruction[1]}], Buffer_Kinds[{Instruction[1]}] == 0)', f'{Indent}Changed[{Instruction[1]}][{Offset}] = 1'])
                continue
            if Identity:
                _Identity_Emit(Instruction[4], 'Owner', Lines, Indent)
                Lines.extend([Indent + 'if Owner == 0:', Indent + '    Valid[0] = False', Indent + '    return 0.0', f'{Indent}Owners[{Instruction[1]}][{Offset}] = Owner'])
            Lines.extend([f"{Indent}Buffers[{Instruction[1]}][{Offset}] = {Saved}", f"{Indent}Changed[{Instruction[1]}][{Offset}] = 1"])
        elif Kind == "if":
            Value = _Value(Instruction[1], Lines, Variables, Functions, Prefix, Indent)
            Lines.append(f"{Indent}if {Value}:")
            _Emit(Instruction[2], Lines, Variables, Functions, Prefix, Cursors, Indent + "    ", Array, Identity)
            Lines.append(Indent + "else:")
            _Emit(Instruction[3], Lines, Variables, Functions, Prefix, Cursors, Indent + "    ", Array, Identity)
        elif Kind == "for":
            Begin = _Value(Instruction[2], Lines, Variables, Functions, Prefix, Indent)
            Cursor, End, Step = "Cursor" + str(len(Cursors)), "End" + str(len(Cursors)), "Step" + str(len(Cursors))
            Cursors.extend((Cursor, End, Step))
            Lines.append(f"{Indent}{Cursor} = <Py_ssize_t>({Begin})")
            Stop = _Value(Instruction[3], Lines, Variables, Functions, Prefix, Indent)
            Lines.append(f"{Indent}{End} = <Py_ssize_t>({Stop})")
            Stride = _Value(Instruction[4], Lines, Variables, Functions, Prefix, Indent)
            Lines.extend([f"{Indent}{Step} = <Py_ssize_t>({Stride})", f"{Indent}if {Step} == 0:", Indent + "    Valid[0] = False", Indent + "    return 0.0", f"{Indent}while ({Step} > 0 and {Cursor} < {End}) or ({Step} < 0 and {Cursor} > {End}):", f"{Indent}    L{Instruction[1]} = {Cursor}", f"{Indent}    {Cursor} += {Step}", f"{Indent}    Assigned[{Instruction[1]}] = 1"])
            if Identity:
                _Identity_Emit(('fresh',), f'Origins[{Instruction[1]}]', Lines, Indent + '    ')
            if Array:
                Lines.append(f'{Indent}    Scalar_Kinds[{Instruction[1]}] = 4')
            _Emit(Instruction[5], Lines, Variables, Functions, Prefix, Cursors, Indent + "    ", Array, Identity)
        elif Kind == "while":
            Lines.append(Indent + "while True:")
            Test = _Value(Instruction[1], Lines, Variables, Functions, Prefix, Indent + "    ")
            Lines.extend([f"{Indent}    if not {Test}:", Indent + "        break"])
            _Tick(Lines, Indent + "    ")
            _Emit(Instruction[2], Lines, Variables, Functions, Prefix, Cursors, Indent + "    ", Array, Identity)
        else:
            Lines.append(Indent + Kind)
    if not Program:
        Lines.append(Indent + "pass")

def _Numeric_Compute(Plan, Line, Parallel=False):
    Prefix = f"_Pyceler_Fast_{Line}_"
    Variables = ["L" + str(Index) for Index in range(len(Plan["Slots"]))]
    Work, Cursors = [], []
    _Emit(Plan["Program"], Work, Variables, Plan["Math"]["Functions"], Prefix, Cursors, "        ", Identity=Plan.get('Dynamic_Identity', False))
    Lines = [f"@{Prefix}Division(True)", f"cdef double _Pyceler_Numeric_Compute_{Line}(double** Buffers, unsigned char** Changed, Py_ssize_t** Shapes, Py_ssize_t** Strides, double* Inputs, long long* Origins, long long** Owners, long long* Sequence, Py_ssize_t Begin, Py_ssize_t End, Py_ssize_t Step, unsigned char* Assigned, bint* Valid, Py_ssize_t* Progress) except? -1:", "    cdef Py_ssize_t Outer", "    cdef long long Owner", "    cdef unsigned int Ticks", "    cdef int* Error = " + Prefix + "Error_Address()"]
    for Start, Type in (("L", "double"), ("T", "volatile double")):
        Group = [Name for Name in Variables if Name.startswith(Start)]
        if Group:
            Lines.append("    cdef " + Type + " " + ", ".join(Group))
    if Cursors:
        Lines.append("    cdef Py_ssize_t " + ", ".join(Cursors))
    Lines.extend(f"    L{Index} = Inputs[{Index}]" for Index in range(len(Plan["Slots"])))
    Index = Plan["Slots"].index(Plan["Index"])
    Lines.extend([*[f"    Assigned[{Slot}] = 0" for Slot in range(len(Plan["Slots"]))], "    Outer = Begin", "    Progress[0] = -1", "    while (Step > 0 and Outer < End) or (Step < 0 and Outer > End):", "        Progress[0] += 1", f"        {Prefix}Signals()", "        Ticks = 0", f"        L{Index} = Outer", "        Outer += Step", f"        Assigned[{Index}] = 1"])
    if Plan.get('Dynamic_Identity'):
        _Identity_Emit(('fresh',), f'Origins[{Index}]', Lines, '        ')
    Lines.extend(Work)
    Lines.extend(f"    Inputs[{Index}] = L{Index}" for Index in range(len(Plan["Slots"])))
    Lines.append("    return 1.0")
    if Parallel:
        Lines = [Row.replace('except? -1:', 'noexcept nogil:') for Row in Lines if Row != f'        {Prefix}Signals()']
    return "\n".join(Lines) + "\n"
