import argparse
import importlib.util
import json
import os
import platform
import sys
from pathlib import Path

def _Run():
    Parser = argparse.ArgumentParser(description="Exercise an isolated pip-installed PyCeler wheel.")
    Parser.add_argument("library", type=Path)
    Parser.add_argument("output", type=Path)
    Args = Parser.parse_args()
    Library, Output = Args.library.resolve(), Args.output.resolve()
    sys.path.insert(0, str(Library))
    os.environ.update(OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE", PYCELER_BUILD_DIR=str(Output / "Build"))
    import PyCeler
    import PyCeler.Engine
    import numpy as Numpy
    assert Path(PyCeler.__file__).resolve().is_relative_to(Library)
    assert Path(PyCeler.Engine.__file__).resolve().is_relative_to(Library)
    assert len(PyCeler.__build_id__) == len(PyCeler.__source_fingerprint__) == 64
    Source = Output / "Wheel_Kernel.py"
    Source.write_text("def Count(N):\n    Total = 0\n    for Index in range(N):\n        Total += Index\n    return Total\n\ndef Clear(Values):\n    for Index in range(len(Values)):\n        Values[Index] = 0\n    return Values\n", encoding="utf-8")
    assert len(PyCeler.Analyze(Source)) == 2
    assert PyCeler.Convert(Source, Output / "Converted", Select=False).is_file()
    Binary = PyCeler.Compile(Source, Output / "Native", Select=False, OpenMP=True)
    Spec = importlib.util.spec_from_file_location("Wheel_Kernel", Binary)
    Native = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Native)
    assert Native.Count(100000) == sum(range(100000))
    Calls, Team = Native._Pyceler_Parallel_Stats()
    assert Calls > 0 and Team == 2, (Calls, Team)
    for Dtype in (Numpy.int32, Numpy.int64, Numpy.float32, Numpy.float64):
        Values = Numpy.ones(4096, dtype=Dtype)
        assert Native.Clear(Values) is Values and not Values.any()
    Values = [1, 2, 3]
    assert Native.Clear(Values) is Values and Values == [0, 0, 0]
    Report = dict(Status="passed", Python=sys.version, Platform=platform.platform(), Interpreter_Architecture=platform.architecture()[0],
                  Engine=PyCeler.Engine.__file__, Build_Id=PyCeler.__build_id__, Source_Fingerprint=PyCeler.__source_fingerprint__,
                  Analyze=True, Convert=True, Compile=True, Native_Parallel_Calls=Calls, Actual_OpenMP_Team=Team)
    (Output / "Installed_Wheel.json").write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(json.dumps(Report, indent=2), flush=True)

if __name__ == "__main__":
    _Run()
