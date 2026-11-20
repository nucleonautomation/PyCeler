# Focused nested scope cases workload; ordinary Python inputs include supported and retained cases.
from math import sin
import math as _Private__math
# Test support/workload for closures, class-private names and lexical scope.
Factor = 9.0

def List_Factory():
    def Kernel(Source, Output, Factor, N):
        for I in range(N):
            Output[I] = Source[I] * Factor + 0.125
        return Output
    return Kernel

def Array_Factory():
    def Kernel(Source: 'numpy.ndarray', Output: 'numpy.ndarray', Factor, N):
        for I in range(N):
            Output[I] = Source[I] * Factor + 0.125
        return Output
    return Kernel

def Captured_List(Source, Factor):
    from math import sin
    def Kernel(Output, N):
        for I in range(N):
            Output[I] = sin(Source[I]) * Factor + 0.125
        return Output
    def Change(Value, Operation):
        nonlocal Factor, sin
        Factor, sin = Value, Operation
    return Kernel, Change

def Captured_Array(Source, Factor):
    from math import sin
    def Kernel(Output):
        for I in range(Source.shape[0]):
            Output[I] = sin(Source[I]) * Factor + 0.125
        return Output
    def Change(Value, Operation):
        nonlocal Factor, sin
        Factor, sin = Value, Operation
    return Kernel, Change

def Shadowed_Builtin(abs):
    def Kernel(Source, Output, N):
        for I in range(N):
            Output[I] = abs(Source[I]) + 0.125
        return Output
    return Kernel

def Nonlocal_Counter():
    Count = 0
    def Kernel(Source, Output, N):
        nonlocal Count
        for I in range(N):
            Output[I] = Source[I] * 0.5
            Count += 1
        return Count
    return Kernel

def Unbound_Capture():
    Factor = 2
    def Kernel(Source, Output, N):
        for I in range(N):
            Output[I] = Source[I] * 0.25
            Output[I] += Factor * 0.5
        return Output
    del Factor
    return Kernel

def Shadowed_Local(Factor):
    def Kernel(Source, Output, N):
        for I in range(N):
            Output[I] = Source[I] * 0.25
            Output[I] += Factor * 0.5
        Factor = 2
        return Output
    return Kernel

def Array_Shadowed_Local(Source, Output):
    for I in range(Source.shape[0]):
        Output[I] = Source[I] * 0.25
        Output[I] += Factor * 0.5
    Factor = 2
    return Output

def Unbound_Math(Source, Output, N):
    for I in range(N):
        Output[I] = Source[I] * 0.25
        Output[I] += math.sin(Source[I])
    import math
    return Output

def Unused_Length(Source, Output, N):
    for I in range(N):
        Output[I] = Source[I] * 0.5 + 0.125
    len = 7
    return Output

def Captured_Length():
    len = 7
    def Kernel(Source, Output, N):
        for I in range(N):
            Output[I] = Source[I] * 0.25
            Output[I] += len(Source) * 0.5
        return Output
    del len
    return Kernel

def Lambda_Default_Shadow():
    Make = lambda Value=(sin := lambda Value: Value + 0.25): Value
    def Kernel(Source, Output, N):
        for I in range(N):
            Output[I] = sin(Source[I]) + 0.125
        return Output
    return Kernel

def Function_Default_Shadow():
    def Make(Value=(sin := lambda Value: Value + 0.5)):
        return Value
    def Kernel(Source, Output, N):
        for I in range(N):
            Output[I] = sin(Source[I]) + 0.125
        return Output
    return Kernel

class Private:
    def Kernel(self, Source, Output, N):
        for I in range(N):
            Output[I] = __math.sin(Source[I]) + 0.125
        return Output
