Tiny = 5e-324
Nested = (2.0, -0.0, 5e-324, 5e-324j)
_Pyceler_Marker = "literal _Pyceler_marker!"

def Same(First, Second):
    return First is Second

def Run(Count):
    global Total, Index, Events
    Total = 0
    Events = []
    Clear()
    for Index in range(Count):
        Total += Index * Index
        if Index % 2 == 0:
            Events.append((Status(), Same(5e-324, Tiny), Same((2.0, -0.0, 5e-324, 5e-324j), Nested), Same("literal _Pyceler_marker!", _Pyceler_Marker)))
    return Total, Events, Status()
