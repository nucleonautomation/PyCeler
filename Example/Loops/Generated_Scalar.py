# Focused generated scalar workload; ordinary Python inputs include supported and retained cases.
def Sum_0(Count, Value, Divisor):
    Total = 7
    for Index in range(Count):
        Total += ((((-3) - 1) % 7) - ((1 - (-3)) // (Index - 3)))
    return Total

def Sum_1(Count, Value, Divisor):
    Total = 1
    for Index in range(-Count, Count, 2):
        Total += (((Value - Value) % (-7)) - Index)
    return Total

def Sum_2(Count, Value, Divisor):
    Total = 7
    for Index in range(Count, -Count, -3):
        Total += (-Value)
    return Total

def Sum_3(Count, Value, Divisor):
    Total = 1
    for Index in range(Count):
        Total += (((7 % Divisor) + (Index + 1)) - ((Index - Value) - (-3)))
    return Total

def Sum_4(Count, Value, Divisor):
    Total = 0
    for Index in range(-Count, Count, 2):
        Total += (-((7 - 7) + (Value % (Index - 3))))
    return Total

def Sum_5(Count, Value, Divisor):
    Total = 1
    for Index in range(Count, -Count, -3):
        Total += (-((Index * Index) % Divisor))
    return Total

def Sum_6(Count, Value, Divisor):
    Total = 0
    for Index in range(Count):
        Total += Value
    return Total

def Sum_7(Count, Value, Divisor):
    Total = 7
    for Index in range(-Count, Count, 2):
        Total += (-Value)
    return Total

def Sum_8(Count, Value, Divisor):
    Total = 0
    for Index in range(Count, -Count, -3):
        Total += (((Value - Value) + (Index % (Index - 3))) // Divisor)
    return Total

def Sum_9(Count, Value, Divisor):
    Total = 1
    for Index in range(Count):
        Total += (-3)
    return Total

def Sum_10(Count, Value, Divisor):
    Total = 1
    for Index in range(-Count, Count, 2):
        Total += ((-7) - ((Value + Value) - (-(-3))))
    return Total

def Sum_11(Count, Value, Divisor):
    Total = 1
    for Index in range(Count, -Count, -3):
        Total += ((-(Index // 7)) - (-3))
    return Total

def Sum_12(Count, Value, Divisor):
    Total = 1
    for Index in range(Count):
        Total += 1
    return Total

def Sum_13(Count, Value, Divisor):
    Total = 0
    for Index in range(-Count, Count, 2):
        Total += (((Index // 7) - (Value % (-7))) // Divisor)
    return Total

def Sum_14(Count, Value, Divisor):
    Total = 7
    for Index in range(Count, -Count, -3):
        Total += (((Index - 7) * (Index % (Index - 3))) - ((Index + Index) * (Value % (-7))))
    return Total

def Sum_15(Count, Value, Divisor):
    Total = 1
    for Index in range(Count):
        Total += 7
    return Total

def Sum_16(Count, Value, Divisor):
    Total = 1
    for Index in range(-Count, Count, 2):
        Total += (-((7 - Value) % Divisor))
    return Total

def Sum_17(Count, Value, Divisor):
    Total = 7
    for Index in range(Count, -Count, -3):
        Total += ((-((-3) // 7)) % (Index - 3))
    return Total

def Sum_18(Count, Value, Divisor):
    Total = 7
    for Index in range(Count):
        Total += ((-(Index * Index)) % (Index - 3))
    return Total

def Sum_19(Count, Value, Divisor):
    Total = 1
    for Index in range(-Count, Count, 2):
        Total += ((-(Index - (-3))) * Index)
    return Total

def Sum_20(Count, Value, Divisor):
    Total = 1
    for Index in range(Count, -Count, -3):
        Total += (7 - (((-3) // 7) % (-7)))
    return Total

def Sum_21(Count, Value, Divisor):
    Total = 7
    for Index in range(Count):
        Total += (-3)
    return Total

def Sum_22(Count, Value, Divisor):
    Total = 0
    for Index in range(-Count, Count, 2):
        Total += (((Value - 1) // 7) % (-7))
    return Total

def Sum_23(Count, Value, Divisor):
    Total = 7
    for Index in range(Count, -Count, -3):
        Total += Value
    return Total

def Ordered_0(Count, Value, Divisor):
    Total = 0
    Index = 0
    while Index < Count:
        Index += 1
        if Index % 3 == 0:
            continue
        Total += ((-Value) * (((-3) * 7) * (-Index)))
        if Index > 17:
            break
    return Total

def Ordered_1(Count, Value, Divisor):
    Total = Value + 0
    for Index in range(-Count, Count, 2):
        Scratch = (-((1 % (Index - 3)) // 7))
        if Index % 2 == 0:
            Total += Scratch
        else:
            Total -= Scratch
    return Total

def Ordered_2(Count, Value, Divisor):
    Total = 0
    Index = 0
    while Index < Count:
        Index += 1
        if Index % 3 == 0:
            continue
        Total += (((7 % (-7)) * (-Value)) * (-(7 + Value)))
        if Index > 17:
            break
    return Total

def Ordered_3(Count, Value, Divisor):
    Total = Value + 0
    for Index in range(Count):
        Scratch = (-(7 // Divisor))
        if Index % 2 == 0:
            Total += Scratch
        else:
            Total -= Scratch
    return Total

def Ordered_4(Count, Value, Divisor):
    Total = 0
    Index = 0
    while Index < Count:
        Index += 1
        if Index % 3 == 0:
            continue
        Total += (((7 * Value) + Index) * 7)
        if Index > 17:
            break
    return Total

def Ordered_5(Count, Value, Divisor):
    Total = Value + 0
    for Index in range(Count, -Count, -3):
        Scratch = ((-(-(-3))) * ((Value - (-3)) * 1))
        if Index % 2 == 0:
            Total += Scratch
        else:
            Total -= Scratch
    return Total

def Ordered_6(Count, Value, Divisor):
    Total = 0
    Index = 0
    while Index < Count:
        Index += 1
        if Index % 3 == 0:
            continue
        Total += (((1 + (-3)) - (-(-3))) % 7)
        if Index > 17:
            break
    return Total

def Ordered_7(Count, Value, Divisor):
    Total = Value + 0
    for Index in range(-Count, Count, 2):
        Scratch = Index
        if Index % 2 == 0:
            Total += Scratch
        else:
            Total -= Scratch
    return Total

def Ordered_8(Count, Value, Divisor):
    Total = 0
    Index = 0
    while Index < Count:
        Index += 1
        if Index % 3 == 0:
            continue
        Total += (-3)
        if Index > 17:
            break
    return Total

def Ordered_9(Count, Value, Divisor):
    Total = Value + 0
    for Index in range(Count):
        Scratch = Value
        if Index % 2 == 0:
            Total += Scratch
        else:
            Total -= Scratch
    return Total

def Ordered_10(Count, Value, Divisor):
    Total = 0
    Index = 0
    while Index < Count:
        Index += 1
        if Index % 3 == 0:
            continue
        Total += (((1 // 7) * (-Index)) + (-(Value - 1)))
        if Index > 17:
            break
    return Total

def Ordered_11(Count, Value, Divisor):
    Total = Value + 0
    for Index in range(Count, -Count, -3):
        Scratch = (Value // (Index - 3))
        if Index % 2 == 0:
            Total += Scratch
        else:
            Total -= Scratch
    return Total

def Aliases_0(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result %= Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_1(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result = Index % Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_2(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result %= Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_3(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result = Value % Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_4(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result %= Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_5(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result = Value % Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_6(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result %= Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_7(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result = Index % Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_8(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result %= Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_9(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result = Index % Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_10(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result %= Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Aliases_11(Count, Value, Divisor):
    Result = Value
    Copy = Result
    Index = -1
    for Index in range(Count):
        Result = (Value + Index) % Divisor
        Copy = Result
    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index

def Callback_0(Count, Value, Divisor, Events):
    Total = Value + 0
    for Index in range(Count):
        Total += (-(-Index))
        if Index % 5 == 0 and Index != 0:
            Events.append((Index, Total))
    return Total, Events

def Callback_1(Count, Value, Divisor, Events):
    Total = Value + 0
    for Index in range(Count):
        Total += (-(Value + Value))
        if Index % 7 == 0 and Index != 0:
            Events.append((Index, Total))
    return Total, Events

def Callback_2(Count, Value, Divisor, Events):
    Total = Value + 0
    for Index in range(Count):
        Total += (-7)
        if Index % 5 == 0 and Index != 0:
            Events.append((Index, Total))
    return Total, Events

def Callback_3(Count, Value, Divisor, Events):
    Total = Value + 0
    for Index in range(Count):
        Total += ((-Index) + (7 * Value))
        if Index % 7 == 0 and Index != 0:
            Events.append((Index, Total))
    return Total, Events

def Callback_4(Count, Value, Divisor, Events):
    Total = Value + 0
    for Index in range(Count):
        Total += (-(Value // (Index - 3)))
        if Index % 7 == 0 and Index != 0:
            Events.append((Index, Total))
    return Total, Events

def Callback_5(Count, Value, Divisor, Events):
    Total = Value + 0
    for Index in range(Count):
        Total += (((-3) * Value) % (-7))
        if Index % 5 == 0 and Index != 0:
            Events.append((Index, Total))
    return Total, Events
