def Count(N):
    Total = 0
    for Index in range(N):
        Total += Index
    return Total
# Test support/workload for stable-ABI loading and native loop execution.
def Clear(Values):
    for Index in range(len(Values)):
        Values[Index] = 0
    return Values
