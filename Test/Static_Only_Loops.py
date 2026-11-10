raise RuntimeError("Static analysis executed the target module.")

class Example:
    def Clear(self, Buffer):
        for Position in range(len(Buffer)):
            Buffer[Position] = 0

def Indirect_Write(Values, Indices):
    for Index in range(len(Values)):
        Values[Indices[Index]] = 0

def With_Call(Values, Callback):
    for Index in range(len(Values)):
        Values[Index] = 0
        Callback(Values)

def Other_Source(Values, Source):
    for Index in range(1, len(Values)):
        Values[Index] += Source[Index - 1]

def Other_Bounds(Values, Positions):
    for Index in Positions:
        Values[Index] = 0

def Nested(Values, Count):
    while Count > 0:
        for Index in range(len(Values)):
            Values[Index] = 0
        Count -= 1
