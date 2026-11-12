import argparse
import ast
import hashlib
import json
import os
import platform
import random
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter

Root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Root))
from Test import Benchmark_Math

def _Digest(File):
    return hashlib.sha256(Path(File).read_bytes()).hexdigest()

def _Call(Module, Function, Source, Output, Expected, Line, Variant, Threads, Timed, Eligible):
    if Eligible or Variant == "Python":
        return Benchmark_Math._Call(Module, Function, Source, Output, Expected, Line, Variant, Threads, Timed)
    Before = Benchmark_Math._Statistics(Module, Line)
    Duration = Benchmark_Math._Call(Module, Function, Source, Output, Expected, Line, "Python", Threads, Timed)
    After = Benchmark_Math._Statistics(Module, Line)
    if After["Native_Elements"] != Before["Native_Elements"] or After["Parallel_Elements"] != Before["Parallel_Elements"]:
        raise AssertionError((Function, Variant, "Backend-ineligible call entered unboxed arithmetic", Before, After))
    return Duration

def _Measure(Modules, Locations, Sizes, Samples, Threads, Eligible):
    import numpy as N
    Generator = random.Random(20261112)
    Rows = []
    for Function in ("Map_erf", "Map_erfc", "Composed"):
        for Size in Sizes:
            Source = N.linspace(-4.0, 4.0, Size, dtype=N.float64)
            Source.flags.writeable = False
            Expected = N.empty_like(Source)
            getattr(Modules["Python"], Function)(Source, Expected)
            Outputs = {Variant: N.empty_like(Source) for Variant in Modules}
            Values = {Variant: [] for Variant in Modules}
            Observations = {}
            for Variant, Module in Modules.items():
                if Variant != "Python":
                    Module._Pyceler_Dispatch_Stats(True, True)
                try:
                    for Warmup in range(2):
                        _Call(Module, Function, Source, Outputs[Variant], Expected, Locations[Function], Variant, Threads, False, Eligible)
                finally:
                    if Variant != "Python":
                        Observations[Variant] = Module._Pyceler_Dispatch_Stats(False).get("Execution", {})
                if Variant != "Python":
                    Expected_Team = Threads if Eligible and Variant == "OpenMP" else 1
                    Expected_Mode = "native_parallel" if Eligible and Variant == "OpenMP" else "native_serial"
                    if Observations[Variant].get("Native_Entry") is not True or Observations[Variant].get("Actual_Team") != Expected_Team or Observations[Variant].get("Reason") != Expected_Mode:
                        raise AssertionError((Function, Variant, Observations[Variant]))
            Orders = []
            for Sample in range(Samples):
                Order = list(Modules)
                Generator.shuffle(Order)
                Orders.append(Order)
                for Variant in Order:
                    Values[Variant].append(_Call(Modules[Variant], Function, Source, Outputs[Variant], Expected, Locations[Function], Variant, Threads, True, Eligible))
            Medians = {Variant: statistics.median(Times) for Variant, Times in Values.items()}
            Rows.append(dict(Function=Function, Elements=Size, Input_Range=[-4.0, 4.0], Exact_Bits=True, Output_Identity=True,
                             Backend_Eligible=Eligible, Native_Elements_Per_Call=Size if Eligible else 0,
                             Execution="Unboxed_Float64" if Eligible else "Ordered_Original_Library_Calls", Actual_Parallel_Team=Threads if Eligible else None,
                             Warmup_Observations=Observations, Sample_Order=Orders,
                             Timings={Variant: dict(Samples_Ns=Times, Median_Ns=Medians[Variant], Minimum_Ns=min(Times),
                                      CV=statistics.pstdev(Times) / statistics.mean(Times), Speedup_Vs_Python=Medians["Python"] / Medians[Variant],
                                      Speedup_Vs_Serial=Medians["Serial"] / Medians[Variant]) for Variant, Times in Values.items()}))
            print(Function + f" [{Size}, {'unboxed' if Eligible else 'ordered'}]: " + ", ".join(f"{Variant} {Median / 1000000:.6f} ms" for Variant, Median in Medians.items()), flush=True)
    return Rows

