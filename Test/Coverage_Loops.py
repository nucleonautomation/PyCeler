import math

def Independent_Map(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = Source[Index] * 2
    return Output

def Dependent_Map(Values):
    for Index in range(1, len(Values)):
        Values[Index] += Values[Index - 1]
    return Values

def Alias_Map(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = Source[Index] + 1
    return Output

def Math_Map(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.sin(Source[Index]) + math.sqrt(Source[Index])
    return Output

def Callback_Boundary(Source, Output, Callback):
    Callback("before")
    for Index in range(len(Output)):
        Output[Index] = Source[Index] * 2
    Callback("after")
    return Output

def Callback_In_Loop(Values, Callback):
    for Index in range(len(Values)):
        Values[Index] = Callback(Values[Index])
    return Values

def Scalar_Control(Count):
    Total = 0
    for Index in range(Count):
        if Index % 3 == 0:
            continue
        if Index > 20:
            break
        Total += Index * 2
    else:
        Total += 1
    return Total

def Dynamic_Stride(Start, Stop, Step):
    Total = 0
    for Index in range(Start, Stop, Step):
        Total += Index
    return Total

def Dependent_While(Count):
    Total = 0
    while Count > 0:
        Total += Count
        Count -= 1
    return Total

def Enumerated(Values):
    Total = 0
    for Index, Value in enumerate(Values):
        Total += Index * Value
    return Total

def Zipped(Left, Right):
    Total = 0
    for A, B in zip(Left, Right):
        Total += A * B
    return Total

def Comprehensions(Values):
    List_Result = [Value * Value for Value in Values if Value > 0]
    Set_Result = {Value for Value in Values}
    Dict_Result = {Index: Value for Index, Value in enumerate(Values)}
    Generator = (A * B for A in Values for B in Values if B)
    return List_Result, Set_Result, Dict_Result, Generator

def Early_Return(Values):
    for Value in Values:
        if Value < 0:
            return Value
    return None

def Exception_Boundary(Values, Events):
    for Value in Values:
        try:
            Events.append(10 // Value)
        except ZeroDivisionError:
            Events.append("zero")
        finally:
            Events.append("visited")
    return Events

def Three_Dimensional(Source, Output):
    for First in range(Output.shape[0]):
        for Second in range(Output.shape[1]):
            for Third in range(Output.shape[2]):
                Output[First, Second, Third] = Source[First, Second, Third]
    return Output

def Four_Dimensional(Source, Output):
    for First in range(Output.shape[0]):
        for Second in range(Output.shape[1]):
            for Third in range(Output.shape[2]):
                for Fourth in range(Output.shape[3]):
                    Output[First, Second, Third, Fourth] = Source[First, Second, Third, Fourth]
    return Output

def Mixed_Libraries(Frames, Numpy, OpenCV):
    Results = []
    for Frame in Frames:
        Result = OpenCV.cvtColor(Frame, OpenCV.COLOR_BGR2GRAY)
        Results.append(Numpy.mean(Result))
    return Results

def Ordered_Receive(Transport, Count, Events):
    Buffer = bytearray()
    while len(Buffer) < Count:
        Part = Transport.recv(Count - len(Buffer))
        Events.append(("receive", bytes(Part)))
        if not Part:
            raise EOFError("incomplete buffer")
        Buffer.extend(Part)
    return bytes(Buffer)

def Generator_Suspension(Values):
    for Value in Values:
        yield Value * 2

async def Async_Iteration(Values):
    Result = []
    async for Value in Values:
        Result.append(Value)
    return Result

class Mutable_Receiver:
    def __init__(self, Fragments):
        self._Fragments = list(Fragments)
        self._Requests = []

    def recv(self, Count):
        self._Requests.append(Count)
        return self._Fragments.pop(0) if self._Fragments else b""

    def Transform(self, Values):
        for Index in range(len(Values)):
            Values[Index] += len(self._Requests)
        return Values
