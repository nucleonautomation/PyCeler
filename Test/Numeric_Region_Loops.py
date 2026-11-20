import math
# Test support/workload for nested numeric control flow, list identities and partial errors.
def Escape(Canvas, Rows, Columns, Limit):
    for North in range(Rows):
        for East in range(Columns):
            Real = (East - Columns / 2) * 3.8 / Columns - 0.4
            Imaginary = (North - Rows / 2) * 3.8 / Columns
            U = 0.0
            V = 0.0
            Count = 0
            while U * U + V * V < 3.9 and Count < Limit:
                Next = U * U - V * V + Real
                V = 2.0 * U * V + Imaginary
                U = Next
                Count += 1
            Canvas[North][East] = Count
    return Canvas

def Pairwise(P, Q, Weight, First, Second, Size, Soft, Scale):
    for Target in range(Size):
        for Source in range(Size):
            if Target == Source:
                continue
            Dx = P[Source] - P[Target]
            Dy = Q[Source] - Q[Target]
            Distance = Dx * Dx + Dy * Dy + Soft
            Reciprocal = 1.0 / math.sqrt(Distance)
            Strength = Scale * Weight[Source] * Reciprocal ** 3
            First[Target] += Strength * Dx
            Second[Target] += Strength * Dy
    return First, Second

def Integrate(P, Q, V, W, A, B, Size, Step):
    for Point in range(Size):
        V[Point] += A[Point] * Step
        W[Point] += B[Point] * Step
        P[Point] += V[Point] * Step
        Q[Point] += W[Point] * Step
    return P, Q, V, W

def Prefix(Values, Size):
    for Position in range(1, Size):
        Values[Position] = Values[Position - 1] * 0.25 + Values[Position] * 0.75
    return Values

def Powers(Values, Output, Size):
    for Position in range(Size):
        Positive = Values[Position] ** 3
        Negative = Values[Position] ** -2
        Output[Position] = Positive + Negative
    return Output

def Control(Values, Output, Size, Limit):
    for Position in range(Size):
        Value = Values[Position]
        Counter = 0
        while Counter < Limit:
            Counter += 1
            if Counter == 3:
                continue
            Value = Value * 0.9 + 0.125
            if Value > 1.2:
                break
        Output[Position] = Value + 0.0
    return Output

def Nested(Values, Output, Rows, Columns, Passes):
    for North in range(Rows):
        for East in range(Columns):
            Value = Values[North][East]
            for Cycle in range(Passes):
                Value = Value * 0.9 + 0.05
            Output[North][East] = Value + 0.0
    return Output

def Aliases(Values, Output, Size):
    Position = -1
    Value = Shared = None
    for Position in range(Size):
        Value = Values[Position] * 0.25
        Shared = Value
        Output[Position] = Shared
    return Output, Value, Shared, Position

def Dimensions(Values, Output, Size):
    Position = -1
    for Position in range(len(Values)):
        Value = math.sqrt(Values[Position])
        Output[Position] = Value * 0.7
    return Output, Position

def Sparse(Values, Output, Size):
    for Position in range(Size):
        Value = Values[Position]
        if Position == 3:
            continue
        if Value > 0.1:
            Output[Position] = Value * 0.5
    return Output

def Binding_State(Values, Output, Size):
    for Position in range(Size):
        Output[Position] += Values[Position] * 0.1
        Value = math.sqrt(Values[Position])
        Output[Position] += Value
    return Output
