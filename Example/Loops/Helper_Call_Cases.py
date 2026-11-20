# Focused helper call cases workload; ordinary Python inputs include supported and retained cases.
import math
from math import cos as Cosine
# Test support/workload for helper argument order, identity and guarded inlining.
def Scale(Value, Unused):
    return Value * 0.5

def Square(Value):
    return Value * Value

def Blend(First, /, Second, Third):
    return First * Second + Third

def Trig(Value):
    return math.sin(Value) + Cosine(Value)

def Nested(Value):
    return Square(Value + 0.125) + Trig(Value)

def Integer_First(Value):
    return Value * Value * 0.5

def Divide(First, Second):
    return First / Second

def Adjust(Value):
    return Value * 0.1 if Value < 0.0 else Value + 0.3

def Choose(First, Second):
    return First * 0.1 if First < 0.1 else Second + 0.3

def Nested_Choice(First, Second):
    return (Choose(First, Second) + 1.234567) * 0.333333

def Apply(Source, Output, Count):
    for Index in range(Count):
        Output[Index] = Nested(Source[Index])
    return Output

def Inline(Source, Output, Count):
    for Index in range(Count):
        Value = Source[Index] + 0.125
        Output[Index] = Value * Value + (math.sin(Source[Index]) + Cosine(Source[Index]))
    return Output

def Local_Alias(Source, Output, Count):
    from math import cos as Wave
    for Index in range(Count):
        Output[Index] = Wave(Source[Index]) + 0.125
    return Output

def Captured_Alias():
    from math import sin as Wave
    def Apply_Captured(Source, Output, Count):
        for Index in range(Count):
            Output[Index] = Wave(Source[Index]) + 0.125
        return Output
    return Apply_Captured

def Keywords(Source, Output, Count):
    for Index in range(Count):
        Output[Index] = Blend(Source[Index], Third=1.0 / (Index - 5), Second=0.25)
    return Output

def Unused_Argument(Source, Output, Count):
    for Index in range(Count):
        Output[Index] = Scale(Source[Index], 1.0 / (Index - 7))
    return Output

def Keyword_Order(Source, Output, Count):
    for Index in range(Count):
        Output[Index] = Blend(Source[Index], Third=math.sqrt(-1.0 if Index == 5 else 0.25), Second=1.0 / (Index - 5))
    return Output

def Integer_Intermediate(Source, Output, Count):
    for Index in range(Count):
        Output[Index] = Integer_First(Source[Index])
    return Output

def Shared_Result(Source, Left, Right, Count):
    for Index in range(Count):
        Value = Nested(Source[Index])
        Left[Index] = Value
        Right[Index] = Value
    return Left, Right, Value

def Shadowed_Math(Source, Output, Count):
    math = None
    Cosine = None
    for Index in range(Count):
        Output[Index] = Nested(Source[Index])
    return Output, math, Cosine

def Local_Callable(Source, Output, Count, Nested):
    for Index in range(Count):
        Output[Index] = Nested(Source[Index])
    return Output

def Captured_Callable(Nested):
    def Apply_Captured(Source, Output, Count):
        for Index in range(Count):
            Output[Index] = Nested(Source[Index])
        return Output
    return Apply_Captured

def Array_Apply(Source: 'numpy.ndarray', Output: 'numpy.ndarray', Count):
    for Index in range(Count):
        Output[Index] = Nested(Source[Index])
    return Output

def Array_Arithmetic(Source: 'numpy.ndarray', Output: 'numpy.ndarray', Count):
    for Index in range(Count):
        Output[Index] = Square(Source[Index] + 0.125)
    return Output

def Array_Conditional(Source: 'numpy.ndarray', Output: 'numpy.ndarray', Count):
    for Index in range(Count):
        Output[Index] = (Adjust(Source[Index]) + 1.234567) * 0.333333
    return Output

def Array_Mixed_Choice(First: 'numpy.ndarray', Second: 'numpy.ndarray', Output: 'numpy.ndarray', Count):
    for Index in range(Count):
        Value = -Nested_Choice(First[Index], Second[Index])
        Output[Index] = abs(Value) + 0.1234567
    return Output

def Array_Inline_Choice(Source: 'numpy.ndarray', Output: 'numpy.ndarray', Count):
    for Index in range(Count):
        Value = Source[Index] * 0.1 if Source[Index] < 0.1 else Source[Index] + 0.3
        Output[Index] = (Value + 1.234567) * 0.333333
    return Output

def Heavy(Source, Output, Count):
    for Index in range(Count):
        Value = Source[Index] + 0.0
        for Step in range(128):
            Value = Trig(Value) * 0.125
        Output[Index] = Value
    return Output
