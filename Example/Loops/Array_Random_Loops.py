# Focused array random loops workload; ordinary Python inputs include supported and retained cases.
import math
import random
# Test support/workload for random draw order and state preservation.
def Random_Image(Pixels, Depth, Rows, Columns, Phase):
    for Row in range(Rows):
        for Column in range(Columns):
            Wave = math.sin((Row + Column) * 0.03 + Phase * 0.2)
            Noise = random.random() * 4.0
            Pixels[Row, Column, 0] = int(max(0, min(255, 80.0 + Wave * 12.0 + Noise)))
            Pixels[Row, Column, 1] = int(max(0, min(255, 100.0 + Wave * 6.0)))
            Depth[Row, Column] = Wave * 0.25 + 1.5
    return Pixels, Depth

def Random_Pairs(Output, Rows, Columns):
    for Row in range(Rows):
        for Column in range(Columns):
            First = random.random()
            Second = random.random()
            Output[Row, Column] = First * 0.125 + Second
    return Output

def Random_Domain(Output, Rows, Columns, Offset):
    for Row in range(Rows):
        for Column in range(Columns):
            Noise = random.random()
            Output[Row, Column] = math.sqrt(Offset - Row - Column) + Noise
    return Output

def Random_Variable(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Index in range(len(Source)):
        Output[Index] = random.random() * 0.5 if Source[Index] < 0.0 else Source[Index] + 0.3
    return Output

def Random_Balanced(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Index in range(len(Source)):
        Output[Index] = random.random() * 0.5 if Source[Index] < 0.0 else random.random() + 0.3
    return Output

def Random_Condition(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Index in range(len(Source)):
        Output[Index] = random.random() * Source[Index] if random.random() < 0.4 else Source[Index] + 0.3
    return Output

def Random_Branch(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Index in range(len(Source)):
        if Source[Index] < 0.0:
            Value = random.random() * 0.5
        else:
            Value = random.random() + 0.3
        Output[Index] = Value
    return Output

def Random_Nested(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Index in range(len(Source)):
        Value = random.random() if Source[Index] < 0.0 else random.random() + random.random() if random.random() < 0.5 else 0.25
        Output[Index] = Value * 0.5 + Source[Index]
    return Output

def Random_Rows(Source, Output, Rows, Columns):
    for Row in range(Rows):
        for Column in range(Columns):
            Output[Row, Column] = random.random() if Source[Row, Column] < 0.0 else Source[Row, Column] + 0.3
    return Output

def Random_Branch_Error(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Index in range(len(Source)):
        Value = random.random() if Source[Index] < 0.0 else Source[Index]
        Output[Index] = Value + math.sqrt(19.5 - Index)
    return Output
