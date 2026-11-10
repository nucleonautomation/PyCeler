def Modulo_Total(Count, Divisor):
    Total = 0
    for Index in range(Count):
        Total += (Index * Index + Index * 7) % Divisor
    return Total

def Signed_Total(Begin, Stop, Offset):
    Total = 7
    for Index in range(Begin, Stop, 3):
        Total += Index - Offset
    return Total

def Reverse_Total(Begin, Stop, Divisor):
    Total = 0
    for Index in range(Begin, Stop, -2):
        Total += Index // Divisor
    return Total

def Constant_Total(Count, Value):
    Total = 0
    for Index in range(Count):
        Total += Value
    return Total

def Modulo_Constant(Count, Value, Divisor):
    Total = 0
    for Index in range(Count):
        Total += Value % Divisor
    return Total

def Floor_Constant(Count, Value, Divisor):
    Total = 0
    for Index in range(Count):
        Total += Value // Divisor
    return Total

def Intermediate_Overflow(Count, Value):
    Total = 0
    for Index in range(Count):
        Total += (Value * Value) % 7
    return Total

def Bounds_Division(Count, Divisor):
    Total = 0
    for Index in range(Count // Divisor):
        Total += Index
    return Total

def Ordered_Float(Count):
    Total = 0
    for Index in range(Count):
        Total += Index / 7
    return Total

def Dependent_Total(Count):
    Total = 0
    for Index in range(Count):
        Total += Total + Index
    return Total

def Rebound_Index(Index):
    Total = 0
    for Index in range(Index):
        Total += Index
    return Total

def Workloads():
    for Count in (8, 4096, 262144):
        yield {"Args": (Count, 999983), "Label": str(Count)}
    yield {"Args": (131072, -999983), "Label": "negative holdout", "Holdout": True}
