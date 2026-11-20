def Weighted(Source, Output, Height, Width):
    for Row in range(1, Height - 1):
        for Column in range(1, Width - 1):
            Center = Source[Row][Column]
            Top = Source[Row - 1][Column]
            Bottom = Source[Row + 1][Column]
            Left = Source[Row][Column - 1]
            Right = Source[Row][Column + 1]
            Output[Row][Column] = Center * 0.5 + Top * 0.125 + Bottom * 0.125 + Left * 0.125 + Right * 0.125
    return Output
# Test support/workload for nested list updates and object identity.
def Diagonal(Source, Output, Height, Width):
    for Row in range(1, Height - 1):
        for Column in range(1, Width - 1):
            A = Source[Row - 1][Column - 1] + Source[Row + 1][Column + 1]
            B = Source[Row - 1][Column + 1] - Source[Row + 1][Column - 1]
            Output[Row][Column] = A * 0.3 + B * 0.7
    return Output

def Horizontal(Source, Output, Height, Width):
    for Row in range(1, Height - 1):
        for Column in range(1, Width - 1):
            Output[Row][Column] = (Source[Row][Column + 1] - Source[Row][Column - 1]) * 0.25
    return Output

def Vertical(Source, Output, Height, Width):
    for Row in range(1, Height - 1):
        for Column in range(1, Width - 1):
            Output[Row][Column] = (Source[Row + 1][Column] - Source[Row - 1][Column]) * 0.75
    return Output

def Conditional(Source, Output, Height, Width):
    for Row in range(1, Height - 1):
        for Column in range(1, Width - 1):
            A = Source[Row][Column]
            if A > 0.3:
                B = Source[Row - 1][Column] * 0.25
            else:
                B = Source[Row + 1][Column] * 0.75
            Output[Row][Column] = A + B
    return Output

def Indexed(Source, Output, Height, Width):
    for Row in range(1, Height - 1):
        for Column in range(1, Width - 1):
            Output[Row][Column] = Source[Row][Column] + Row * 0.001 - Column * 0.003
    return Output

def Quotient(Source, Output, Height, Width):
    for Row in range(1, Height - 1):
        for Column in range(1, Width - 1):
            Output[Row][Column] = Source[Row - 1][Column] / Source[Row][Column]
    return Output

def Aliases(Source, Output, Height, Width):
    Row = Column = -1
    Value = Shared = None
    for Row in range(1, Height - 1):
        for Column in range(1, Width - 1):
            Value = Source[Row][Column] * 0.5
            Shared = Value
            Output[Row][Column] = Shared
    return Output, Value, Shared, Row, Column

def Swap(Source, Output, Height, Width):
    for Step in range(5):
        for Row in range(1, Height - 1):
            for Column in range(1, Width - 1):
                Center = Source[Row][Column]
                Side = Source[Row][Column - 1] + Source[Row][Column + 1]
                Output[Row][Column] = Center * 0.5 + Side * 0.25
        Source, Output = Output, Source
    return Source

def Dimensions(Source, Output, Height, Width):
    for Row in range(1, len(Source) - 1):
        for Column in range(1, len(Source[0]) - 1):
            Output[Row][Column] = Source[Row][Column] * 0.7 + Source[Row - 1][Column] * 0.3
    return Output

def Two_Inputs(First, Second, Output, Height, Width):
    for Row in range(1, Height - 1):
        for Column in range(1, Width - 1):
            Output[Row][Column] = First[Row][Column] * 0.4 + Second[Row + 1][Column] * 0.6
    return Output
