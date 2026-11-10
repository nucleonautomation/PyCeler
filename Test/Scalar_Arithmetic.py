def Modulo_Total(Count, Divisor):
    Total = 0
    for Index in range(Count):
        Total += (Index * Index + Index * 7) % Divisor
    return Total

def Floor_Total(Count, Left, Right):
    Total = 0
    for Index in range(Count):
        Total += (Left + Index) // Right
    return Total

def Remainder_Total(Count, Left, Right):
    Total = 0
    for Index in range(Count):
        Total += (Left + Index) % Right
    return Total

def Minimum_Remainder(Count):
    Total = 0
    for Index in range(Count):
        Total += -9223372036854775808 % -1
    return Total

def Division_Total(Count, Divisor):
    Total = 0
    for Index in range(Count):
        Total += (Index * Index + Index * 7) / Divisor
    return Total

def Wide_Division(Count, Left, Right):
    Total = 0
    for Index in range(Count):
        Total += (Left + Index) / Right
    return Total

def Mixed_Division(Count, Left, Right):
    Total = -0.0
    for Index in range(Count):
        Total += (Left + Index) / Right * 0.5 - 1.25
    return Total

def Negative_Zero(Count):
    Total = -0.0
    for Index in range(Count):
        Total += 0 / -1
    return Total

def Fractional_Divisor(Count):
    Total = 0
    for Index in range(Count):
        Total += Index / 0.25
    return Total

def Division_Overflow(Count, Left, Right):
    Total = 0
    for Index in range(Count):
        Total += (Left * Left + Index) / Right
    return Total
