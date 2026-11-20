import math
import random
# Test support/workload for exact scalar-power precision and exceptional arithmetic.
def Square(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Row in range(len(Source)):
        for Column in range(len(Source[Row])):
            Value = Source[Row][Column] / 3.0
            Output[Row][Column] = Value ** 2
    return Output

def Inverse(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Row in range(len(Source)):
        for Column in range(len(Source[Row])):
            Value = Source[Row][Column]
            Output[Row][Column] = Value ** -2 + Value ** 0 + Value ** 1
    return Output

def Transform(Value):
    Shifted = Value + 0.125
    return Shifted ** 3

def Helper(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Row in range(len(Source)):
        for Column in range(len(Source[Row])):
            Value = Source[Row][Column]
            Output[Row][Column] = Transform(Value) if Value < 1.0 else math.sin(Value) ** 2
    return Output

def Ordered(Source: 'numpy.ndarray'):
    Total = 0.0
    for Row in range(len(Source)):
        for Column in range(len(Source[Row])):
            Value = Source[Row][Column]
            Total += Value ** 3 if Value > 0.5 else (Value / 2.0) ** 2
    return Total, Row, Column, Value

def Random_Power(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Row in range(len(Source)):
        for Column in range(len(Source[Row])):
            Value = random.random() + Source[Row][Column]
            Output[Row][Column] = Value ** 3
    return Output
