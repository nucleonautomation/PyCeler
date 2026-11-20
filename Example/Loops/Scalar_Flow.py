# Focused scalar flow workload; ordinary Python inputs include supported and retained cases.
Module_Results = []
def Compute_Conditional_Direct_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Index in range(Begin, End, Stride):
        Value = Index + 11 if Index % 2 else Index * 3 + 5
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Conditional_For_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Outer in range(2):
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value = Index + 11 if Index % 2 else Index * 3 + 5
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Conditional_While_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value = Index + 11 if Index % 2 else Index * 3 + 5
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
        Outer += 1
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Conditional_Branch_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Index in range(Begin, Bound, Stride):
        Value = Index + 11 if Index % 2 else Index * 3 + 5
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

Begin = -3
End = 257
Stride = 2
Total = 7
Modulus = 999983
Value = -17
Other = -19
Index = -23
for Index in range(Begin, End, Stride):
    Value = Index + 11 if Index % 2 else Index * 3 + 5
    Total += Value
Module_Results.append((Total, Value, Other, Index))
def Compute_Tuple_Direct_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Index in range(Begin, End, Stride):
        Value, Other = (Index * Index + 5) % Modulus, Total % 101 + Index
        Total += Value + Other
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Tuple_For_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Outer in range(2):
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value, Other = (Index * Index + 5) % Modulus, Total % 101 + Index
            Total += Value + Other
        Events.append(('after', Outer, Total, Value, Other, Index))
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Tuple_While_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value, Other = (Index * Index + 5) % Modulus, Total % 101 + Index
            Total += Value + Other
        Events.append(('after', Outer, Total, Value, Other, Index))
        Outer += 1
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Tuple_Branch_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Index in range(Begin, Bound, Stride):
        Value, Other = (Index * Index + 5) % Modulus, Total % 101 + Index
        Total += Value + Other
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

Begin = -3
End = 257
Stride = 2
Total = 7
Modulus = 999983
Value = -17
Other = -19
Index = -23
for Index in range(Begin, End, Stride):
    Value, Other = (Index * Index + 5) % Modulus, Total % 101 + Index
    Total += Value + Other
Module_Results.append((Total, Value, Other, Index))
def Compute_Intermediate_Direct_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Index in range(Begin, End, Stride):
        Value = Index
        Value += 11
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Intermediate_For_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Outer in range(2):
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value = Index
            Value += 11
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Intermediate_While_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value = Index
            Value += 11
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
        Outer += 1
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Intermediate_Branch_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Index in range(Begin, Bound, Stride):
        Value = Index
        Value += 11
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

Begin = -3
End = 257
Stride = 2
Total = 7
Modulus = 999983
Value = -17
Other = -19
Index = -23
for Index in range(Begin, End, Stride):
    Value = Index
    Value += 11
    Total += Value
Module_Results.append((Total, Value, Other, Index))
def Compute_Cached_Direct_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Index in range(Begin, End, Stride):
        Value = 0
        if Index % 2:
            Value += Index + 1
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Cached_For_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Outer in range(2):
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value = 0
            if Index % 2:
                Value += Index + 1
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Cached_While_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value = 0
            if Index % 2:
                Value += Index + 1
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
        Outer += 1
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Cached_Branch_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Index in range(Begin, Bound, Stride):
        Value = 0
        if Index % 2:
            Value += Index + 1
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

Begin = -3
End = 257
Stride = 2
Total = 7
Modulus = 999983
Value = -17
Other = -19
Index = -23
for Index in range(Begin, End, Stride):
    Value = 0
    if Index % 2:
        Value += Index + 1
    Total += Value
Module_Results.append((Total, Value, Other, Index))
def Compute_Branches_Direct_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Index in range(Begin, End, Stride):
        if Index % 2:
            Value = (Index ^ 23) + 1
        else:
            Value = (Index * 3 + 5) % Modulus
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Branches_For_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Outer in range(2):
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            if Index % 2:
                Value = (Index ^ 23) + 1
            else:
                Value = (Index * 3 + 5) % Modulus
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Branches_While_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            if Index % 2:
                Value = (Index ^ 23) + 1
            else:
                Value = (Index * 3 + 5) % Modulus
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
        Outer += 1
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Branches_Branch_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Index in range(Begin, Bound, Stride):
        if Index % 2:
            Value = (Index ^ 23) + 1
        else:
            Value = (Index * 3 + 5) % Modulus
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

