cdef void Fill_Helper(long[::1] Values):
    cdef Py_ssize_t Index
    for Index from 0 <= Index < Values.shape[0]:
        Values[Index] = 1
