# Focused generalization regions workload; ordinary Python inputs include supported and retained cases.
import math
import numpy as np

def Nested(Source, Output, Other, N, Depth):
    for I in range(N):
        Value = 0.0
        for J in range(Depth):
            Value += math.sqrt(abs(Source[I] - J * 0.125) + 0.25)
        Copy = Value
        Output[I] = Value
        Other[I] = Copy
    return Output, Other

def Nested_While(Source, Output, Other, N, Depth):
    for I in range(N):
        Value = 0.0
        J = 0
        while J < Depth:
            Value += math.sqrt(abs(Source[I] - J * 0.125) + 0.25)
            J += 1
        Copy = Value
        Output[I] = Value
        Other[I] = Copy
    return Output, Other

def Repeated_Index(Source, Output, Other, N, Depth):
    for Step in range(Depth):
        for I in range(N):
            Value = 0.0
            for J in range(3):
                Value += math.sin(Source[I] + J)
            Output[I] = Value
        for I in range(N):
            Other[I] = Output[I] * 0.75
    return Output, Other

def Conditional_Constant(Source, Output, Other, N, Depth):
    for I in range(N):
        Value = Source[I] * 2.0
        if I < Depth:
            Value = 1.25 + 2.5
        Output[I] = Value
        Other[I] = Value
    return Output, Other

def Shared_Inner(Source, Output, Other, N, Depth):
    for I in range(N):
        Value = Source[I] * 2.0
        for J in range(Depth):
            Output[J] = Value
            Other[J] = Value
    return Output, Other

def Integer_Absolute(Source, Output, Other, N, Depth):
    for I in range(N):
        Value = abs(Source[I])
        Output[I] = Value + 1
        Other[I] = Value + 2
    return Output, Other

def Interleaved(Source, Output, Other, N, Depth):
    for I in range(N):
        Value = math.sqrt(abs(Source[I]) + 1.0)
        Output[2 * I] = Value
        Output[2 * I + 1] = Value
        Other[I] = Value
    return Output, Other

def Columns(Source: "numpy.ndarray", Output: "numpy.ndarray", Other: "numpy.ndarray", N, Depth):
    for I in range(N):
        for J in range(Depth):
            Output[J, I] = abs(Source[J, I]) * 0.5 + 0.125
    return Output, Other

def Dependent(Source, Output, Other, N, Depth):
    for I in range(1, N):
        Output[I] = Output[I - 1] * 0.75 + Source[I]
    return Output, Other

def Direct_Absolute(Source, Output, Other, N, Depth):
    for I in range(N):
        Output[I] = abs(Source[I])
    return Output, Other

def Conditional_Expression(Source, Output, Other, N, Depth):
    for I in range(N):
        Value = Source[I] * 2.0
        Value = 1.25 + 2.5 if I < Depth else 1.5 + 2.25
        Output[I] = Value
        Other[I] = Value
    return Output, Other

def Many_Slots_List(Source, Output, Other, N, Depth):
    for I in range(N):
        Value_0 = Source[I] * 0.75
        Value_1 = Value_0 + 0.001
        Value_2 = Value_1 + 0.001
        Value_3 = Value_2 + 0.001
        Value_4 = Value_3 + 0.001
        Value_5 = Value_4 + 0.001
        Value_6 = Value_5 + 0.001
        Value_7 = Value_6 + 0.001
        Value_8 = Value_7 + 0.001
        Value_9 = Value_8 + 0.001
        Value_10 = Value_9 + 0.001
        Value_11 = Value_10 + 0.001
        Value_12 = Value_11 + 0.001
        Value_13 = Value_12 + 0.001
        Value_14 = Value_13 + 0.001
        Value_15 = Value_14 + 0.001
        Value_16 = Value_15 + 0.001
        Value_17 = Value_16 + 0.001
        Value_18 = Value_17 + 0.001
        Value_19 = Value_18 + 0.001
        Value_20 = Value_19 + 0.001
        Value_21 = Value_20 + 0.001
        Value_22 = Value_21 + 0.001
        Value_23 = Value_22 + 0.001
        Value_24 = Value_23 + 0.001
        Value_25 = Value_24 + 0.001
        Value_26 = Value_25 + 0.001
        Value_27 = Value_26 + 0.001
        Value_28 = Value_27 + 0.001
        Value_29 = Value_28 + 0.001
        Value_30 = Value_29 + 0.001
        Value_31 = Value_30 + 0.001
        Value_32 = Value_31 + 0.001
        Value_33 = Value_32 + 0.001
        Value_34 = Value_33 + 0.001
        Value_35 = Value_34 + 0.001
        Value_36 = Value_35 + 0.001
        Value_37 = Value_36 + 0.001
        Value_38 = Value_37 + 0.001
        Value_39 = Value_38 + 0.001
        Value_40 = Value_39 + 0.001
        Value_41 = Value_40 + 0.001
        Value_42 = Value_41 + 0.001
        Value_43 = Value_42 + 0.001
        Value_44 = Value_43 + 0.001
        Value_45 = Value_44 + 0.001
        Value_46 = Value_45 + 0.001
        Value_47 = Value_46 + 0.001
        Value_48 = Value_47 + 0.001
        Value_49 = Value_48 + 0.001
        Value_50 = Value_49 + 0.001
        Value_51 = Value_50 + 0.001
        Value_52 = Value_51 + 0.001
        Value_53 = Value_52 + 0.001
        Value_54 = Value_53 + 0.001
        Value_55 = Value_54 + 0.001
        Value_56 = Value_55 + 0.001
        Value_57 = Value_56 + 0.001
        Value_58 = Value_57 + 0.001
        Value_59 = Value_58 + 0.001
        Value_60 = Value_59 + 0.001
        Value_61 = Value_60 + 0.001
        Value_62 = Value_61 + 0.001
        Value_63 = Value_62 + 0.001
        Value_64 = Value_63 + 0.001
        Value_65 = Value_64 + 0.001
        Value_66 = Value_65 + 0.001
        Value_67 = Value_66 + 0.001
        Value_68 = Value_67 + 0.001
        Value_69 = Value_68 + 0.001
        Value_70 = Value_69 + 0.001
        Value_71 = Value_70 + 0.001
        Output[I] = Value_71
    return Output, Other

