import numpy as Numpy

def _Cases(Name):
    Cases = []
    for Size, Holdout in ((32, False), (96, True), (4096, False), (6144, True), (65536, False), (98304, True)):
        Shape = (8, Size // 8) if Name == "Column_First" else (Size,)
        Source = (Numpy.arange(Size, dtype=Numpy.int32) % 7).reshape(Shape)
        Count = 2 if Name in ("Fused_Maps", "Repeated_Scores", "Local_Values", "Versioned_Reads") else 1
        Extra = (1,) if Name == "Repeated_Scores" else (2, 3) if Name in ("Invariant_Scale", "Temporary_Pipeline") else ()
        Args = (Source, *(Numpy.zeros_like(Source) for Index in range(Count)), *Extra)
        Cases.append(dict(Args=Args, Label=f"{Name}_{Size}", Holdout=Holdout))
    return Cases

def Fused_Maps():
    return _Cases("Fused_Maps")

def Repeated_Scores():
    return _Cases("Repeated_Scores")

def Local_Values():
    return _Cases("Local_Values")

def Versioned_Reads():
    return _Cases("Versioned_Reads")

def Column_First():
    return _Cases("Column_First")

def Invariant_Scale():
    return _Cases("Invariant_Scale")

def Temporary_Pipeline():
    return _Cases("Temporary_Pipeline")
