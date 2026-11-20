_Array_Scalar_Types = {1: 'float32', 2: 'float64', 3: 'bool_', 11: 'int8', 12: 'int16', 14: 'int32', 18: 'int64', 21: 'uint8', 22: 'uint16', 24: 'uint32', 28: 'uint64'}
# Generate exact integer-copy guards, NumPy scalar promotion rules and boxing at Python/native boundaries.
def _Array_Integer_Copy(Prefix):
    Lines = [f'cdef bint {Prefix}Integer_Copy(void* Source, double* Target, Py_ssize_t Count, int Kind) noexcept nogil:', '    cdef Py_ssize_t Position', '    cdef long long Signed', '    cdef unsigned long long Unsigned']
    Types = {11: 'signed char', 12: 'short', 14: 'int', 18: 'long long', 21: 'unsigned char', 22: 'unsigned short', 24: 'unsigned int', 28: 'unsigned long long'}
    for Kind, Type in Types.items():
        Value = 'Signed' if Kind < 20 else 'Unsigned'
        Test = 'Signed < -1125899906842624LL or Signed > 1125899906842624LL' if Kind < 20 else 'Unsigned > 1125899906842624ULL'
        Lines.extend([f'    if Kind == {Kind}:', '        for Position in range(Count):', f'            {Value} = (<{Type}*>Source)[Position]', f'            if {Test}:', '                return False', f'            Target[Position] = <double>{Value}', '        return True'])
    Lines.append('    return False')
    return '\n'.join(Lines) + '\n'

def _Array_Scalar_Kernel(Prefix):
    Lines = [f'cdef inline bint {Prefix}Scalar_Integer_Valid(double Value, int Kind) noexcept nogil:', '    if Value < -1125899906842624.0 or Value > 1125899906842624.0:', '        return False', '    if Kind == 3 or Kind == 5:', '        return Value == 0.0 or Value == 1.0']
    for Kind, Low, High in ((11, -128, 127), (12, -32768, 32767), (14, -2147483648, 2147483647), (21, 0, 255), (22, 0, 65535), (24, 0, 4294967295), (28, 0, 1125899906842624)):
        Lines.extend([f'    if Kind == {Kind}:', f'        return {Low}.0 <= Value <= {High}.0'])
    Lines.extend(['    return True', f'cdef inline int {Prefix}Scalar_Promote(int Left, int Right, bint Divide) noexcept nogil:', '    cdef int Kind, Signed, Unsigned', '    if Left == 2 or Right == 2:', '        return 2', '    if Left == 1 or Right == 1:', '        Kind = Right if Left == 1 else Left', '        return 2 if Kind >= 10 and Kind % 10 >= 4 else 1', '    if Left == 0 or Right == 0:', '        return 2 if Left >= 10 or Right >= 10 or Left == 3 or Right == 3 else 0', '    if Divide:', '        return 2 if Left >= 10 or Right >= 10 or Left == 3 or Right == 3 else 0', '    if Left == 3:', '        if Right == 3 or Right == 5:', '            return 255', '        return 18 if Right == 4 else Right', '    if Right == 3:', '        if Left == 5:', '            return 255', '        return 18 if Left == 4 else Left', '    if Left < 10:', '        return Right if Right >= 10 else 4', '    if Right < 10:', '        return Left', '    if (Left < 20) == (Right < 20):', '        return max(Left, Right)', '    Signed = Left if Left < 20 else Right', '    Unsigned = Right if Right >= 20 else Left', '    if Signed % 10 > Unsigned % 10:', '        return Signed', '    return 2 if Unsigned == 28 else 10 + (Unsigned % 10) * 2', f'cdef int {Prefix}Scalar_Kind(object Value, object N):', '    import builtins as B', '    Kind = B.type(Value)', '    if Kind is int:', '        return 4', '    if Kind is float:', '        return 0', '    if Kind is bool:', '        return 5'])
    for Kind, Name in _Array_Scalar_Types.items():
        Lines.extend([f'    if Kind is N.{Name}:', f'        return {Kind}'])
    Lines.extend(['    return 255', f'cdef object {Prefix}Scalar_Box(double Value, int Kind, object N):', '    if Kind == 4:', '        return int(Value)', '    if Kind == 5:', '        return bool(Value)'])
    for Kind, Name in _Array_Scalar_Types.items():
        Lines.extend([f'    if Kind == {Kind}:', f'        return N.{Name}(Value)'])
    Lines.append('    return Value')
    return _Array_Integer_Copy(Prefix) + '\n'.join(Lines) + '\n'
