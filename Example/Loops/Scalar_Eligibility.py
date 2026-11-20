# Focused scalar eligibility workload; ordinary Python inputs include supported and retained cases.
Module_Results = []
def Compute_And_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) & Operand
        Total += Value
    return Value

def Compute_And_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) & Operand
        Total += Value
    return Value, Total, Index

def Compute_And_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = (Initial + Index) & Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = (Initial + Index) & Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Or_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) | Operand
        Total += Value
    return Value

def Compute_Or_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) | Operand
        Total += Value
    return Value, Total, Index

def Compute_Or_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = (Initial + Index) | Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = (Initial + Index) | Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Xor_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) ^ Operand
        Total += Value
    return Value

def Compute_Xor_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) ^ Operand
        Total += Value
    return Value, Total, Index

def Compute_Xor_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = (Initial + Index) ^ Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = (Initial + Index) ^ Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Left_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) << Operand
        Total += Value
    return Value

def Compute_Left_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) << Operand
        Total += Value
    return Value, Total, Index

def Compute_Left_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = (Initial + Index) << Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = (Initial + Index) << Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Right_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) >> Operand
        Total += Value
    return Value

def Compute_Right_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Initial + Index) >> Operand
        Total += Value
    return Value, Total, Index

def Compute_Right_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = (Initial + Index) >> Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = (Initial + Index) >> Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Right_Literal_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Initial >> 1
        Total += Value
    return Value

def Compute_Right_Literal_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Initial >> 1
        Total += Value
    return Value, Total, Index

def Compute_Right_Literal_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = Initial >> 1
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = Initial >> 1
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Power_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Index % 3) ** Operand
        Total += Value
    return Value

def Compute_Power_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (Index % 3) ** Operand
        Total += Value
    return Value, Total, Index

def Compute_Power_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = (Index % 3) ** Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = (Index % 3) ** Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Negate_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = -Initial
        Total += Value
    return Value

def Compute_Negate_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = -Initial
        Total += Value
    return Value, Total, Index

def Compute_Negate_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = -Initial
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = -Initial
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Invert_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = ~Initial
        Total += Value
    return Value

def Compute_Invert_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = ~Initial
        Total += Value
    return Value, Total, Index

def Compute_Invert_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = ~Initial
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = ~Initial
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Positive_Fresh_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = +(Initial + Index)
        Total += Value
    return Value

def Compute_Positive_Fresh_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = +(Initial + Index)
        Total += Value
    return Value, Total, Index

def Compute_Positive_Fresh_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = +(Initial + Index)
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = +(Initial + Index)
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Conditional_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = ~Initial if Index % 2 else Initial ^ Operand
        Total += Value
    return Value

def Compute_Conditional_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = ~Initial if Index % 2 else Initial ^ Operand
        Total += Value
    return Value, Total, Index

def Compute_Conditional_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = ~Initial if Index % 2 else Initial ^ Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = ~Initial if Index % 2 else Initial ^ Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Modulo_Fresh_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (~Initial) % Operand
        Total += Value
    return Value

def Compute_Modulo_Fresh_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = (~Initial) % Operand
        Total += Value
    return Value, Total, Index

def Compute_Modulo_Fresh_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = (~Initial) % Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = (~Initial) % Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Negative_Cached_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = -1
        Total += Value
    return Value

def Compute_Negative_Cached_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = -1
        Total += Value
    return Value, Total, Index

def Compute_Negative_Cached_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = -1
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = -1
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Aug_And_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value &= Operand
        Total += Value
    return Value

def Compute_Aug_And_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value &= Operand
        Total += Value
    return Value, Total, Index

def Compute_Aug_And_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = Index + 2
            Value &= Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = Index + 2
    Value &= Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Aug_Or_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value |= Operand
        Total += Value
    return Value

def Compute_Aug_Or_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value |= Operand
        Total += Value
    return Value, Total, Index

def Compute_Aug_Or_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = Index + 2
            Value |= Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = Index + 2
    Value |= Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Aug_Xor_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value ^= Operand
        Total += Value
    return Value

def Compute_Aug_Xor_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value ^= Operand
        Total += Value
    return Value, Total, Index

def Compute_Aug_Xor_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = Index + 2
            Value ^= Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = Index + 2
    Value ^= Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Aug_Left_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value <<= Operand
        Total += Value
    return Value

def Compute_Aug_Left_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value <<= Operand
        Total += Value
    return Value, Total, Index

def Compute_Aug_Left_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = Index + 2
            Value <<= Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = Index + 2
    Value <<= Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Aug_Right_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value >>= 1
        Total += Value
    return Value

def Compute_Aug_Right_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value >>= 1
        Total += Value
    return Value, Total, Index

def Compute_Aug_Right_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = Index + 2
            Value >>= 1
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = Index + 2
    Value >>= 1
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Aug_Power_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value **= Operand
        Total += Value
    return Value

def Compute_Aug_Power_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Index + 2
        Value **= Operand
        Total += Value
    return Value, Total, Index

def Compute_Aug_Power_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = Index + 2
            Value **= Operand
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = Index + 2
    Value **= Operand
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_Conditional_Xor_Whole_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Initial + Index
        if Index % 2:
            Value ^= Operand
        if Value % 7 == 0:
            Value += Index
        Total += Value
    return Value

def Compute_Conditional_Xor_Region_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    for Index in range(Count):
        Value = Initial + Index
        if Index % 2:
            Value ^= Operand
        if Value % 7 == 0:
            Value += Index
        Total += Value
    return Value, Total, Index

