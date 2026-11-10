import time

def Progress_Control(Iterations, Events):
    Total = 0
    Index = -23
    for Index in range(Iterations):
        Total += Index * 7
        if Index % 5 == 0:
            Events.append((Index, Total))
            if Index == 10:
                break
            if Index == 5:
                continue
            Index = -77
    Events.append(("done", Total, Index))

Module_Events = []
Module_Total = 0
Module_Index = -23
for Module_Index in range(33):
    Module_Total += (Module_Index * Module_Index + Module_Index * 7) % 999983
    if Module_Index % 7 == 0 and Module_Index != 0:
        Module_Events.append((Module_Index, Module_Total))
Module_Result = (Module_Total, Module_Index)

Module_Division_Events = []
Module_Division_Total = 0
Module_Division_Index = -23
for Module_Division_Index in range(33):
    Module_Division_Total += (Module_Division_Index * Module_Division_Index + Module_Division_Index * 7) / 999983
    if Module_Division_Index % 7 == 0 and Module_Division_Index != 0:
        Module_Division_Events.append((Module_Division_Index, Module_Division_Total))
Module_Division_Result = (Module_Division_Total, Module_Division_Index)

def Remainder(Iterations, Events):
    Total = 0
    Index = -23
    for Index in range(Iterations):
        Total += (Index * Index + Index * 7) % 999983
        if Index % 7 == 0 and Index != 0:
            Events.append((Index, Total))
    Events.append(("done", Total, Index))

def Division(Iterations, Events):
    Total = 0
    Index = -23
    for Index in range(Iterations):
        Total += (Index * Index + Index * 7) / 999983
        if Index % 7 == 0 and Index != 0:
            Events.append((Index, Total))
    Events.append(("done", Total, Index))

def Plain_Region(Iterations, Events):
    Total = 0
    Index = -23
    for Index in range(Iterations):
        Total += Index * 7
    Events.append((Total, Index))

def Mutating_Progress(Iterations, Events, Callback):
    Total = 0
    Index = -23
    for Index in range(Iterations):
        Total += (Index * Index + Index * 7) % 999983
        if Index % 5 == 0 and Index != 0:
            Events.append((Index, Total))
            Total = Callback(Index, Total)
    Events.append(("done", Total, Index))

def Overflow(Iterations, Events, Factor):
    Total = 0
    Index = -23
    for Index in range(Iterations):
        Total += (Index * Index + Index * 7) * Factor
        if Index % 4 == 0 and Index != 0:
            Events.append((Index, Total))
    Events.append(("done", Total, Index))

def Range_Snapshot(Iterations, Events):
    Total = 0
    Index = -23
    for Index in range(Iterations):
        Total += Index + Iterations
        if Index % 5 == 0:
            Events.append((Index, Total, Iterations))
            Iterations += 3
    Events.append(("done", Total, Index, Iterations))

def Negative_Start(Iterations, Events):
    Total = 0
    Index = -23
    for Index in range(-9, Iterations):
        Total += (Index * Index + Index * 7) % 999983
        if Index % 4 == 0:
            Events.append((Index, Total))
    Events.append(("done", Total, Index))

def Conditional_Identity(Iterations, Total, Events):
    for Index in range(Iterations):
        if Index < 0:
            Total += Index
    Events.append(Total)

def Literal_Identity(Iterations, Events):
    Total = 0
    for Index in range(Iterations):
        Total += Index
        Total = 1000000000000000000
    Events.append(Total)

def Constant_Identity(Iterations, Events):
    Total = 0
    for Index in range(Iterations):
        Total = 1000 * 1000
    Events.append(Total)

def Remainder_Benchmark(Iterations):
    Start = time.perf_counter()
    Total = 0
    for Index in range(Iterations):
        Total += (Index * Index + Index * 7) % 999983
        if Index % 10 == 0 and Index != 0:
            Elapsed = time.perf_counter() - Start
            print(f"Progress: {Index:,} / {Iterations:,} | Time: {Elapsed:.2f}s | Result: {Total}")
    Elapsed = time.perf_counter() - Start
    print(f"Final result: {Total}")
    print(f"Total time: {Elapsed:.2f} seconds")

def Division_Benchmark(Iterations):
    Start = time.perf_counter()
    Total = 0
    for Index in range(Iterations):
        Total += (Index * Index + Index * 7) / 999983
        if Index % 10 == 0 and Index != 0:
            Elapsed = time.perf_counter() - Start
            print(f"Progress: {Index:,} / {Iterations:,} | Time: {Elapsed:.2f}s | Result: {Total}")
    Elapsed = time.perf_counter() - Start
    print(f"Final result: {Total}")
    print(f"Total time: {Elapsed:.2f} seconds")
