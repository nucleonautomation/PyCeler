import math

def Math_Chain(Source, Output):
    for Index in range(len(Source)):
        Wave = math.sin(Source[Index])
        Phase = math.cos(Source[Index])
        Energy = Wave * Wave + Phase * Phase
        Output[Index] = math.sqrt(Energy) + math.log1p(math.fabs(Wave))
    return Output

def Math_Ordered(Source, Output):
    for Index in range(len(Source)):
        Required = math.log(Source[Index])
        Wave = math.sin(Source[Index])
        Wave = Wave + math.cos(Source[Index])
        Output[Index] = Wave
    return Output

def Math_Branch(Source, Output):
    for Index in range(len(Source)):
        Wave = math.sin(Source[Index])
        if Wave < 0.0:
            Part = math.sqrt(-Wave)
        else:
            Part = math.log1p(Wave)
        Output[Index] = Part + math.cos(Source[Index])
    return Output

def Math_Conditional(Source, Output):
    for Index in range(len(Source)):
        Wave = math.sin(Source[Index])
        Output[Index] = math.sqrt(-Wave) if Wave < 0.0 else math.log1p(Wave)
    return Output

def Math_Nested(Source, Output):
    for Row in range(Source.shape[0]):
        for Column in range(Source.shape[1]):
            Wave = math.sin(Source[Row, Column])
            Phase = math.cos(Source[Row, Column])
            Energy = Wave * Wave + Phase * Phase
            Output[Row, Column] = math.sqrt(Energy) + math.log1p(math.fabs(Wave))
    return Output

def Math_Branch_Output(Source, Output):
    for Index in range(len(Source)):
        Wave = math.sin(Source[Index])
        if Wave < 0.0:
            Output[Index] = math.sqrt(-Wave)
        else:
            Output[Index] = math.log1p(Wave)
    return Output

def Math_Logical(Source, Output):
    for Index in range(len(Source)):
        Wave = math.sin(Source[Index])
        if Wave > 0.0 and math.log(Wave) > -2.0:
            Output[Index] = math.sqrt(Wave)
        else:
            Output[Index] = math.cos(Source[Index])
    return Output

def Math_Nested_Branch(Source, Output):
    for Row in range(Source.shape[0]):
        for Column in range(Source.shape[1]):
            Wave = math.sin(Source[Row, Column])
            if Wave < 0.0:
                Part = math.sqrt(-Wave)
            else:
                Part = math.log1p(Wave)
            Output[Row, Column] = Part + math.cos(Source[Row, Column])
    return Output

def Array_Nested(Source, Output):
    for Row in range(Source.shape[0]):
        for Column in range(Source.shape[1]):
            Value = Source[Row, Column] * 2
            Other = Value + Source[Row, Column]
            if Other > 9:
                Value = Other - 3
            else:
                Value = Other + 5
            Output[Row, Column] = Value * 2
    return Output

def Array_Volume(Source, Output):
    for Depth in range(Source.shape[0]):
        for Row in range(Source.shape[1]):
            for Column in range(Source.shape[2]):
                Value = Source[Depth, Row, Column] * 2
                Other = Value + Source[Depth, Row, Column]
                Output[Depth, Row, Column] = Other - 3 if Other > 9 else Other + 5
    return Output

def Math_Volume(Source, Output):
    for Depth in range(Source.shape[0]):
        for Row in range(Source.shape[1]):
            for Column in range(Source.shape[2]):
                Wave = math.sin(Source[Depth, Row, Column])
                Phase = math.cos(Source[Depth, Row, Column])
                Energy = Wave * Wave + Phase * Phase
                Output[Depth, Row, Column] = math.sqrt(Energy) + math.log1p(math.fabs(Wave))
    return Output
