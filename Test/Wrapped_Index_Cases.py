import math
# Test support/workload for negative/wrapped indices, aliasing and scalar identity.
def Reverse(Source, Output, Count):
    for Index in range(Count):
        Output[-Index - 1] = Source[-Index - 1] * 1.25 + 0.5
    return Output

def Stepped(Source, Output, Begin, End, Step):
    for Index in range(Begin, End, Step):
        Output[Index] = Source[Index] * 1.25 + 0.5
    return Output

def Negate(Source, Output, Count):
    for Index in range(Count):
        Output[-Index - 1] = -Source[-Index - 1]
    return Output

def Rows(Source, Output, Count, Width):
    for Row in range(Count):
        for Column in range(Width):
            Output[-Row - 1][-Column - 1] = Source[-Row - 1][-Column - 1] * 1.25 + 0.5
    return Output

def In_Place(Values, Begin, End):
    for Index in range(Begin, End):
        Values[Index] = Values[Index] * 1.25 + 0.5
    return Values

def Wrapped_Alias(Values, Source, Begin, End):
    for Index in range(Begin, End):
        Values[Index] = Values[Index] * 1.25 + Source[0] * 0.5
    return Values

def Shared_Indices(Left, Right, Begin, End):
    for Index in range(Begin, End):
        Left[Index - Begin] = Index
        Right[Index - Begin] = Index
    return Left, Right

def Carried_Index(Left, Right, Count):
    for Index in range(Count):
        Value = Index
        Left[Index] = Value
        Right[Index] = Value
    return Left, Right

def Index_And_Copy(Left, Right, Count):
    for Index in range(Count):
        Left[Index] = Index
        Right[Index] = Index + 0
    return Left, Right

def Repeated_Indices(Left, Right, Count, Width):
    for Row in range(Count):
        for Index in range(300, 300 + Width):
            Left[Row][Index - 300] = Index
            Right[Row][Index - 300] = Index
    return Left, Right

def Array_Reverse(Source: 'numpy.ndarray', Output, Count):
    for Index in range(Count):
        Output[-Index - 1] = Source[-Index - 1] * 1.25 + 0.5
    return Output

def Array_Rows(Source: 'numpy.ndarray', Output, Count, Width):
    for Row in range(Count):
        for Column in range(Width):
            Output[-Row - 1][-Column - 1] = Source[-Row - 1][-Column - 1] * 1.25 + 0.5
    return Output

def Array_Alias(Values: 'numpy.ndarray', Source, Begin, End):
    for Index in range(Begin, End):
        Values[Index] = Values[Index] * 1.25 + Source[0] * 0.5
    return Values

def Heavy(Source, Output, Count):
    for Index in range(Count):
        Value = 0.0
        for Phase in range(128):
            Value += math.sin(Source[-Index - 1] + Phase * 0.001)
        Output[-Index - 1] = Value
    return Output