Begin = -3
End = 257
Stride = 2
Total = 7
Modulus = 999983
Value = -17
Other = -19
Index = -23
for Index in range(Begin, End, Stride):
    if Index % 2:
        Value = (Index ^ 23) + 1
    else:
        Value = (Index * 3 + 5) % Modulus
    Total += Value
Module_Results.append((Total, Value, Other, Index))
def Compute_Overwrite_Direct_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Index in range(Begin, End, Stride):
        Value = Total
        if Index % 2:
            Value = Index + 11
        else:
            Value = Total % 101 + 7
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Overwrite_For_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    for Outer in range(2):
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value = Total
            if Index % 2:
                Value = Index + 11
            else:
                Value = Total % 101 + 7
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Overwrite_While_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Total))
        for Index in range(Begin, End, Stride):
            Value = Total
            if Index % 2:
                Value = Index + 11
            else:
                Value = Total % 101 + 7
            Total += Value
        Events.append(('after', Outer, Total, Value, Other, Index))
        Outer += 1
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

def Compute_Overwrite_Branch_0(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Total = Initial
    Value = -17
    Other = -19
    Index = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Index in range(Begin, Bound, Stride):
        Value = Total
        if Index % 2:
            Value = Index + 11
        else:
            Value = Total % 101 + 7
        Total += Value
    Events.append(('done', Total))
    return Total, Value, Other, Index, Events

Begin = -3
End = 257
Stride = 2
Total = 7
Modulus = 999983
Value = -17
Other = -19
Index = -23
for Index in range(Begin, End, Stride):
    Value = Total
    if Index % 2:
        Value = Index + 11
    else:
        Value = Total % 101 + 7
    Total += Value
Module_Results.append((Total, Value, Other, Index))
def Compute_Conditional_Direct_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Cursor in range(Begin, End, Stride):
        Term = Cursor + 11 if Cursor % 2 else Cursor * 3 + 5
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Conditional_For_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Outer in range(2):
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term = Cursor + 11 if Cursor % 2 else Cursor * 3 + 5
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Conditional_While_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term = Cursor + 11 if Cursor % 2 else Cursor * 3 + 5
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
        Outer += 1
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Conditional_Branch_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Cursor in range(Begin, Bound, Stride):
        Term = Cursor + 11 if Cursor % 2 else Cursor * 3 + 5
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

Begin = -3
End = 257
Stride = 2
Accumulator = 7
Modulus = 999983
Term = -17
Scratch = -19
Cursor = -23
for Cursor in range(Begin, End, Stride):
    Term = Cursor + 11 if Cursor % 2 else Cursor * 3 + 5
    Accumulator += Term
Module_Results.append((Accumulator, Term, Scratch, Cursor))
def Compute_Tuple_Direct_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Cursor in range(Begin, End, Stride):
        Term, Scratch = ((Cursor * Cursor + 5) % Modulus, Accumulator % 101 + Cursor)
        Accumulator += Term + Scratch
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Tuple_For_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Outer in range(2):
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term, Scratch = ((Cursor * Cursor + 5) % Modulus, Accumulator % 101 + Cursor)
            Accumulator += Term + Scratch
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Tuple_While_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term, Scratch = ((Cursor * Cursor + 5) % Modulus, Accumulator % 101 + Cursor)
            Accumulator += Term + Scratch
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
        Outer += 1
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Tuple_Branch_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Cursor in range(Begin, Bound, Stride):
        Term, Scratch = ((Cursor * Cursor + 5) % Modulus, Accumulator % 101 + Cursor)
        Accumulator += Term + Scratch
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

Begin = -3
End = 257
Stride = 2
Accumulator = 7
Modulus = 999983
Term = -17
Scratch = -19
Cursor = -23
for Cursor in range(Begin, End, Stride):
    Term, Scratch = ((Cursor * Cursor + 5) % Modulus, Accumulator % 101 + Cursor)
    Accumulator += Term + Scratch
Module_Results.append((Accumulator, Term, Scratch, Cursor))
def Compute_Intermediate_Direct_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Cursor in range(Begin, End, Stride):
        Term = Cursor
        Term += 11
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Intermediate_For_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Outer in range(2):
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term = Cursor
            Term += 11
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Intermediate_While_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term = Cursor
            Term += 11
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
        Outer += 1
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Intermediate_Branch_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Cursor in range(Begin, Bound, Stride):
        Term = Cursor
        Term += 11
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

Begin = -3
End = 257
Stride = 2
Accumulator = 7
Modulus = 999983
Term = -17
Scratch = -19
Cursor = -23
for Cursor in range(Begin, End, Stride):
    Term = Cursor
    Term += 11
    Accumulator += Term
Module_Results.append((Accumulator, Term, Scratch, Cursor))
def Compute_Cached_Direct_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Cursor in range(Begin, End, Stride):
        Term = 0
        if Cursor % 2:
            Term += Cursor + 1
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Cached_For_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Outer in range(2):
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term = 0
            if Cursor % 2:
                Term += Cursor + 1
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Cached_While_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term = 0
            if Cursor % 2:
                Term += Cursor + 1
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
        Outer += 1
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Cached_Branch_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Cursor in range(Begin, Bound, Stride):
        Term = 0
        if Cursor % 2:
            Term += Cursor + 1
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

Begin = -3
End = 257
Stride = 2
Accumulator = 7
Modulus = 999983
Term = -17
Scratch = -19
Cursor = -23
for Cursor in range(Begin, End, Stride):
    Term = 0
    if Cursor % 2:
        Term += Cursor + 1
    Accumulator += Term
Module_Results.append((Accumulator, Term, Scratch, Cursor))
def Compute_Branches_Direct_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Cursor in range(Begin, End, Stride):
        if Cursor % 2:
            Term = (Cursor ^ 23) + 1
        else:
            Term = (Cursor * 3 + 5) % Modulus
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Branches_For_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Outer in range(2):
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            if Cursor % 2:
                Term = (Cursor ^ 23) + 1
            else:
                Term = (Cursor * 3 + 5) % Modulus
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Branches_While_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            if Cursor % 2:
                Term = (Cursor ^ 23) + 1
            else:
                Term = (Cursor * 3 + 5) % Modulus
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
        Outer += 1
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Branches_Branch_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Cursor in range(Begin, Bound, Stride):
        if Cursor % 2:
            Term = (Cursor ^ 23) + 1
        else:
            Term = (Cursor * 3 + 5) % Modulus
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

Begin = -3
End = 257
Stride = 2
Accumulator = 7
Modulus = 999983
Term = -17
Scratch = -19
Cursor = -23
for Cursor in range(Begin, End, Stride):
    if Cursor % 2:
        Term = (Cursor ^ 23) + 1
    else:
        Term = (Cursor * 3 + 5) % Modulus
    Accumulator += Term
Module_Results.append((Accumulator, Term, Scratch, Cursor))
def Compute_Overwrite_Direct_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Cursor in range(Begin, End, Stride):
        Term = Accumulator
        if Cursor % 2:
            Term = Cursor + 11
        else:
            Term = Accumulator % 101 + 7
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Overwrite_For_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    for Outer in range(2):
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term = Accumulator
            if Cursor % 2:
                Term = Cursor + 11
            else:
                Term = Accumulator % 101 + 7
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Overwrite_While_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    Outer = 0
    while Outer < 2:
        Events.append(('before', Outer, Accumulator))
        for Cursor in range(Begin, End, Stride):
            Term = Accumulator
            if Cursor % 2:
                Term = Cursor + 11
            else:
                Term = Accumulator % 101 + 7
            Accumulator += Term
        Events.append(('after', Outer, Accumulator, Term, Scratch, Cursor))
        Outer += 1
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

def Compute_Overwrite_Branch_1(Begin, End, Stride, Initial, Modulus, Flag):
    Events = []
    Accumulator = Initial
    Term = -17
    Scratch = -19
    Cursor = -23
    if Flag:
        Bound = End
    else:
        Bound = End + 0
    for Cursor in range(Begin, Bound, Stride):
        Term = Accumulator
        if Cursor % 2:
            Term = Cursor + 11
        else:
            Term = Accumulator % 101 + 7
        Accumulator += Term
    Events.append(('done', Accumulator))
    return (Accumulator, Term, Scratch, Cursor, Events)

Begin = -3
End = 257
Stride = 2
Accumulator = 7
Modulus = 999983
Term = -17
Scratch = -19
Cursor = -23
for Cursor in range(Begin, End, Stride):
    Term = Accumulator
    if Cursor % 2:
        Term = Cursor + 11
    else:
        Term = Accumulator % 101 + 7
    Accumulator += Term
Module_Results.append((Accumulator, Term, Scratch, Cursor))
