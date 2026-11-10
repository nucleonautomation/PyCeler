def Copy_Grid(Source, Output):
    Rows = Source.shape[0]
    for Row in range(Rows):
        for Column in range(len(Source[Row])):
            Output[Row, Column] = Source[Row, Column]
    return Output

def Threshold_Grid(Source, Output, Level=4):
    Rows, Columns = Output.shape
    for Row in range(Rows):
        for Column in range(Columns):
            if Source[Row, Column] >= Level:
                Output[Row, Column] = 1
            else:
                Output[Row, Column] = 0
    return Output

def Clip_Negative(Values):
    for Index in range(len(Values)):
        if Values[Index] < 0:
            Values[Index] = 0
    return Values

def Blend(Left, Right, Output, Factor):
    for Index in range(len(Output)):
        Output[Index] = Left[Index] * Factor + Right[Index]
    return Output

def Add_In_Place(Values, Step=1):
    for Index in range(Values.shape[0]):
        Values[Index] += Step
    return Values

def Fill_Grid(Output, Value):
    for Row in range(len(Output)):
        for Column in range(Output.shape[1]):
            Output[Row, Column] = Value
    return Output

def Select(Left, Right, Output):
    for Index in range(len(Output)):
        Output[Index] = Left[Index] if Left[Index] < Right[Index] else Right[Index]
    return Output

def Difference(Left, Right, Output):
    Count = len(Output)
    for Index in range(Count):
        Output[Index] = Left[Index] - Right[Index]
    return Output

def Scale(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = Source[Index] * 0.5
    return Output

def Transpose_Into(Source, Output):
    for Row in range(Output.shape[0]):
        for Column in range(Output.shape[1]):
            Output[Row, Column] = Source[Column, Row]
    return Output

def Shared_Write(Source, Output):
    for Index in range(len(Source)):
        Output[0] = Source[Index]
    return Output
