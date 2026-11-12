def Mixed(Begin, End, Stride, Initial, Events, Callback):
    Total = Initial
    Index = -23
    for Index in range(Begin, End, Stride):
        Total += (Index * Index + Index * Stride) % 999983
        if Index % 6 == 0:
            Events.append((Index, Total, Stride))
            Total, Stride = Callback(Index, Total, Stride)
    else:
        Events.append(("else", Total, Index, Stride))
    Events.append(("done", Total, Index, Stride))
    return Total, Index, Stride

def Control(Begin, End, Stride, Events, Callback):
    Total = 0
    Index = -23
    for Index in range(Begin, End, Stride):
        Total += Index * Index
        if Index % 6 == 0:
            Events.append((Index, Total))
            Total = Callback(Index, Total)
            if Total == -777:
                break
            if Total == -888:
                continue
            Index = -99
    Events.append(("done", Total, Index))
    return Total, Index

def Fraction(Begin, End, Stride, Events):
    Total = 0.0
    Index = -23
    for Index in range(Begin, End, Stride):
        Total += (Index * Index + 7 * Index) / 999983
        if Index % 6 == 0:
            Events.append((Index, Total))
    else:
        Events.append(("else", Total, Index))
    return Total, Index

def Header(Begin, End, Stride, Events):
    Total = 0
    Index = -23
    for Index in range(Begin, End, Stride):
        Total += Index * 7
    else:
        Events.append(("else", Total, Index))
    return Total, Index

def Unbound(Begin, End, Stride, Events):
    Total = 0
    for Index in range(Begin, End, Stride):
        Total += Index * 7
    Events.append(Index)
    return Total, Index

def Partial(Begin, End, Stride, Divisor, Events):
    Total = 0
    Count = 0
    for Index in range(Begin, End, Stride):
        Count += 1
        Total += 20 // (Divisor - Index)
        if Index % 6 == 0:
            Events.append((Index, Total, Count))
    else:
        Events.append(("else", Total, Count))
    return Total, Count

Module_Results = []
for Begin, End, Stride in ((-19, 40, 3), (19, -40, -4), (3, 3, 7), (1, 10, 2**70), (1, -10, -(2**70))):
    Module_Events = []
    Total = 0
    Index = -23
    for Index in range(Begin, End, Stride):
        Total += (Index * Index + Index * Stride) % 999983
        if Index % 6 == 0:
            Module_Events.append((Index, Total, Stride))
            Stride = -Stride
    else:
        Module_Events.append(("else", Total, Index, Stride))
    Module_Results.append((Total, Index, Stride, tuple(Module_Events)))
