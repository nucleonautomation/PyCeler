import numpy as np

def Fused_Maps(Input, Output_A, Output_B):
    for Index in range(len(Input)):
        Output_A[Index] = Input[Index] * 2
    for Index in range(len(Input)):
        Output_B[Index] = Input[Index] + 5
    return Output_B

def Invariant_Scale(Input, Output, Scale, Multiplier):
    for Index in range(len(Input)):
        Output[Index] = Input[Index] * (Scale * Multiplier)
    return Output

def Repeated_Scores(Input, Output_A, Output_B, Target):
    for Index in range(len(Input)):
        Output_A[Index] = (Input[Index] - Target) * (Input[Index] - Target)
        Output_B[Index] = abs(Input[Index] - Target)
    return Output_B

def Local_Values(Input, Output_A, Output_B):
    for Index in range(len(Input)):
        Difference = Input[Index] - 1
        Output_A[Index] = Difference * Difference
        Output_B[Index] = Difference + 2
    return Output_B

def Column_First(Input, Output):
    Height, Width = Input.shape
    for Column in range(Width):
        for Row in range(Height):
            Output[Row, Column] = Input[Row, Column] * 2
    return Output

def Temporary_Pipeline(Input, Output, Scale, Offset):
    Temporary = np.empty_like(Input)
    for Index in range(len(Input)):
        Temporary[Index] = Input[Index] * Scale
    for Index in range(len(Input)):
        Output[Index] = Temporary[Index] + Offset
    return Output

def Versioned_Reads(Input, Output_A, Output_B):
    for Index in range(len(Input)):
        Previous = Output_A[Index]
        Output_A[Index] = Input[Index] + 1
        Output_B[Index] = Previous + Output_A[Index]
    return Output_B

def Unsafe_Neighbor(Input, Output):
    for Index in range(1, len(Input)):
        Output[Index] = Input[Index - 1]
    return Output

def Implicit_Fusion(Input, Output_A, Output_B):
    for Index in range(len(Input)):
        Output_A[Index] = Input[Index] * 2
    for Index in range(len(Input)):
        Output_B[Index] = Input[Index] + 5

def Explicit_None(Input, Output, Scale, Multiplier):
    for Index in range(len(Input)):
        Output[Index] = Input[Index] * (Scale * Multiplier)
    return None
