import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

def _Source(Iterations, Operator, Wrapped):
    Lines = ["import time", "start = time.perf_counter()", "total = 0", f"iterations = {Iterations}",
             "for i in range(iterations):", f"    total += (i * i + i * 7) {Operator} 999983",
             "    if i % 10_000_000 == 0 and i != 0:", "        elapsed = time.perf_counter() - start",
             "        print(f'Progress: {i:,} / {iterations:,} | Time: {elapsed:.2f}s | Result: {total}')",
             "elapsed = time.perf_counter() - start", "print(f'Final result: {total}')", "print(f'Total time: {elapsed:.9f}')"]
    if Wrapped:
        Lines = [Lines[0], "def benchmark():", *("    " + Line for Line in Lines[1:]), "benchmark()"]
    return "\n".join(Lines) + "\n"

def _Run(File, Native):
    if Native:
        Program = "import importlib.util,sys; s=importlib.util.spec_from_file_location(sys.argv[2],sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)"
        Command = [sys.executable, "-I", "-B", "-c", Program, str(File), File.name.split(".")[0]]
    else:
        Command = [sys.executable, "-I", "-B", str(File)]
    Result = subprocess.run(Command, text=True, capture_output=True, timeout=180)
    if Result.returncode:
        raise RuntimeError(Result.stdout + Result.stderr)
    Value = re.search(r"^Final result: (.+)$", Result.stdout, re.MULTILINE).group(1)
    Seconds = float(re.search(r"^Total time: (.+)$", Result.stdout, re.MULTILINE).group(1))
    Progress = [re.sub(r"Time: [0-9.]+s", "Time: CLOCK", Line) for Line in Result.stdout.splitlines() if Line.startswith("Progress:")]
    return dict(Value=Value, Seconds=Seconds, Progress=Progress, Output=Result.stdout)

def _Main():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--iterations", type=int, default=100000000)
    Args = Parser.parse_args()
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    from PyCeler import Analyze, Compile
    Folder = Path(tempfile.mkdtemp(prefix="Scalar_Benchmark_", dir=Root / "Test_Run"))
    os.environ["PYCELER_BUILD_DIR"] = str(Folder / "Build")
    Results = []
    for Label, Operator in (("Modulo", "%"), ("Division", "/"), ("Product", "*")):
        for Wrapped in (False, True):
            Name = Label + ("_Function" if Wrapped else "_Module")
            Source = Folder / (Name + ".py")
            Source.write_text(_Source(Args.iterations, Operator, Wrapped), encoding="utf-8")
            Findings = Analyze(Source)
            Binary = Compile(Source, Folder / "Native", OpenMP=False)
            Python = _Run(Source, False)
            Native = _Run(Binary, True)
            if Python["Value"] != Native["Value"] or Python["Progress"] != Native["Progress"]:
                raise AssertionError((Name, Python, Native))
            Result = dict(Name=Name, Iterations=Args.iterations, Python=Python, Native=Native,
                          Speedup=Python["Seconds"] / Native["Seconds"], Changes=[Finding.Change for Finding in Findings])
            Results.append(Result)
            (Folder / "Results.json").write_text(json.dumps(Results, indent=2), encoding="utf-8")
            print(f"{Name}: {Result['Speedup']:.2f}x; results and progress match", flush=True)
    print(Folder / "Results.json", flush=True)

if __name__ == "__main__":
    _Main()
