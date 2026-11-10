def Count(N):
    Total = 0
    for Index in range(N):
        Total += Index
    return Total

def Clear(Values):
    for Index in range(len(Values)):
        Values[Index] = 0
    return Values
