import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from time import perf_counter

def _Source(Functions):
    Sections = []
    for Index in range(Functions):
        Sections.append(f"def Pipeline_{Index}(Input, Output):\n    for Index in range(len(Input)):\n        Output[Index] = Input[Index] * 2\n    for Index in range(len(Input)):\n        Output[Index] = Output[Index] + 1\n    return Output\n")
    return "\n".join(Sections)

def _Main():
    Parser = argparse.ArgumentParser(description="Measure read-only analysis scaling on large structural Python files.")
    Parser.add_argument("--functions", type=int, nargs="+", default=[100, 500, 1500])
    Parser.add_argument("--compile-only", action="store_true", help="Also compile and import the largest case without conversion")
    Args = Parser.parse_args()
    if any(Size <= 0 or Size > 10000 for Size in Args.functions):
        Parser.error("Function counts must be between 1 and 10000")
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    import PyCeler
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Run = Path(tempfile.mkdtemp(prefix="Large_Source_", dir=Runs))
    Report = dict(Platform=platform.platform(), Python=sys.version, PyCeler=PyCeler.__version__, Cases=[])
    for Functions in Args.functions:
        Source = Run / f"Source_{Functions}.py"
        Source.write_text(_Source(Functions), encoding="utf-8")
        Digest = hashlib.sha256(Source.read_bytes()).hexdigest()
        Before = set(Run.iterdir())
        Durations = []
        for Repeat in range(3):
            Start = perf_counter()
            Findings = PyCeler.Analyze(Source)
            Durations.append(perf_counter() - Start)
            if len(Findings) != Functions * 2 or any("loop_fusion" not in Item.Transformations for Item in Findings):
                raise AssertionError("Large source analysis lost loop coverage or structural transformations")
        if hashlib.sha256(Source.read_bytes()).hexdigest() != Digest or set(Run.iterdir()) != Before:
            raise AssertionError("Read-only analysis changed its source or generated output")
        Case = dict(Functions=Functions, Lines=len(Source.read_text(encoding="utf-8").splitlines()), Loops=len(Findings), SHA256=Digest,
                    Seconds=Durations, Median_Seconds=statistics.median(Durations))
        Report["Cases"].append(Case)
        print(json.dumps(Case), flush=True)
    if Args.compile_only:
        Source = Run / f"Source_{max(Args.functions)}.py"
        os.environ["PYCELER_BUILD_DIR"] = str(Run / "Build")
        Start = perf_counter()
        Binary = PyCeler.Compile(Source, Run / "Native", Convert=False)
        Program = "\n".join(("import importlib, sys", "sys.path.insert(0, sys.argv[1])", "Module = importlib.import_module(sys.argv[2])",
                             "for Index in range(int(sys.argv[3])):", "    Values, Output = [0, 1, 2, 3, 4], [0] * 5",
                             "    Result = getattr(Module, f'Pipeline_{Index}')(Values, Output)",
                             "    assert Result is Output and Output == [1, 3, 5, 7, 9] and Values == [0, 1, 2, 3, 4]"))
        Process = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent), Source.stem, str(max(Args.functions))],
                                 capture_output=True, text=True, timeout=60)
        if Process.returncode:
            raise AssertionError(Process.stdout + Process.stderr)
        Expected = next(Case["SHA256"] for Case in Report["Cases"] if Case["Functions"] == max(Args.functions))
        if hashlib.sha256(Source.read_bytes()).hexdigest() != Expected or list(Binary.parent.iterdir()) != [Binary]:
            raise AssertionError("Compile-only changed the source or published nonbinary files")
        Report["Compile_Only"] = dict(Seconds=perf_counter() - Start, Binary=str(Binary), Functions_Checked=max(Args.functions), Status="passed")
    Result = Run / "Results.json"
    Result.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(Result, flush=True)

if __name__ == "__main__":
    _Main()
