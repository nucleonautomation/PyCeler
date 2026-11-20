import math
# Test support/workload for expanded numeric.
def Volume(Source, Target, Layers, Rows, Columns):
    for A in range(1, Layers - 1):
        for B in range(1, Rows - 1):
            for C in range(1, Columns - 1):
                Value = Source[A - 1][B][C] + Source[A + 1][B][C]
                Value = Value + Source[A][B - 1][C] + Source[A][B + 1][C]
                Value = Value + Source[A][B][C - 1] + Source[A][B][C + 1]
                Target[A][B][C] = Value * 0.125 + Source[A][B][C] * 0.25
    return Target

def Initialize(Volume, Layers, Rows, Columns):
    for A in range(Layers):
        for B in range(Rows):
            for C in range(Columns):
                X = (A - Layers / 3) * 0.1
                Y = (B - Rows / 4) * 0.2
                Z = (C - Columns / 5) * 0.3
                Volume[A][B][C] = math.exp(-(X * X + Y * Y + Z * Z))
    return Volume

def Neighbors(Source, Target, Rows, Columns):
    for A in range(1, Rows - 1):
        for B in range(1, Columns - 1):
            Total = Source[A - 1][B] + Source[A + 1][B] + Source[A][B - 1] + Source[A][B + 1]
            Occupied = Source[A][B]
            if Occupied:
                if Total == 2 or Total == 3:
                    Target[A][B] = 1
            else:
                if Total == 3:
                    Target[A][B] = 1
    return Target

def Mark(Flags, Begin, End, Step):
    for Position in range(Begin, End, Step):
        Flags[Position] = False
    return Flags

def Count_Flags(Flags, Size):
    Count = 0
    Total = 0
    for Position in range(Size):
        if Flags[Position]:
            Count += 1
            Total += Position + 1
    return Count, Total

def Product(Left, Right, Output, Size):
    for Row in range(Size):
        for Inner in range(Size - 1, -1, -1):
            Factor = Left[Row][Inner]
            for Column in range(Size):
                Output[Row][Column] += Factor * Right[Inner][Column]
    return Output

def Scatter(Indices, Values, Size):
    for Position in range(Size):
        Values[Indices[Position]] = 0
    return Values

def Hypercube(Source, Output, Size):
    for A in range(Size):
        for B in range(3):
            for C in range(4):
                for D in range(2):
                    Value = Source[A][B][C][D] * 0.25
                    Output[A][B][C][D] = math.sin(Value) + 0.125
    return Output
