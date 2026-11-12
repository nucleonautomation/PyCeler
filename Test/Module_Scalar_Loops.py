Results = {}
Events = []
Total = 0
Iterations = 64
for Index in range(Iterations):
    Total += (Index * Index + Index * 7) % 999983
    if Index % 8 == 0 and Index != 0:
        Events.append((Index, Total))
Results["Progress"] = (Total, Index, tuple(Events))

def Callback():
    global Total, Index, Iterations
    Events.append((Index, Total))
    if Index == 8:
        Total = -10000
        Index = 777
        Iterations = 1

Events = []
Total = 0
Iterations = 32
for Index in range(Iterations):
    Total += (Index * Index + Index * 7) % 999983
    if Index % 8 == 0 and Index != 0:
        Callback()
Results["Mutation"] = (Total, Index, Iterations, tuple(Events))

Events = []
Total = 2**100
for Index in range(16):
    Total += (Index * Index + Index * 7) % 999983
    if Index % 4 == 0 and Index != 0:
        Events.append((Index, Total))
Results["Bigint"] = (Total, Index, tuple(Events))

Total = 42
Index = -23
for Index in range(0):
    Total += (Index * Index + Index * 7) % 999983
Results["Empty"] = (Total, Index)

Total = 0
Events = []
for Index in range(29, -9, -3):
    Total += (Index * Index + Index * 7) % 999983
    if Index % 8 == 0 and Index != 0:
        Events.append((Index, Total))
Results["Descending"] = (Total, Index, tuple(Events))
