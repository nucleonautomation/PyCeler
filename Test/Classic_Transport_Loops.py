import socket

def Choose_Labels(Distances, Labels, Rows, Groups):
    for Row in range(Rows):
        Best = 0
        for Group in range(1, Groups):
            if Distances[Row, Group] < Distances[Row, Best]:
                Best = Group
        Labels[Row] = Best
    return Labels

def Evaluate_Models(Points, Remaining, Models, Labels, Use_Labels):
    Best = (-1, None)
    Size = Remaining.shape[0]
    for Model, (Ax, Ay, Nx, Ny, Limit, Label) in enumerate(Models):
        Count = 0
        for I in range(Size):
            K = Remaining[I]
            if Use_Labels and Labels[K] != Label:
                continue
            DX = float(Points[K, 0]) - Ax
            DY = float(Points[K, 1]) - Ay
            Distance = DX * Nx + DY * Ny
            if abs(Distance) <= Limit:
                Count += 1
        if Count > Best[0]:
            Best = (Count, Model)
    return Best

def Count_Residuals(Errors, Limit, Report):
    Count = 0
    for I in range(len(Errors)):
        if Errors[I] <= Limit:
            Count += 1
    Report(Count)
    return Count

def Score_Stripes(Points, Ax, Ay, Nx, Ny, Limit, Labels, Label, Use_Stripes, Stripes, Stripe):
    Count = 0
    for K in range(Points.shape[0]):
        if Labels[K] != Label:
            continue
        if Use_Stripes and Stripes[K] != Stripe:
            continue
        DX = float(Points[K, 0]) - Ax
        DY = float(Points[K, 1]) - Ay
        Distance = DX * Nx + DY * Ny
        if Distance < 0.0:
            Distance = -Distance
        if Distance <= Limit:
            Count += 1
    return Count

class Frame_Processor:
    def Process(self, Convert, Frame, Offset):
        Values, Output = Convert(Frame)
        Rows, Columns = Output.shape
        for Y in range(Rows):
            for X in range(Columns):
                Output[Y, X] = Values[Y, X] + Offset
        return Output

def Copy_Rows(Source, Target, Rows):
    for Y in range(Rows):
        for X in range(Target.shape[1]):
            Target[Y, X] = Source[Y, X]
    return Target

def Load_Fragment(Stream, Target, Offset, Length):
    Source = Stream.recv(Length + Offset)
    for Index in range(Length):
        Target[Index] = Source[Offset + Index]
    for Index in range(Length, len(Target)):
        Target[Index] = 0
    return Target

def Pump(Transport, Output, Notify):
    while True:
        try:
            Source = Transport.recv(len(Output))
        except BlockingIOError:
            break
        if not Source:
            break
        for Index in range(len(Output)):
            Output[Index] = Source[Index]
        Notify(Output)
        Transport.sendall(Output)
    return Output

def Read_Exact(Stream, Needed):
    Data = b""
    while len(Data) < Needed:
        try:
            Chunk = Stream.recv(Needed - len(Data))
        except socket.timeout:
            raise
        except Exception:
            return None
        if not Chunk:
            return None
        Data += Chunk
    return Data

def Read_Frame(Peer, Size):
    Buffer = b""
    while len(Buffer) < Size:
        try:
            Part = Peer.recv(Size - len(Buffer))
        except socket.timeout:
            raise
        except:
            return None
        if not Part:
            return None
        Buffer += Part
    return Buffer

def Visible_Counter(Source, Target):
    for Index in range(len(Target)):
        Target[Index] = Source[Index]
    return Index

def Partial_Count(Errors, Limit):
    Count = 0
    try:
        for Index in range(len(Errors)):
            if Errors[Index] <= Limit:
                Count += 1
    except TypeError:
        return Count
    return Count
