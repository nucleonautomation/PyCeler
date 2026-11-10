from cython.parallel cimport prange
include "Native_Helper.pxi"

raise RuntimeError("Static analysis must not execute native source")

cpdef Fill(long[::1] Values):
    cdef Py_ssize_t Index
    for Index in range(Values.shape[0]):
        Values[Index] = 0
    return Values

cdef void Prefix(long[::1] Values):
    cdef Py_ssize_t Index
    for Index in range(1, Values.shape[0]):
        Values[Index] += Values[Index - 1]

def Parallel_Fill(long[::1] Values):
    cdef Py_ssize_t Index
    for Index in prange(Values.shape[0], nogil=True):
        Values[Index] = 0

cdef class Example:
    def Count(self, int Count):
        cdef int Index = 0
        while Index < Count:
            Index += 1
        return Index
