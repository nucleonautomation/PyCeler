def Shared(Source, First, Second, N):
    for I in range(N):
        Value = Source[I] * 0.75 + 0.125
        First[I] = Value
        Second[I] = Value
    return First, Second
# Test support/workload for list storage and publication semantics.
def Divide(Source, Output, N):
    for I in range(N):
        Output[I] = 1.0 / Source[I] + 0.125
    return Output

def Nested(Source, Output, N):
    for I in range(N):
        Value = Source[I] * 0.75
        for J in range(3):
            Value = Value * 0.5 + 0.125
        Output[I] = Value
    return Output

def Divide_Stepped(Source, Output, Start, Stop, Step):
    for I in range(Start, Stop, Step):
        Output[I] = 1.0 / Source[I] + 0.125
    return Output
