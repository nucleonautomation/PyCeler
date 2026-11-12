Events = []
Results = {}
Total = 0
if True:
    for Index in range(8):
        Total += Index * 7
    Events.append(("if", Total, Index))

try:
    for Index in range(6):
        Total += 10 // (3 - Index)
except ZeroDivisionError:
    Events.append(("division", Total, Index))
finally:
    for Final_Index in range(4):
        Total += Final_Index * 2
    Events.append(("finally", Total, Final_Index))

class Manager:
    def __enter__(self):
        Events.append("enter")
        return 2

    def __exit__(self, Kind, Value, Traceback):
        Events.append(("exit", Kind.__name__ if Kind is not None else None, Total, Index))

with Manager() as Factor:
    for Index in range(5):
        Total += Index * Factor
    Events.append(("with", Total, Index))

for Outer in range(3):
    for Index in range(4):
        Total += Index + Outer
    Events.append(("outer", Outer, Total, Index))

Remaining = 2
while Remaining:
    for Index in range(4):
        Total += Index * Remaining
    Remaining -= 1
    Events.append(("while", Remaining, Total, Index))

if False:
    Missing = 0
try:
    for Index in range(2):
        Missing += Index
except NameError as Error:
    Events.append(("missing", Index, type(Error).__name__))

def Global_Region(Flag):
    global Total, Index
    if Flag:
        for Index in range(4):
            Total += Index * 3

Global_Region(True)
Results["Nested"] = (Total, Index, Final_Index, tuple(Events))

def Local_Reporting(Local):
    global Total, Index
    for Index in range(4):
        Total += Index * 2
        if Index % 2 == 0:
            Events.append((Local, Index, Total))

Local_Reporting("local")
Results["Local_Reporting"] = (Total, Index, tuple(Events))
