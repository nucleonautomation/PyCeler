import math
from math import copysign as Copy_Sign
from math import fmod as Float_Remainder

def Map_Copysign(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.copysign(Left[Index], Right[Index])
    return Output

def Map_Fmod(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.fmod(Left[Index], Right[Index])
    return Output

def Aliased(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = Copy_Sign(Float_Remainder(Left[Index], Right[Index]), Right[Index])
    return Output

def Composed(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.copysign(math.fmod(math.sin(Left[Index]), math.exp(Right[Index])), math.cos(Right[Index]))
    return Output

def Ordered_Arguments(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.fmod(math.sqrt(Left[Index]), math.log(Right[Index]))
    return Output

def Nested_Zero(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.fmod(Left[Index], math.sin(Right[Index]))
    return Output

def Integer_Zero_Sign(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.copysign(math.fmod(Left[Index], Right[Index]), -0)
    return Output

def Float_Negative_Zero_Sign(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.copysign(math.fmod(Left[Index], Right[Index]), -0.0)
    return Output

def Boolean_Zero_Sign(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.copysign(math.fmod(Left[Index], Right[Index]), -math.isinf(Right[Index]))
    return Output

def Same_Input(Left, Output):
    for Index in range(len(Left)):
        Output[Index] = math.copysign(Left[Index], Left[Index])
    return Output

def Deferred_Atan2(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.atan2(Left[Index], Right[Index])
    return Output

def Deferred_Pow(Left, Right, Output):
    for Index in range(len(Left)):
        Output[Index] = math.pow(Left[Index], Right[Index])
    return Output

def Deferred_Degrees(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.degrees(Source[Index])
    return Output

def Deferred_Radians(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = math.radians(Source[Index])
    return Output
