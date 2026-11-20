# Focused random bound loops workload; ordinary Python inputs include supported and retained cases.
import math
import random
# Test support/workload for random bound.
def Pure_Body(Output: 'numpy.ndarray'):
    for Row in range(8):
        for Column in range(2 + int(random.random() * 6.0)):
            Output[Row, Column] = math.sin(Row * 0.125) + Column * 0.25
    return Output

def Random_Body(Output: 'numpy.ndarray'):
    for Row in range(8):
        for Column in range(2 + int(random.random() * 6.0)):
            Output[Row, Column] = math.sin(Row * 0.125) + random.random()
    return Output

def Heavy(Output: 'numpy.ndarray', Width):
    for Row in range(8):
        for Column in range(int(Width * (0.5 + random.random() * 0.5))):
            Value = (Column + Row) * 0.001
            for Repeat in range(24):
                Value = math.sin(Value + 0.1) + math.cos(Value - 0.1)
            Output[Row, Column] = Value
    return Output

def Ordered_Math(Output: 'numpy.ndarray', Width):
    for Row in range(8):
        for Column in range(Width):
            Value = (Column + Row) * 0.001
            for Repeat in range(24):
                Value = math.sin(Value + 0.1) + math.cos(Value - 0.1)
            Output[Row, Column] = Value
    return Output

def List_Math(Output, Width):
    for Row in range(8):
        for Column in range(Width):
            Value = (Column + Row) * 0.001
            for Repeat in range(24):
                Value = math.sin(Value + 0.1) + math.cos(Value - 0.1)
            Output[Row][Column] = Value
    return Output
