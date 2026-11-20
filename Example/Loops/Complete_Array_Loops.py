# Focused complete array loops workload; ordinary Python inputs include supported and retained cases.
import math
# Test support/workload for complete output transactions and late errors.
def Interior(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Plane in range(1, len(Source) - 1):
        for Row in range(1, len(Source[Plane]) - 1):
            for Column in range(1, len(Source[Plane][Row]) - 1):
                Value = (Source[Plane][Row][Column] + Source[Plane - 1][Row][Column]) * 0.25
                Output[Plane][Row][Column] = math.sqrt(Value + 1.0)
    return Output

def Reverse(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Plane in range(len(Source) - 1, -1, -2):
        for Row in range(len(Source[Plane])):
            for Column in range(len(Source[Plane][Row])):
                Value = Source[Plane][Row][Column]
                if Value > 0.1:
                    Output[Plane][Row][Column] = math.sin(Value) * 0.25
    return Output

def Domain(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Plane in range(len(Source)):
        for Row in range(len(Source[Plane])):
            for Column in range(len(Source[Plane][Row])):
                Output[Plane][Row][Column] = math.sqrt(Source[Plane][Row][Column])
    return Output