def Many_Slots_Array(Source: "numpy.ndarray", Output: "numpy.ndarray", Other: "numpy.ndarray", N, Depth):
    for I in range(N):
        Value_0 = Source[I] * 0.75
        Value_1 = Value_0 + 0.001
        Value_2 = Value_1 + 0.001
        Value_3 = Value_2 + 0.001
        Value_4 = Value_3 + 0.001
        Value_5 = Value_4 + 0.001
        Value_6 = Value_5 + 0.001
        Value_7 = Value_6 + 0.001
        Value_8 = Value_7 + 0.001
        Value_9 = Value_8 + 0.001
        Value_10 = Value_9 + 0.001
        Value_11 = Value_10 + 0.001
        Value_12 = Value_11 + 0.001
        Value_13 = Value_12 + 0.001
        Value_14 = Value_13 + 0.001
        Value_15 = Value_14 + 0.001
        Value_16 = Value_15 + 0.001
        Value_17 = Value_16 + 0.001
        Value_18 = Value_17 + 0.001
        Value_19 = Value_18 + 0.001
        Value_20 = Value_19 + 0.001
        Value_21 = Value_20 + 0.001
        Value_22 = Value_21 + 0.001
        Value_23 = Value_22 + 0.001
        Value_24 = Value_23 + 0.001
        Value_25 = Value_24 + 0.001
        Value_26 = Value_25 + 0.001
        Value_27 = Value_26 + 0.001
        Value_28 = Value_27 + 0.001
        Value_29 = Value_28 + 0.001
        Value_30 = Value_29 + 0.001
        Value_31 = Value_30 + 0.001
        Value_32 = Value_31 + 0.001
        Value_33 = Value_32 + 0.001
        Value_34 = Value_33 + 0.001
        Value_35 = Value_34 + 0.001
        Value_36 = Value_35 + 0.001
        Value_37 = Value_36 + 0.001
        Value_38 = Value_37 + 0.001
        Value_39 = Value_38 + 0.001
        Value_40 = Value_39 + 0.001
        Value_41 = Value_40 + 0.001
        Value_42 = Value_41 + 0.001
        Value_43 = Value_42 + 0.001
        Value_44 = Value_43 + 0.001
        Value_45 = Value_44 + 0.001
        Value_46 = Value_45 + 0.001
        Value_47 = Value_46 + 0.001
        Value_48 = Value_47 + 0.001
        Value_49 = Value_48 + 0.001
        Value_50 = Value_49 + 0.001
        Value_51 = Value_50 + 0.001
        Value_52 = Value_51 + 0.001
        Value_53 = Value_52 + 0.001
        Value_54 = Value_53 + 0.001
        Value_55 = Value_54 + 0.001
        Value_56 = Value_55 + 0.001
        Value_57 = Value_56 + 0.001
        Value_58 = Value_57 + 0.001
        Value_59 = Value_58 + 0.001
        Value_60 = Value_59 + 0.001
        Value_61 = Value_60 + 0.001
        Value_62 = Value_61 + 0.001
        Value_63 = Value_62 + 0.001
        Value_64 = Value_63 + 0.001
        Value_65 = Value_64 + 0.001
        Value_66 = Value_65 + 0.001
        Value_67 = Value_66 + 0.001
        Value_68 = Value_67 + 0.001
        Value_69 = Value_68 + 0.001
        Value_70 = Value_69 + 0.001
        Value_71 = Value_70 + 0.001
        Output[I] = Value_71
    return Output, Other

def Many_Buffers(Input_0, Input_1, Input_2, Input_3, Input_4, Input_5, Input_6, Input_7, Input_8, Input_9, Input_10, Output, N):
    for I in range(N):
        Output[I] = Input_0[I] + Input_1[I] + Input_2[I] + Input_3[I] + Input_4[I] + Input_5[I] + Input_6[I] + Input_7[I] + Input_8[I] + Input_9[I] + Input_10[I]
    return Output
