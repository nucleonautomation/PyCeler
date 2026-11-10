import numpy as np

raise RuntimeError("Ranking must inspect source without executing it")

def Small(Values):
    for Index in range(4):
        Values[Index] = Values[Index] * 2

def Large(Values):
    for Index in range(4096):
        Values[Index] = Values[Index] * 2

def Empty(Values):
    for Index in range(0):
        Values[Index] = 1

def Native_Calls(Values):
    for Index in range(4096):
        np.add(Values, Values)

def Dynamic(Values, Count):
    for Index in range(Count):
        Values[Index] = Values[Index] * 2

def Nested(Values):
    for Row in range(8):
        for Column in range(8):
            Values[Row, Column] = 0

def Early_Exit(Values):
    for Index in range(4096):
        if Values[Index] == 0:
            break

def Shadowed(Values, range):
    for Index in range(4096):
        Values[Index] = 0

def Reverse(Values):
    for Index in range(9, -1, -2):
        Values[Index] = 0
