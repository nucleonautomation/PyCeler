import math
from math import erf as Error_Function, erfc as Complementary_Function

def Map_erf(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.erf(Source[Index])
    return Output

def Map_erfc(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.erfc(Source[Index])
    return Output

def Aliased_erf(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = Error_Function(Source[Index])
    return Output

def Aliased_erfc(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = Complementary_Function(Source[Index])
    return Output

def Composed(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.erf(Source[Index]) + math.erfc(Source[Index]) / 2.0
    return Output

def Nested(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.erfc(math.erf(Source[Index]))
    return Output

def Domain_erf(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.log(math.erf(Source[Index]))
    return Output

def Domain_erfc(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.log(math.erfc(Source[Index]))
    return Output

def Overflow_erfc(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.exp(math.erfc(Source[Index]) * 1000.0)
    return Output
