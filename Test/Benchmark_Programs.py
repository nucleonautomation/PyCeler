import json
import statistics
import subprocess
import sys
from pathlib import Path
# Measurement harness for programs.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from Benchmark_List_Grids import _Probe, _Snapshot

def Probe(File, Fields):
    Result = _Probe(File, Fields)
    Module = sys.modules[File.name.split(".")[0]]
    Random = vars(Module).get("random")
    if Random is not None and getattr(Random, "__name__", None) == "random":
        Result["Random_State"] = _Snapshot(Random.getstate())
    return Result

def Run(File, Fields, Timeout=900):
    Process = subprocess.run([sys.executable, "-I", "-B", __file__, "--probe", str(File), json.dumps(Fields)], capture_output=True, text=True, timeout=Timeout)
    if Process.returncode:
        raise RuntimeError(Process.stdout + Process.stderr)
    return json.loads(Process.stdout)

def Compare(Source, Binary, Fields, Destination, Repeats=3, Require_Native=True):
    Results = {"Python": [], "Native": []}
    for Batch in range(Repeats + 1):
        Order = (("Python", Source), ("Native", Binary)) if Batch % 2 == 0 else (("Native", Binary), ("Python", Source))
        for Mode, File in Order:
            Result = Run(File, Fields)
            assert Result["Error"] is None, Result
            if Mode == "Native" and Require_Native:
                assert sum(Value["Native_Elements"] for Value in Result["Native"].values()) > 0, Result
            Results[Mode].append(Result)
            print(Source.stem, Batch, Mode, Result["Seconds"], flush=True)
    assert len({(Value["State"], Value.get("Random_State")) for Rows in Results.values() for Value in Rows}) == 1, "Values, aliases or random state differ"
    Summary = {}
    for Mode, Rows in Results.items():
        Times = [Value["Seconds"] for Value in (Rows[1:] if Repeats else Rows)]
        Summary[Mode] = dict(Samples=Times, Median=statistics.median(Times), Minimum=min(Times), Maximum=max(Times), CV=statistics.pstdev(Times) / statistics.mean(Times))
    Summary["Speedup"] = Summary["Python"]["Median"] / Summary["Native"]["Median"]
    Report = dict(Summary=Summary, Runs=Results)
    Path(Destination).write_text(json.dumps(Report, indent=2))
    return Summary

if __name__ == "__main__":
    if sys.argv[1] == "--probe":
        print(json.dumps(Probe(Path(sys.argv[2]), json.loads(sys.argv[3]))))
