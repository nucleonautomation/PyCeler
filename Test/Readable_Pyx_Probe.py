import importlib.util
import json
import sys
import numpy as N
# Isolated verification for editable single-file output without runtime source strings.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Run(Source, Binary, Message='edited generated source'):
    Reference = _Load('Reference', Source)
    Native = _Load('Readable_Pyx_Loops', Binary)
    assert Native.Ordinary(3) == (Message, 27)
    assert Native.Events == [3]
    Values = N.arange(4096, dtype='float64').reshape(128, 32) * 0.001
    Expected, Actual = N.zeros_like(Values), N.zeros_like(Values)
    Reference.Process(Values, Expected)
    Native._Pyceler_Dispatch_Stats(True, True)
    Native.Process(Values, Actual)
    assert Expected.tobytes() == Actual.tobytes()
    Stats = Native._Pyceler_Dispatch_Stats()
    assert Stats['Totals']['Native_Entries'] > 0, Stats
    assert Stats['Totals']['Maximum_Team'] > 1, Stats
    assert Reference.Ordered(Values.reshape(-1)) == Native.Ordered(Values.reshape(-1))
    print(json.dumps(dict(Exact=True, Editable=True, Stats=Stats)), flush=True)

if __name__ == '__main__':
    _Run(*sys.argv[1:])
