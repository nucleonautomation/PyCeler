def _Parallel_Bounds(Plan):
    Lines = []
    for Name, (Axis, Scale, Offsets) in Plan.get('Parallel_Axes', {}).items():
        Slot = Plan['Buffers'][Name][0]
        Low = f'min(B.int(Begin) * ({Scale}), B.int(Last) * ({Scale})) + ({min(Offsets)})'
        High = f'max(B.int(Begin) * ({Scale}), B.int(Last) * ({Scale})) + ({max(Offsets)})'
        Shift = ' + '.join(f'({Scale}) * Namespace[{Parameter!r}]' for Parameter, Scale in Plan.get('Parallel_Shifts', {}).get(Name, ()))
        if Shift:
            Low, High = f'({Low}) + ({Shift})', f'({High}) + ({Shift})'
        Dimension = f'Shapes[{Slot}][{Axis}]'
        Lines.extend([f'if {Low} < -{Dimension} or {High} >= {Dimension} or ({High}) - ({Low}) >= {Dimension}:', '    Parallel_OK = False'])
    return Lines
# Split only proven-independent outer spans into workers; dependent reductions remain ordered.
def _Numeric_Worker(Plan, Line):
    Prefix, Numeric = f'_Pyceler_Fast_{Line}_', f'_Pyceler_Numeric_{Line}_'
    Count = len(Plan['Slots'])
    Parameters = 'double** Buffers, unsigned char** Changed, Py_ssize_t** Shapes, Py_ssize_t** Strides, double* Inputs, long long* Origins, long long** Owners, long long* Series, Py_ssize_t Begin, Py_ssize_t End, Py_ssize_t Step, int Part'
    Lines = [f'cdef bint {Numeric}Worker({Parameters}, const {Prefix}Environment* Saved, int* Flags, Py_ssize_t* Progress) noexcept nogil:',
             f'    cdef double Local_Inputs[{Count}]', f'    cdef long long Local_Origins[{Count}], Sequence[2]',
             f'    cdef unsigned char Assigned[{Count}]', '    cdef bint Valid = True', '    cdef Py_ssize_t Slot',
             f'    cdef {Prefix}Environment Previous', f'    {Prefix}Get_Environment(&Previous)', f'    {Prefix}Set_Environment(Saved)',
             '    Sequence[0], Sequence[1] = Series[Part], 256', f'    for Slot in range({Count}):',
             '        Local_Inputs[Slot] = Inputs[Slot]', '        Local_Origins[Slot] = Origins[Slot]',
             f'    _Pyceler_Numeric_Compute_{Line}(Buffers, Changed, Shapes, Strides, Local_Inputs, Local_Origins, Owners, Sequence, Begin, End, Step, Assigned, &Valid, Progress)',
             '    Series[Part] = Sequence[0]', f'    Flags[0] = {Prefix}Test_Exceptions({Prefix}All_Exceptions)',
             f'    {Prefix}Set_Environment(&Previous)', '    return Valid']
    return '\n'.join(Lines) + '\n'
# Worker failure must preserve the last validated prefix and route remaining work through continuation.
def _Numeric_Parallel(Plan, Line):
    Prefix, Numeric = f'_Pyceler_Fast_{Line}_', f'_Pyceler_Numeric_{Line}_'
    Lines = [f'if Mode != 1 and Count >= 3 and (Total >= 4096 or ({len(Plan["Loops"]) > 1!r} and Count >= 128)) and not ' + Prefix + 'In_Parallel():', '    Parallel_OK = True']
    Lines.extend('    ' + Row for Row in _Parallel_Bounds(Plan))
    Lines.extend(['    if Parallel_OK:', f'        Workers = min(8, {Prefix}Max_Threads()) if Mode < 100 else Mode - 100',
                  '        Team[0] = 1', '        Progress = Count', '        for Part in range(256):', '            Series[Part] = Part',
                  '        for Chunk in range(0, Count - 1, 65536):', f'            {Prefix}Signals()',
                  '            Width = min(65536, Count - 1 - Chunk)', '            Parts = min(Workers, Width, 256)',
                  f"            for Part in {Prefix}Prange(Parts, nogil=True, schedule='static', num_threads=Workers):",
                  '                if Part == 0:', f'                    Team[0] = {Prefix}Team_Size()',
                  f'                Checks[Part] = {Numeric}Worker(Buffers, Changed, Shapes, Strides, Inputs, Origins, Owners, Series, Begin + Step * (Chunk + Width * Part // Parts), Begin + Step * (Chunk + Width * (Part + 1) // Parts), Step, Part, &Saved, &Exceptions[Part], &Failures[Part])',
                  '            Used_Parallel = True', '            for Part in range(Parts):',
                  '                Valid = Valid and Checks[Part]', '                Flags |= Exceptions[Part]',
                  '                if not Checks[Part]:', '                    Progress = min(Progress, Chunk + Width * Part // Parts + Failures[Part])',
                  '            if not Valid:', '                break'])
    return '\n'.join(Lines)
