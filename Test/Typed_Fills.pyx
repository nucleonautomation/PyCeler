def Fill_Int(int[::1] Output, int Value):
    cdef Py_ssize_t Index
    for Index in range(Output.shape[0]):
        Output[Index] = Value

def Fill_Float(float[::1] Output, float Value):
    cdef Py_ssize_t Index
    for Index in range(Output.shape[0]):
        Output[Index] = Value
    return None

def Clear_Double(double[::1] Output):
    cdef Py_ssize_t Index
    for Index in range(Output.shape[0]):
        Output[Index] = 0