def Compute_Conditional_Xor_Nested_0(Count, Initial, Operand):
    Value = 0
    Total = 0
    Index = 0
    Events = []
    for Outer in range(2):
        for Index in range(Count):
            Value = Initial + Index
            if Index % 2:
                Value ^= Operand
            if Value % 7 == 0:
                Value += Index
            Total += Value
        Events.append((Value, Total, Index))
    return Events

Initial = 19
Operand = 2
Value = 0
Total = 0
Index = 0
Count = 17
for Index in range(Count):
    Value = Initial + Index
    if Index % 2:
        Value ^= Operand
    if Value % 7 == 0:
        Value += Index
    Total += Value
Module_Results.append((Value, Total, Index))
def Compute_And_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor & Operand
        Sum += Term
    return Term

def Compute_And_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor & Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_And_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Initial + Cursor & Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Initial + Cursor & Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Or_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor | Operand
        Sum += Term
    return Term

def Compute_Or_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor | Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Or_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Initial + Cursor | Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Initial + Cursor | Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Xor_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor ^ Operand
        Sum += Term
    return Term

def Compute_Xor_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor ^ Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Xor_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Initial + Cursor ^ Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Initial + Cursor ^ Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Left_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor << Operand
        Sum += Term
    return Term

def Compute_Left_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor << Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Left_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Initial + Cursor << Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Initial + Cursor << Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Right_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor >> Operand
        Sum += Term
    return Term

def Compute_Right_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor >> Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Right_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Initial + Cursor >> Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Initial + Cursor >> Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Right_Literal_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial >> 1
        Sum += Term
    return Term

def Compute_Right_Literal_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial >> 1
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Right_Literal_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Initial >> 1
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Initial >> 1
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Power_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = (Cursor % 3) ** Operand
        Sum += Term
    return Term

def Compute_Power_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = (Cursor % 3) ** Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Power_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = (Cursor % 3) ** Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = (Cursor % 3) ** Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Negate_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = -Initial
        Sum += Term
    return Term

def Compute_Negate_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = -Initial
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Negate_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = -Initial
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = -Initial
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Invert_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = ~Initial
        Sum += Term
    return Term

def Compute_Invert_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = ~Initial
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Invert_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = ~Initial
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = ~Initial
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Positive_Fresh_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = +(Initial + Cursor)
        Sum += Term
    return Term

def Compute_Positive_Fresh_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = +(Initial + Cursor)
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Positive_Fresh_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = +(Initial + Cursor)
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = +(Initial + Cursor)
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Conditional_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = ~Initial if Cursor % 2 else Initial ^ Operand
        Sum += Term
    return Term

def Compute_Conditional_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = ~Initial if Cursor % 2 else Initial ^ Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Conditional_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = ~Initial if Cursor % 2 else Initial ^ Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = ~Initial if Cursor % 2 else Initial ^ Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Modulo_Fresh_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = ~Initial % Operand
        Sum += Term
    return Term

def Compute_Modulo_Fresh_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = ~Initial % Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Modulo_Fresh_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = ~Initial % Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = ~Initial % Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Negative_Cached_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = -1
        Sum += Term
    return Term

def Compute_Negative_Cached_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = -1
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Negative_Cached_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = -1
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = -1
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Aug_And_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term &= Operand
        Sum += Term
    return Term

def Compute_Aug_And_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term &= Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Aug_And_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Cursor + 2
            Term &= Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Cursor + 2
    Term &= Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Aug_Or_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term |= Operand
        Sum += Term
    return Term

def Compute_Aug_Or_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term |= Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Aug_Or_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Cursor + 2
            Term |= Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Cursor + 2
    Term |= Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Aug_Xor_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term ^= Operand
        Sum += Term
    return Term

def Compute_Aug_Xor_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term ^= Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Aug_Xor_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Cursor + 2
            Term ^= Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Cursor + 2
    Term ^= Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Aug_Left_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term <<= Operand
        Sum += Term
    return Term

def Compute_Aug_Left_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term <<= Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Aug_Left_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Cursor + 2
            Term <<= Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Cursor + 2
    Term <<= Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Aug_Right_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term >>= 1
        Sum += Term
    return Term

def Compute_Aug_Right_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term >>= 1
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Aug_Right_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Cursor + 2
            Term >>= 1
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Cursor + 2
    Term >>= 1
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Aug_Power_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term **= Operand
        Sum += Term
    return Term

def Compute_Aug_Power_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Cursor + 2
        Term **= Operand
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Aug_Power_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Cursor + 2
            Term **= Operand
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Cursor + 2
    Term **= Operand
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
def Compute_Conditional_Xor_Whole_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor
        if Cursor % 2:
            Term ^= Operand
        if Term % 7 == 0:
            Term += Cursor
        Sum += Term
    return Term

def Compute_Conditional_Xor_Region_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    for Cursor in range(Count):
        Term = Initial + Cursor
        if Cursor % 2:
            Term ^= Operand
        if Term % 7 == 0:
            Term += Cursor
        Sum += Term
    return (Term, Sum, Cursor)

def Compute_Conditional_Xor_Nested_1(Count, Initial, Operand):
    Term = 0
    Sum = 0
    Cursor = 0
    Events = []
    for Outer in range(2):
        for Cursor in range(Count):
            Term = Initial + Cursor
            if Cursor % 2:
                Term ^= Operand
            if Term % 7 == 0:
                Term += Cursor
            Sum += Term
        Events.append((Term, Sum, Cursor))
    return Events

Initial = 19
Operand = 2
Term = 0
Sum = 0
Cursor = 0
Count = 17
for Cursor in range(Count):
    Term = Initial + Cursor
    if Cursor % 2:
        Term ^= Operand
    if Term % 7 == 0:
        Term += Cursor
    Sum += Term
Module_Results.append((Term, Sum, Cursor))