def _Run():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--sizes", nargs="+", type=int, default=[64, 4096, 262144])
    Parser.add_argument("--samples", type=int, default=9)
    Parser.add_argument("--threads", type=int, default=2)
    Parser.add_argument("--package", type=Path)
    Parser.add_argument("--expected-build-id")
    Options = Parser.parse_args()
    if not 3 <= Options.samples <= 31 or not 2 <= Options.threads <= 32 or not Options.sizes or any(Size < 1 or Size > 10000000 for Size in Options.sizes):
        Parser.error("Use 3..31 samples, 2..32 threads and sizes 1..10000000")
    if Options.package is not None:
        sys.path.insert(0, str(Options.package.resolve()))
    import Cython
    import numpy as N
    import PyCeler
    Build_Id = getattr(PyCeler, "__build_id__", None)
    if not Build_Id or Options.expected_build_id is not None and Options.expected_build_id != Build_Id:
        raise RuntimeError(("Unexpected active PyCeler build", Build_Id, Options.expected_build_id))
    Package = Path(PyCeler.__file__).resolve().parent
    if Options.package is not None and Package.parent != Options.package.resolve():
        raise RuntimeError(("Package import escaped the requested location", str(Package), str(Options.package)))
    Manifest_File = Package.parent / "PyCeler.manifest.json"
    Manifest = json.loads(Manifest_File.read_text(encoding="utf-8")) if Manifest_File.is_file() else {}
    if Manifest and Manifest.get("Build_Id") != Build_Id:
        raise RuntimeError("Package manifest and imported build identity differ")
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Run = Path(tempfile.mkdtemp(prefix="Erf_Benchmark_", dir=Runs))
    print("Report directory: " + str(Run), flush=True)
    os.environ.update(PYCELER_BUILD_DIR=str(Run / "Build"), OMP_NUM_THREADS=str(Options.threads), OMP_DYNAMIC="FALSE")
    Fixture = Root / "Test/Fast_Erf_Loops.py"
    Tree = ast.parse(Fixture.read_text(encoding="utf-8"))
    Tree.body = [Node for Node in Tree.body if isinstance(Node, (ast.Import, ast.ImportFrom)) or isinstance(Node, ast.FunctionDef) and Node.name in {"Map_erf", "Map_erfc", "Composed"}]
    Text = ast.unparse(Tree) + "\n"
    Locations = {Node.name: Node.body[0].lineno for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef)}
    Reference = Run / "Original_Erf.py"
    Reference.write_text(Text, encoding="utf-8")
    Modules = {"Python": Benchmark_Math._Load("Original_Erf", Reference)}
    Builds = {}
    Eligibility = {}
    for Variant in ("Serial", "OpenMP"):
        Source = Run / (Variant + "_Erf.py")
        Source.write_text(Text, encoding="utf-8")
        Started = perf_counter()
        Converted = PyCeler.Convert(Source, Run / (Variant + "_Source"), OpenMP=Variant == "OpenMP", Select=False)
        Converted.write_text(Converted.read_text(encoding="utf-8") + f"\ndef _Benchmark_Erf_Backend():\n    return _Pyceler_Fast_{Locations['Map_erf']}_Erf_Backend_Eligible\n", encoding="utf-8")
        Binary = PyCeler.Compile(Converted, Run / Variant, Convert=False, OpenMP=Variant == "OpenMP")
        Builds[Variant] = dict(Binary=str(Binary), Binary_SHA256=_Digest(Binary), Generated_Source=str(Converted), Generated_SHA256=_Digest(Converted), Seconds=perf_counter() - Started)
        Modules[Variant] = Benchmark_Math._Load(Source.stem, Binary)
        Modules[Variant]._Pyceler_Dispatch_Stats(False)
        Eligibility[Variant] = Modules[Variant]._Benchmark_Erf_Backend()
    Expected_Eligibility = sys.implementation.name == "cpython" and sys.version_info[:2] in ((3, 12), (3, 13), (3, 14))
    if any(Value != Expected_Eligibility for Value in Eligibility.values()):
        raise AssertionError(("Runtime backend gate differs from the supported source contract", Eligibility, sys.version))
    Rows = _Measure(Modules, Locations, sorted(set(Options.sizes)), Options.samples, Options.threads, Expected_Eligibility)
    Report = dict(Platform=platform.platform(), Machine=platform.machine(), CPU=platform.processor(), Python=sys.version, Interpreter=sys.executable,
                  Cython=Cython.__version__, NumPy=N.__version__, PyCeler=PyCeler.__version__, Build_Id=Build_Id, Package=str(Package),
                  Source_Fingerprint=Manifest.get("Source_Fingerprint"), Manifest_SHA256=_Digest(Manifest_File) if Manifest else None,
                  Fixture_SHA256=_Digest(Fixture), Benchmark_SHA256=_Digest(Path(__file__)), Reference_SHA256=_Digest(Reference),
                  Samples=Options.samples, Warmups=2, Threads=Options.threads, Builds=Builds, Backend_Eligibility=Eligibility,
                  Backend_Status="Eligible_Unboxed" if Expected_Eligibility else "Ineligible_Ordered", Selection=False,
                  Timing="Complete calls including guards, allocation, library operations, writes and checkpoints; preparation/builds/verification excluded; two warmups and shuffled interleaved samples",
                  Contract="Exact output bits and output identity on every call. Eligible calls verify unboxed element counts and actual team; ineligible calls require zero unboxed/parallel counts, with ordered native entry verified during untimed warmups. Raw candidates, not measured-selection claims.", Rows=Rows)
    File = Run / "Results.json"
    File.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print("Report: " + str(File), flush=True)

if __name__ == "__main__":
    _Run()
