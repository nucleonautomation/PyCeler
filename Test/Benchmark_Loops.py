import importlib.util
import json
import math
import os
import platform
import random
import statistics
import sys
import tempfile
import timeit
from pathlib import Path

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Cases(Modules):
    import numpy as Numpy
    Cases = []
    for Size, Rows, Columns, Shape in (("Small", 4, 4, (1, 4, 4)), ("Medium", 128, 256, (8, 32, 128)), ("Large", 512, 512, (16, 128, 128))):
        Expected_Count = Modules["Python"].Count_Pairs(Rows, Columns)
        for Variant in ("Python", "Serial"):
            Function = Modules[Variant].Count_Pairs
            Result = Function(Rows, Columns)
            if type(Result) is not int or Result != Expected_Count:
                raise ValueError(f"Invalid scalar result: {Variant}, {Size}")
            Cases.append(("Count_Pairs", Size, (Rows, Columns), Variant, timeit.Timer(lambda F=Function, R=Rows, C=Columns: F(R, C))))
        Source = (Numpy.arange(math.prod(Shape), dtype=Numpy.int32) % 71).reshape(Shape)
        Source.flags.writeable = False
        Expected = Modules["Python"].Threshold_Volume(Source, Numpy.empty_like(Source), 35)
        for Variant, Module in Modules.items():
            Output = Numpy.full_like(Source, -1)
            Function = Module.Threshold_Volume
            if Function(Source, Output, 35) is not Output:
                raise ValueError(f"Invalid array identity: {Variant}, {Size}")
            Numpy.testing.assert_array_equal(Output, Expected)
            Cases.append(("Threshold_Volume", Size, Shape, Variant, timeit.Timer(lambda F=Function, S=Source, O=Output: F(S, O, 35))))
    return Cases

def _Measure(Cases):
    Rows = []
    for Name, Size, Shape, Variant, Timer in Cases:
        Timer.timeit(3)
        Calls = 1
        while Timer.timeit(Calls) < 0.012:
            Calls *= 2
        Rows.append(dict(Function=Name, Size=Size, Shape=Shape, Elements=math.prod(Shape), Variant=Variant, Calls_Per_Sample=Calls, Samples_ns=[]))
    Order = list(range(len(Cases)))
    Shuffle = random.Random(4281)
    for Round in range(18):
        Shuffle.shuffle(Order)
        for Index in Order:
            Row = Rows[Index]
            Calls = Row["Calls_Per_Sample"]
            Duration = Cases[Index][-1].timeit(Calls)
            Row["Samples_ns"].append(Duration * 1e9 / Calls)
        if Round == 8:
            Noisy = any(statistics.pstdev(Row["Samples_ns"]) > 0.10 * statistics.mean(Row["Samples_ns"]) for Row in Rows)
            Close = any(0.90 < statistics.median(Row["Samples_ns"]) / statistics.median(Other["Samples_ns"]) < 1.10
                        for Row in Rows for Other in Rows if Row["Function"] == Other["Function"] and Row["Size"] == Other["Size"] and Row["Variant"] != Other["Variant"])
            if not (Noisy or Close):
                break
    for Row in Rows:
        Samples = Row["Samples_ns"]
        Row.update(Median_ns=statistics.median(Samples), Minimum_ns=min(Samples), CV=statistics.pstdev(Samples) / statistics.mean(Samples))
    Times = {(Row["Function"], Row["Size"], Row["Variant"]): Row["Median_ns"] for Row in Rows}
    for Row in Rows:
        Key = (Row["Function"], Row["Size"])
        Row["Speedup_vs_Python"] = Times[(*Key, "Python")] / Row["Median_ns"]
        Row["Speedup_vs_Serial"] = Times[(*Key, "Serial")] / Row["Median_ns"]
    return Rows

def _Run():
    Directory = Path(__file__).resolve().parent
    Root = Directory.parent
    sys.path.insert(0, str(Root))
    import PyCeler
    import Cython
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Run = Path(tempfile.mkdtemp(prefix="Benchmark_Loops_", dir=Runs))
    os.environ.update(PYCELER_BUILD_DIR=str(Run / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
    import numpy as Numpy
    Fixture = Directory / "Loop_Workloads.py"
    Modules = {"Python": _Load("Original_Loops", Fixture)}
    for Variant in ("Serial", "OpenMP"):
        Source = Run / (Variant + "_Loops.py")
        Source.write_bytes(Fixture.read_bytes())
        Binary = PyCeler.Compile(Source, Run / Variant, OpenMP=Variant == "OpenMP", Select=False)
        Modules[Variant] = _Load(Source.stem, Binary)
    Rows = _Measure(_Cases(Modules))
    Report = Run / "Timings.json"
    Report.write_text(json.dumps(dict(Platform=platform.platform(), CPU=platform.processor(), Python=sys.version,
                                      Cython=Cython.__version__, NumPy=Numpy.__version__, PyCeler=PyCeler.__version__,
                                      ABI="3.11", OpenMP_Threads=2, Rows=Rows), indent=2), encoding="utf-8")
    print(Report)
    for Row in Rows:
        print(f"{Row['Function']:18} {Row['Size']:7} {Row['Variant']:7} {Row['Median_ns'] / 1000:10.2f} us  {Row['Speedup_vs_Python']:8.2f}x Python")

if __name__ == "__main__":
    _Run()
