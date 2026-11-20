import math
# Test support/workload for monitoring.
def Transform(Value):
    return Value * 0.5 + math.sin(Value)

def Apply(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = Transform(Source[Index])
    return Output

def Inline(Source, Output):
    for Index in range(len(Source)):
        Value = Source[Index] + 0.0
        for Step in range(3):
            Value = Value * 0.5 + math.sin(Value)
        Output[Index] = Value
    return Output
