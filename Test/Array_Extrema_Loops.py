import numpy as N
# Test support/workload for dtype-preserving extrema, clamped indices and repeated reductions.
def Clamp(Values, Output, Low, High):
    for Row in range(len(Values)):
        for Column in range(len(Values[0])):
            Value = min(High, max(Low, Values[Row, Column]))
            Output[Row, Column] = Value * 1.0000001 + 0.0000001
    return Output

def Extrema(Left, Right, Output, Bound):
    for Row in range(len(Left)):
        Output[Row, 0] = min(Left[Row], Right[Row], Bound)
        Output[Row, 1] = max(Bound, Left[Row], Right[Row])
        Value = min(Bound, Left[Row], Right[Row])
        Output[Row, 2] = Value * 1.0000001
    return Output

def Convolution(Values, Kernel, Output):
    Height, Width, Channels = Values.shape
    for Row in range(Height):
        for Column in range(Width):
            for Channel in range(Channels):
                Total = 0.0
                for Vertical in range(3):
                    for Horizontal in range(3):
                        Y = min(max(Row + Vertical - 1, 0), Height - 1)
                        X = min(max(Column + Horizontal - 1, 0), Width - 1)
                        Total += Values[Y, X, Channel] * Kernel[Vertical, Horizontal]
                Output[Row, Column, Channel] = min(200.0, max(-10.0, Total))
    return Output

def Binned(Values, Output):
    for Row in range(len(Values)):
        for Column in range(len(Values[0])):
            Index = min(15, max(0, int(Values[Row, Column])))
            Output[Index] += 1
    return Output

def Scaled_Window(Values, Output, Divisor):
    Height, Width = Values.shape
    for Row in range(Height // Divisor):
        for Column in range(Width // Divisor):
            Total = 0.0
            for Vertical in range(Divisor):
                for Horizontal in range(Divisor):
                    Total += Values[Row * Divisor + Vertical, Column * Divisor + Horizontal]
            Output[Row, Column] = Total
    return Output

def Signed_Division(Values, Output, Divisor):
    for Row in range(len(Values)):
        Index = int(Values[Row]) // Divisor
        Output[Row] = Index
    return Output

def Borrowed(Values, Bound):
    Result = Bound
    for Row in range(len(Values)):
        Result = min(Bound, Values[Row])
    return Result, Result is Bound

def Repeated_Scales(Values):
    Height, Width = Values.shape
    First = N.zeros((Height // 2, Width // 2))
    Second = N.zeros((Height // 4, Width // 4))
    for Row in range(Height // 2):
        for Column in range(Width // 2):
            Total = 0.0
            for Vertical in range(2):
                for Horizontal in range(2):
                    Total += Values[Row * 2 + Vertical, Column * 2 + Horizontal]
            First[Row, Column] = Total * 0.25
    for Row in range(Height // 4):
        for Column in range(Width // 4):
            Total = 0.0
            for Vertical in range(2):
                for Horizontal in range(2):
                    Total += First[Row * 2 + Vertical, Column * 2 + Horizontal]
            Second[Row, Column] = Total * 0.25
    return First, Second
