# Focused integer array loops workload; ordinary Python inputs include supported and retained cases.
import math
# Test support/workload for integer indexing, promotion, precision and overflow.
def Segments(Bounds, Keys, Weights, Source, Output):
    for Row in range(len(Bounds) - 1):
        First = Bounds[Row]
        Stop = Bounds[Row + 1]
        Total = 0.0
        for Cursor in range(First, Stop):
            Location = Keys[Cursor]
            Total += Source[Location] * Weights[Cursor]
        Output[Row] = Total
    return Output

def Nested(Bounds, Keys, Source, Output):
    for Row in range(len(Bounds) - 1):
        Total = 0.0
        Count = 0
        for Cursor in range(Bounds[Row], Bounds[Row + 1]):
            Location = Keys[Cursor]
            for Other in range(Bounds[Location], Bounds[Location + 1]):
                Position = Keys[Other]
                if Position == Row:
                    continue
                Difference = Source[Row] - Source[Position]
                Total += Difference * Difference
                Count += 1
        if Count > 0:
            Output[Row] = Total / Count
    return Output

def Arithmetic(Left, Right, Output):
    for Index in range(len(Left)):
        Sum = Left[Index] + Right[Index]
        Product = Left[Index] * Right[Index]
        Difference = Left[Index] - Right[Index]
        Ratio = Left[Index] / Right[Index]
        Output[Index, 0] = Sum
        Output[Index, 1] = Product
        Output[Index, 2] = Difference
        Output[Index, 3] = Ratio
    return Output, Sum, Product, Difference, Ratio

def Boolean_Add(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = Source[Index] + True
    return Output

def Prefix(Source, Output):
    for Index in range(len(Source)):
        Output[Index + 1] = Output[Index] + Source[Index]
    return Output

def Copy_Integer(Source, Output):
    for Index in range(len(Source)):
        Output[Index + 1] = Source[Index]
    return Output
