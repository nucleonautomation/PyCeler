import math
import math as Trig
from math import sin, cos
# Test support/workload for scalar math call boundaries and observer behavior.
def Recurrence(Count, X, Y, Value):
    K = -1
    A = B = 0.0
    for K in range(Count):
        A = math.sin(X + K * 0.0001)
        B = math.cos(Y - K * 0.0002)
        X = A * 0.7 + B * 0.3
        Y = B * 0.6 - A * 0.4
        Value += X * X + Y * Y
    return X, Y, Value, A, B, K

def Aliases(Count, X, Y, Value):
    K = -1
    A = B = 0.0
    for K in range(Count):
        A = Trig.sin(X + K * 0.0001)
        B = cos(Y - K * 0.0002)
        X = A * 0.7 + B * 0.3
        Y = B * 0.6 - A * 0.4
        Value += X * X + Y * Y
    return X, Y, Value, A, B, K

def Branches(Count, X, Y, Value):
    K = -1
    A = B = 0.0
    for K in range(Count):
        A = math.sin(X + K * 0.001)
        if A > 0.0 and (Y < 2.0 or math.log(Y) > 0.0):
            B = math.sqrt(A)
        else:
            B = math.cos(Y)
        X = A * 0.7 + B * 0.3
        Y = math.sin(Y) if Y < 0.0 else math.cos(Y)
        Value += X * X + Y * Y
    return X, Y, Value, A, B, K

def Descending(Count, X, Y, Value):
    K = -1
    A = B = 0.0
    for K in range(Count, 0, -3):
        A = sin(X + K * 0.0001)
        B = cos(Y - K * 0.0002)
        X = A * 0.7 + B * 0.3
        Y = B * 0.6 - A * 0.4
        Value += X * X + Y * Y
    return X, Y, Value, A, B, K

def Domain(Count, X, Y, Value):
    K = -1
    A = B = 0.0
    for K in range(Count):
        X -= 0.125
        A = math.sqrt(X)
        B = math.exp(Y)
        Value += A / B
    return X, Y, Value, A, B, K

def Global_Domain(Count, First):
    global State, Total, Last, Part
    State = First
    Total = 0.0
    Last = -1
    Part = -17.0
    for Last in range(Count):
        State -= 0.125
        Part = math.sqrt(State)
        Total += Part * 0.25
    return State, Total, Last, Part

def Nested(Count, X, Y, Value):
    K = -1
    A = B = 0.0
    for Row in range(3):
        for K in range(Count):
            A = math.sin(X + K * 0.0001)
            B = math.cos(Y - K * 0.0002)
            X = A * 0.7 + B * 0.3
            Y = B * 0.6 - A * 0.4
            Value += X * X + Y * Y
    return X, Y, Value, A, B, K

Module_X = 0.2
Module_Y = 0.4
Module_Value = 0.0
for Module_K in range(80):
    Module_A = math.sin(Module_X + Module_K * 0.0001)
    Module_B = math.cos(Module_Y - Module_K * 0.0002)
    Module_X = Module_A * 0.7 + Module_B * 0.3
    Module_Y = Module_B * 0.6 - Module_A * 0.4
    Module_Value += Module_X * Module_X + Module_Y * Module_Y
Module_Result = Module_X, Module_Y, Module_Value, Module_A, Module_B, Module_K

Events = []

class Guard_Meta(type):
    def __eq__(self, Other):
        Events.append("unexpected type comparison")
        return False

class Sentinel(metaclass=Guard_Meta):
    def __del__(self):
        Events.append(Observed)

def Destruction(Count, X):
    global Observed, Temporary, Position, Operand
    Observed = 0.0
    Operand = X
    Events.clear()
    Temporary = Sentinel()
    for Position in range(Count):
        Temporary = math.sin(Operand)
        Observed += Temporary * 0.25
    return Observed, Events[:]

def Local_Destruction(Count, X):
    Temporary = Sentinel()
    Position = -1
    for Position in range(Count):
        Temporary = math.sin(X)
        X += Temporary * 0.25
    return X, Position
