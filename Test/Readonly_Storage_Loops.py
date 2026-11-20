import math
# Test support/workload for shared read-only storage and selection holdouts.
def Flat(First, Second, Output):
    for Index in range(len(First)):
        Output[Index] = math.sin(First[Index]) + math.cos(Second[Index])
    return Output

def Flat_Region(First, Second, Output):
    Marker = 0
    for Index in range(len(First)):
        Output[Index] = math.sin(First[Index]) + math.cos(Second[Index])
    return Output

def Array_Region(First: 'numpy.ndarray', Second: 'numpy.ndarray', Output: 'numpy.ndarray'):
    Marker = 0
    for Index in range(len(First)):
        Output[Index] = math.sin(First[Index]) + math.cos(Second[Index])
    return Output

def Rows(Source, Output):
    for Row in range(len(Source)):
        for Column in range(len(Source[Row])):
            Output[Row][Column] = math.sin(Source[Row][Column]) + math.cos(Source[Row][Column])
    return Output

def Array_Rows(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Row in range(len(Source)):
        for Column in range(len(Source[Row])):
            Output[Row][Column] = math.sin(Source[Row][Column]) + math.cos(Source[Row][Column])
    return Output

def Shifted_Rows(Source, Output, Shift):
    for Row in range(len(Source)):
        for Column in range(len(Source[Row + Shift])):
            Output[Row][Column] = math.sin(Source[Row + Shift][Column])
    return Output

def Volume(Source, Output):
    for Layer in range(len(Source)):
        for Row in range(len(Source[Layer])):
            for Column in range(len(Source[Layer][Row])):
                Output[Layer][Row][Column] = math.sin(Source[Layer][Row][Column])
    return Output

def Length_Identity(Source, Output, Other):
    for Row in range(len(Source)):
        Width = len(Source[Row])
        for Column in range(Width):
            Value = math.sin(Source[Row][Column])
            Output[Row][Column] = Width
            Other[Row][Column] = Width
    return Output

def Checked_Length(Source, Output, Row, Column):
    for Index in range(len(Output)):
        Value = math.sin(Source[0][0][0])
        Output[Index] = len(Source[Row][Column])
    return Output
