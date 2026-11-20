# Focused helper local loops workload; ordinary Python inputs include supported and retained cases.
import math
# Test support/workload for pure-helper local computations and unused arguments.
def Polynomial(Value, Weight):
    Scaled = Value * Weight
    Curve = Scaled * Scaled + Scaled
    Curve += math.sin(Value)
    return Curve

def Nested(Value):
    First = Polynomial(Value, 0.75)
    Second = Polynomial(Value + 0.125, 0.5)
    return First + Second

def Unused(Value, Divisor):
    Ignored = Value / Divisor
    Result = math.sin(Value)
    return Result

def Apply(Source, Output):
    for Index, Value in enumerate(Source):
        Output[Index] = Nested(Value)
    return Output

def With_Error(Source, Output, Divisor):
    for Index, Value in enumerate(Source):
        Output[Index] = Unused(Value, Divisor - Value)
    return Output

def Heavy(Source, Output):
    for Index, Value in enumerate(Source):
        Result = Nested(Value)
        for Step in range(10):
            Result = Polynomial(Result * 0.5, 0.75)
        Output[Index] = Result
    return Output
