# Focused iterator loops workload; ordinary Python inputs include supported and retained cases.
import math
# Test support/workload for iterator construction, target bindings and strict mismatch.
def Enumerated(Source, Output, Start: int):
    for Index, Value in enumerate(Source, start=Start):
        Result = math.sin(Value) + math.cos(Value)
        for Step in range(12):
            Result = Result * 0.99 + math.sqrt(Value + 1.0) * 0.001
        Output[Index - Start] = Result
    return Output, Index, Value

def Array_Enumerated(Source: 'numpy.ndarray', Output: 'numpy.ndarray', Start: int):
    for Index, Value in enumerate(Source, Start):
        Result = math.sin(Value) + math.cos(Value)
        for Step in range(12):
            Result = Result * 0.99 + math.sqrt(Value + 1.0) * 0.001
        Output[Index - Start] = Result
    return Output, Index, Value

def Zipped(First, Second, Output):
    Index = 0
    for Left, Right in zip(First, Second):
        Output[Index] = math.sin(Left) + math.cos(Right)
        Index += 1
    return Output, Index, Left, Right

def Strict(First, Second, Output):
    Index = 0
    for Left, Right in zip(First, Second, strict=True):
        Output[Index] = math.sin(Left) + math.cos(Right)
        Index += 1
    return Output, Index, Left, Right

def Array_Zipped(First: 'numpy.ndarray', Second: 'numpy.ndarray', Output: 'numpy.ndarray'):
    Index = 0
    for Left, Right in zip(First, Second):
        Output[Index] = math.sin(Left) + math.cos(Right)
        Index += 1
    return Output, Index, Left, Right

def Negative_Start(Source, Output):
    for Index, Value in enumerate(Source, -3):
        Output[Index + 3] = math.sin(Value)
    return Output, Index, Value

def Shifted_Range(Source, Output, Start: int):
    for Index in range(Start, Start + len(Source)):
        Value = Source[Index - Start]
        Output[Index - Start] = math.sin(Value)
    return Output, Index, Value
