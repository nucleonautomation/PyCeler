def Clear_Elements(Values):
    for Index in range(len(Values)):
        Values[Index] = 0
    return Values

def Prefix_Sum(Values):
    for Index in range(1, len(Values)):
        Values[Index] += Values[Index - 1]
    return Values
