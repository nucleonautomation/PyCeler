import importlib.util
import sys
from pathlib import Path
import numpy as Numpy

def _Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

Source, Binary = map(Path, sys.argv[1:])
for Module in (_Load(Source, "Reference"), _Load(Binary, Binary.stem)):
    Cells = [1, 0, 1, 0, 1]
    Best = [0, 0]
    Winners = [-1, -1]
    assert Module.Scatter_Best(Cells, [6, 2, 6, 5, 4], Best, Winners) is Winners
    assert Best == [5, 6] and Winners == [3, 0]
    Values = [1e16, 1., -1e16, 7.]
    Totals = [0., 0.]
    assert Module.Ordered_Moments(Values, [0, 0, 0, 1], Totals) is Totals
    assert Totals == [0., 7.]
    for Dtype in (Numpy.uint8, Numpy.uint16):
        Depth = Numpy.array([[0, 2, 3], [0, 4, 5]], dtype=Dtype)
        Output = Numpy.full_like(Depth, 99)
        assert Module.Median_Depth(Depth, Output, 1) is Output
        Numpy.testing.assert_array_equal(Output, [[0, 4, 4], [0, 4, 4]])
