raise RuntimeError("Diagnostic analysis must not execute this module.")

def Rejected_With_Calls(Iterations, Callback):
    Total = 0
    for Index in range(Iterations):
        Total += Index @ 2
        Callback(Total)
    print(Total)

Total = 0
for Index in range(10):
    Total += Index @ 3
    print(Total)
