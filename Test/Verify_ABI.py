import argparse
import json
import os
import sys
from pathlib import Path

def _Main():
    Parser = argparse.ArgumentParser(description="Verify the built stable-ABI package and ABI_Loops module using this interpreter.")
    Parser.add_argument("native", type=Path, help="Directory containing the compiled ABI_Loops module")
    Parser.add_argument("--numpy", type=Path, help="Optional directory containing NumPy for this interpreter")
    Args = Parser.parse_args()
    Root = Path(__file__).resolve().parents[1]
    Native = Args.native.resolve()
    sys.path.insert(0, str(Root / "Build" / "Lib"))
    sys.path.insert(0, str(Native))
    if Args.numpy:
        sys.path.insert(0, str(Args.numpy.resolve()))
    os.environ.update(OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
    import PyCeler
    import PyCeler.Engine
    import ABI_Loops
    import numpy as Numpy
    Source = Root / "Test" / "ABI_Loops.py"
    assert len(PyCeler.Analyze(Source)) == 2
    Converted = PyCeler.Convert(Source, Native.parent / ("Converted_" + str(sys.version_info.minor)), Select=False)
    assert Converted.is_file()
    for Size in (0, 1, 12, 1000):
        assert ABI_Loops.Count(Size) == sum(range(Size))
    Fallbacks = []
    def _Profile(Frame, Event, Value):
        if Event == "call" and Frame.f_code.co_filename == "ABI_Loops.py" and Frame.f_code.co_name == "Clear":
            Fallbacks.append(Event)
    for Dtype in (Numpy.int32, Numpy.int64, Numpy.float32, Numpy.float64):
        for Size in (0, 17, 131072):
            Values = Numpy.ones(Size, dtype=Dtype)
            sys.setprofile(_Profile)
            try:
                assert ABI_Loops.Clear(Values) is Values and not Values.any()
            finally:
                sys.setprofile(None)
    assert not Fallbacks
    Report = dict(Status="passed", Python=sys.version, NumPy=Numpy.__version__, Engine=PyCeler.Engine.__file__, Binary=ABI_Loops.__file__,
                  Scalar_Cases=4, Native_Array_Cases=12, OpenMP_Threads=2, Analyze=True, Convert=True)
    Result = Native.parent / ("ABI_" + str(sys.version_info.minor) + ".json")
    Result.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(Result, flush=True)

if __name__ == "__main__":
    _Main()
