import ctypes
import importlib.util
import random
import sys
from pathlib import Path
import numpy as Numpy
# Isolated verification for random staging.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Main():
    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetErrorMode(3)
    Reference = Load(sys.argv[1], 'Reference')
    Native = Load(sys.argv[2], Path(sys.argv[2]).name.split('.')[0])
    Results = []
    for Module in (Reference, Native):
        random.seed(817)
        random.gauss(0.0, 1.0)
        Output = Numpy.zeros(8192)
        Result = Module.Run(Output)
        Results.append((Result is Output, Output.tobytes(), random.getstate()))
    assert Results[0] == Results[1]
    Count = sum(Value()['Native_Elements'] for Key, Value in vars(Native).items() if Key.startswith('_Pyceler_Fast_') and Key.endswith('Stats'))
    assert Count == 0, Count
    print('Exact result, identity and full RNG state after failed speculative staging; zero published native elements')

if __name__ == '__main__':
    Main()
