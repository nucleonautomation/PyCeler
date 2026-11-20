# Focused numeric loops workload; ordinary Python inputs include supported and retained cases.
def Clear_Elements(Values):
    for Index in range(len(Values)):
        Values[Index] = 0
    return Values
# Test support/workload for numeric.
def Prefix_Sum(Values):
    for Index in range(1, len(Values)):
        Values[Index] += Values[Index - 1]
    return Values
