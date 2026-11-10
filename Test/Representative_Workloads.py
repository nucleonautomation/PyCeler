import numpy as Numpy

def Build_Map_Cases():
    Result = []
    for Size, Holdout in ((32, False), (96, True), (256, False), (384, True)):
        Source = Numpy.arange(Size, dtype=Numpy.int32) % 9
        Output = Numpy.zeros_like(Source)
        Result.append(dict(Args=(Source, Output), Label=f"Map_{Size}", Holdout=Holdout))
    return Result

def Build_Aliased_Cases():
    Storage = Numpy.arange(16, dtype=Numpy.int32)
    return [dict(Args=(Storage[:-1], Storage[1:]), Label="Shifted_Overlap", Holdout=True)]
