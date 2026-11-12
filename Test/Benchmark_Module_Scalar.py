import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

def _Worker(File, Destination):
    Start = time.perf_counter()
    Spec = importlib.util.spec_from_file_location(File.name.split(".")[0], File)
    Module = importlib.util.module_from_spec(Spec)
    sys.modules[Spec.name] = Module
    Spec.loader.exec_module(Module)
    Seconds = time.perf_counter() - Start
    Hooks = [Value for Name, Value in vars(Module).items() if Name.endswith("Module_Stats") and callable(Value)]
    Values = {Name: getattr(Module, Name) for Name in ("total", "i", "iterations") if hasattr(Module, Name)}
    Report = dict(Seconds=Seconds, Values=Values, Native=Hooks[0]() if Hooks else {})
    Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")

def _Run(File, Folder, Label, Timeout):
    Destination = Folder / (Label + ".json")
    Command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker", str(File), "--result", str(Destination)]
    Process = subprocess.run(Command, text=True, capture_output=True, timeout=Timeout)
    (Folder / (Label + ".stdout.txt")).write_text(Process.stdout, encoding="utf-8")
    (Folder / (Label + ".stderr.txt")).write_text(Process.stderr, encoding="utf-8")
    if Process.returncode:
        raise RuntimeError(Label + " failed: " + Process.stdout + Process.stderr)
    Report = json.loads(Destination.read_text(encoding="utf-8"))
    Report["Progress"] = [re.sub(r"Time: [0-9.]+s", "Time: CLOCK", Line) for Line in Process.stdout.splitlines() if Line.startswith("Progress:")]
    Report["Final_Output"] = [Line for Line in Process.stdout.splitlines() if Line.startswith("Final result:")]
    return Report

def _Main():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--input", type=Path)
    Parser.add_argument("--samples", type=int, default=3)
    Parser.add_argument("--threads", type=int, default=2)
    Parser.add_argument("--timeout", type=int, default=600)
    Parser.add_argument("--output", type=Path)
    Parser.add_argument("--worker", type=Path)
    Parser.add_argument("--result", type=Path)
    Args = Parser.parse_args()
    if Args.worker is not None:
        _Worker(Args.worker, Args.result)
        return
    if Args.input is None or Args.samples < 1 or Args.threads < 1:
        Parser.error("--input and positive sample/thread counts are required")
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    from PyCeler import Analyze, Compile, __version__
    Source = Args.input.resolve()
    Original = Source.read_bytes()
    Base = Root / "Test_Run"
    Base.mkdir(exist_ok=True)
    Folder = Args.output or Path(tempfile.mkdtemp(prefix="Module_Benchmark_", dir=Base))
    Folder.mkdir(parents=True, exist_ok=True)
    Snapshot = Folder / Source.name
    Snapshot.write_bytes(Original)
    os.environ["PYCELER_BUILD_DIR"] = str(Folder / "Build")
    os.environ["OMP_NUM_THREADS"] = str(Args.threads)
    Findings = Analyze(Snapshot, OpenMP=True)
    Build_Start = time.perf_counter()
    Serial = Compile(Snapshot, Folder / "Serial", Select=False, OpenMP=False)
    Parallel = Compile(Snapshot, Folder / "Parallel", Select=False, OpenMP=True)
    Build_Seconds = time.perf_counter() - Build_Start
    Report = dict(PyCeler=__version__, Python=sys.version, Platform=platform.platform(), Source=str(Source),
                  SHA256=hashlib.sha256(Original).hexdigest(), Snapshot=str(Snapshot), Build_Seconds=Build_Seconds,
                  Binaries=dict(Serial=str(Serial), Parallel=str(Parallel)), Threads=Args.threads,
                  Findings=[asdict(Item) for Item in Findings], Samples=[], Validation={})
    Destination = Folder / "Results.json"
    Variants = (("Python", Snapshot), ("Serial", Serial), ("Parallel", Parallel))
    Reference = None
    for Sample in range(Args.samples):
        Order = Variants if Sample % 2 == 0 else tuple(reversed(Variants))
        for Name, File in Order:
            Result = _Run(File, Folder, f"{Name}_{Sample + 1}", Args.timeout)
            Observable = {Key: Result[Key] for Key in ("Values", "Progress", "Final_Output")}
            if Reference is None:
                Reference = Observable
            if Observable != Reference:
                Report["Validation"] = dict(Status="failed", Variant=Name, Sample=Sample, Expected=Reference, Actual=Observable)
                Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
                raise AssertionError("Module results or progress differ; inspect " + str(Destination))
            if Name != "Python" and Result["Native"].get("Native", 0) <= 0:
                raise AssertionError("Native module arithmetic did not execute: " + Name)
            if Name == "Parallel" and (Result["Native"].get("Parallel", 0) <= 0 or Result["Native"].get("Team") != Args.threads):
                raise AssertionError("Requested OpenMP team did not execute: " + repr(Result["Native"]))
            Report["Samples"].append(dict(Variant=Name, Sample=Sample + 1, **Result))
            Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
            print(Name + f" sample {Sample + 1}: {Result['Seconds']:.6f}s; result and progress match", flush=True)
    Medians = {Name: statistics.median(Item["Seconds"] for Item in Report["Samples"] if Item["Variant"] == Name) for Name, _ in Variants}
    Report["Medians"] = Medians
    Report["Speedup"] = {Name: Medians["Python"] / Medians[Name] for Name in ("Serial", "Parallel")}
    Report["Parallel_Over_Serial"] = Medians["Serial"] / Medians["Parallel"]
    Report["Validation"] = dict(Status="passed", Exact_Values=True, Progress_Compared_Excluding_Clock=True, Source_Unchanged=Source.read_bytes() == Original)
    if not Report["Validation"]["Source_Unchanged"]:
        raise AssertionError("Original source changed during benchmark")
    Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(Destination, flush=True)

if __name__ == "__main__":
    _Main()
