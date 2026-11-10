import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter_ns
from Benchmark_Structural import _Load, _Copy, _Observe
import Structural_Workloads

def _Main():
    Parser = argparse.ArgumentParser(description="Validate and interleave two existing structural binaries against Python on identical holdouts.")
    Parser.add_argument("before", type=Path)
    Parser.add_argument("after", type=Path)
    Args = Parser.parse_args()
    Before, After = Args.before.resolve(strict=True), Args.after.resolve(strict=True)
    Root = Path(__file__).resolve().parents[1]
    Run = Path(tempfile.mkdtemp(prefix="Structural_Comparison_", dir=Root / "Test_Run"))
    os.environ.update(OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
    Modules = dict(Python=_Load("Reference.Structural_Loops", Root / "Test" / "Structural_Loops.py"),
                   Before=_Load("Before.Structural_Loops", Before), After=_Load("After.Structural_Loops", After))
    Report = dict(Platform=platform.platform(), Python=sys.version, OpenMP_Threads=2, Cases=[],
                  Binaries={Name: dict(File=str(File), SHA256=hashlib.sha256(File.read_bytes()).hexdigest()) for Name, File in (("Before", Before), ("After", After))})
    Random = random.Random(73129)
    for Name in ("Fused_Maps", "Repeated_Scores", "Local_Values", "Versioned_Reads", "Column_First", "Invariant_Scale", "Temporary_Pipeline"):
        for Case in getattr(Structural_Workloads, Name)():
            if not Case["Holdout"]:
                continue
            Inputs = Case["Args"]
            Functions = {Key: getattr(Module, Name) for Key, Module in Modules.items()}
            Expected = _Observe(Functions["Python"], _Copy(Inputs))
            for Key, Function in Functions.items():
                assert _Observe(Function, _Copy(Inputs)) == Expected, (Name, Key, Case["Label"])
            Samples = {Key: [] for Key in Functions}
            for Repeat in range(17):
                Order = list(Functions)
                Random.shuffle(Order)
                for Key in Order:
                    Values = _Copy(Inputs)
                    Start = perf_counter_ns()
                    Functions[Key](*Values)
                    Duration = perf_counter_ns() - Start
                    if Repeat >= 2:
                        Samples[Key].append(Duration)
            Medians = {Key: statistics.median(Values) for Key, Values in Samples.items()}
            Result = dict(Function=Name, Label=Case["Label"], Size=Inputs[0].size, Status="valid", Samples_Ns=Samples, Median_Ns=Medians,
                          Speedup_Vs_Before=Medians["Before"] / Medians["After"], Speedup_Vs_Python=Medians["Python"] / Medians["After"])
            Report["Cases"].append(Result)
            print(json.dumps({Key: Value for Key, Value in Result.items() if Key != "Samples_Ns"}), flush=True)
    File = Run / "Results.json"
    File.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(File, flush=True)

if __name__ == "__main__":
    _Main()
