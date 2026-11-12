import math

def Integer_Zero(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * math.sin(-0)
    return Output

def Integer_Nonzero(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * math.sin(-1)
    return Output

def Boolean_Zero(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * -math.isinf(Source[Index])
    return Output

def Boolean_Nonzero(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * -math.isfinite(Source[Index])
    return Output

def Nested_Boolean_Zero(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * math.sin(-math.isinf(Source[Index]))
    return Output

def Positive_Boolean_Zero(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * +math.isinf(Source[Index])
    return Output

def Double_Integer_Negative(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * math.sin(-(-0))
    return Output

def Float_Negative_Zero(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * math.sin(-0.0)
    return Output

def Double_Boolean_Negative(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * -(-math.isinf(Source[Index]))
    return Output

def Float_Negative_Nonzero(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.sin(Source[Index]) * math.sin(-1.0)
    return Output
