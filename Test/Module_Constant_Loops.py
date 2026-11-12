Marker = 1000
Finite = 1.25
Zero = -0.0
Infinite = 1e10000
Nested_Tuple = (1000, (1.25, -0.0), "identity marker!")
Text = "identity marker!"
Data = b"identity bytes!"
def Same(Value, Expected):
    return Value is Expected
Events = []
Total = 0
for Index in range(16):
    Total += Index * Index
    if Index % 4 == 0:
        Events.append((Same(1000, Marker), Same(1.25, Finite), Same(-0.0, Zero), Same(1e10000, Infinite),
                       Same((1000, (1.25, -0.0), "identity marker!"), Nested_Tuple),
                       Same("identity marker!", Text), Same(b"identity bytes!", Data)))
        def Nested(Value=(1000, (1.25, -0.0), "identity marker!")):
            return Same(Value, Nested_Tuple), Same(1000, Marker)
        Events.append(Nested())
Total = 2 ** 70
for Index in range(6):
    Total += Index * Index
    if Index % 2 == 0:
        Events.append((Same(1000, Marker), Same((1000, (1.25, -0.0), "identity marker!"), Nested_Tuple)))
def range(Count):
    return [2, 5, 8]
for Index in range(100):
    Total += Index * Index
    if Index % 2 == 0:
        Events.append((Same(1000, Marker), Same(-0.0, Zero), Same(b"identity bytes!", Data)))
_Pyceler_Marker = "literal _Pyceler_marker!"
_Pyceler_Total = 0
for _Pyceler_Index in range(100):
    _Pyceler_Total += _Pyceler_Index * _Pyceler_Index
    if _Pyceler_Index % 2 == 0:
        Events.append((Same("literal _Pyceler_marker!", _Pyceler_Marker), Same(1000, Marker)))
