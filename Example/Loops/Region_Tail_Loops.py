# Focused region tail loops workload; ordinary Python inputs include supported and retained cases.
import math
import random
# Test support/workload for conditional tails and bounded prefix recovery.
def Random_Tail(Source: 'numpy.ndarray', Output: 'numpy.ndarray', Limit: int):
    for Index in range(len(Source)):
        Noise = random.random()
        if Index < Limit:
            Value = Source[Index] + Noise
            Output[Index] = Value
    return Output, Index, Noise, Value

def Unobserved_Pairs(Source: 'numpy.ndarray'):
    Total = 0.0
    for Left in range(len(Source)):
        for Right in range(Left + 1, len(Source)):
            Difference = Source[Right] - Source[Left]
            Total += math.sqrt(Difference * Difference + 1.0)
    return Total

def Unobserved_Tail(Source: 'numpy.ndarray', Output: 'numpy.ndarray', Limit: int):
    for Index in range(len(Source)):
        if Index < Limit:
            Value = math.sin(Source[Index])
            Output[Index] = Value
    return Output

def Ordered_Pairs(Source: 'numpy.ndarray'):
    Total = 0.0
    for Left in range(len(Source)):
        for Right in range(Left + 1, len(Source)):
            Difference = Source[Right] - Source[Left]
            Total += math.sqrt(Difference * Difference + 1.0)
    return Total, Left, Right, Difference

def Conditional_Tail(Source: 'numpy.ndarray', Output: 'numpy.ndarray', Limit: int):
    for Index in range(len(Source)):
        if Index < Limit:
            Value = math.sin(Source[Index])
            Alias = Value
            Output[Index] = Value
    return Output, Index, Value, Alias

def Reverse_Triangle(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Row in range(len(Source) - 1, -1, -2):
        for Column in range(Row):
            Value = math.sin(Source[Column])
            Output[Row] = Value
    return Output, Row, Column, Value

def Numeric_Tail(Source, Output, Limit: int):
    for Index in range(len(Source)):
        if Index < Limit:
            Value = math.sin(Source[Index])
            Alias = Value
            Output[Index] = Value
    return Output, Index, Value, Alias
