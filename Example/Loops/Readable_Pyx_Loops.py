# Focused readable pyx loops workload; ordinary Python inputs include supported and retained cases.
from __future__ import annotations
import math
import numpy as N
# Test support/workload for editable single-file output without runtime source strings.
Message = 'editable source'
Events = []

def Smooth(Value):
    Scaled = Value * 0.5
    return Scaled + math.sin(Scaled)

def Process(Source, Output):
    for Row in range(Source.shape[0]):
        for Column in range(Source.shape[1]):
            Output[Row, Column] = Smooth(Source[Row, Column])
    return Output

def Ordinary(Value):
    Events.append(Value)
    return Message, Value ** 3

def Ordered(Source):
    Result = 0.0
    for Index in range(len(Source)):
        Result += Source[Index] * 0.5
    return Result
