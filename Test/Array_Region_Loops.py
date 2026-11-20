import math
import numpy as np
# Test support/workload for ndarray ranks, scalar promotion and ordered region execution.
def Stencil(Source, Velocity, Rows, Columns):
    for Row in range(1, Rows - 1):
        for Column in range(1, Columns - 1):
            Center = Source[Row, Column]
            Delta = Source[Row - 1, Column] + Source[Row + 1, Column] + Source[Row, Column - 1] + Source[Row, Column + 1] - 4.0 * Center
            Velocity[Row, Column] += Delta * 0.001
            if Velocity[Row, Column] > 1.0:
                Velocity[Row, Column] *= 0.5
            elif Velocity[Row, Column] < -1.0:
                Velocity[Row, Column] *= 0.5
    return Velocity

def Volume_Four(Source, Output):
    for A in range(Source.shape[0]):
        for B in range(Source.shape[1]):
            for C in range(Source.shape[2]):
                for D in range(Source.shape[3]):
                    Value = Source[A, B, C, D] * 0.125 + 0.05
                    Output[A, B, C, D] = math.sin(Value)
    return Output

def Row_Sum(Points, Total):
    for Index in range(len(Points)):
        X, Y, Z = Points[Index]
        Value = X * X + Y * Y + Z * Z
        if Value > 1.0:
            Total += math.sqrt(Value)
        else:
            Total += Value * 0.5
    return Total

def Strided(Source, Output, Start, Stop, Step):
    for Row in range(Start, Stop, Step):
        for Column in range(Source.shape[1]):
            Value = Source[Row, Column] * 2.0
            Output[Row, Column] = Value + 1.0
    return Output

def Neighbor_Recurrence(Output):
    for Row in range(1, Output.shape[0]):
        for Column in range(Output.shape[1]):
            Output[Row, Column] = Output[Row - 1, Column] * 0.5 + Output[Row, Column]
    return Output

def Cast_Outputs(Source, Integer, Floating):
    for Row in range(Source.shape[0]):
        for Column in range(Source.shape[1]):
            Integer[Row, Column] = Source[Row, Column] * 2.0
            Floating[Row, Column] = math.sin(Source[Row, Column]) * 0.125
    return Integer, Floating

def Volume_Six(Source, Output):
    Scale = 0.125
    for A in range(Source.shape[0]):
        for B in range(Source.shape[1]):
            for C in range(Source.shape[2]):
                for D in range(Source.shape[3]):
                    for E in range(Source.shape[4]):
                        for F in range(Source.shape[5]):
                            Value = Source[A, B, C, D, E, F] * Scale
                            Output[A, B, C, D, E, F] = math.cos(Value)
    return Output

def Piecewise_Sum(Values: 'numpy.ndarray', Total):
    for Index in range(len(Values)):
        Value = Values[Index]
        if Value < 0.07:
            Total += Value * 1.5
        elif Value < 0.4:
            Total += math.sqrt(Value)
        else:
            Total += Value * 0.2
    return Total
