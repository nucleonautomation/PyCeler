from Native_Types cimport _Adjust
include "Parts/Increment.pxi"

cdef extern from "Parts/Native_Value.h":
    int _Native_Value(int Value)

def Transform(int Value):
    return _Native_Value(_Increment(_Adjust(Value)))
