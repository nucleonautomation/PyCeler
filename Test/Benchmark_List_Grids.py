import contextlib
import hashlib
import importlib.util
import io
import json
import statistics
import struct
import subprocess
import sys
from pathlib import Path
from time import perf_counter
# Measurement harness for nested list updates and object identity.
def _Snapshot(Values):
    Memo, Nodes = {}, []
    def Visit(Value):
        if id(Value) in Memo:
            return Memo[id(Value)]
        Index = len(Nodes)
        Memo[id(Value)] = Index
        Nodes.append(None)
        if type(Value) in (list, tuple):
            Record = type(Value).__name__, [Visit(Part) for Part in Value]
        elif type(Value) is dict:
            Record = "dict", [(Key, Visit(Part)) for Key, Part in sorted(Value.items())]
        elif type(Value) is float:
            Record = "float", struct.pack("!d", Value).hex()
        else:
            Record = type(Value).__name__, repr(Value)
        Nodes[Index] = Record
        return Index
    Visit(Values)
    return hashlib.sha256(json.dumps(Nodes, separators=(",", ":")).encode()).hexdigest()

def _Probe(File, Fields):
    Spec = importlib.util.spec_from_file_location(File.name.split(".")[0], File)
    Module = importlib.util.module_from_spec(Spec)
    sys.modules[Spec.name] = Module
    Error, Output = None, io.StringIO()
    Start = perf_counter()
    with contextlib.redirect_stdout(Output):
        try:
            Spec.loader.exec_module(Module)
        except Exception as Failure:
            Error = type(Failure).__name__, str(Failure)
    Duration = perf_counter() - Start
    Values = {Name: getattr(Module, Name) for Name in Fields if hasattr(Module, Name)}
    Native = {Name: Value() for Name, Value in vars(Module).items() if Name.startswith("_Pyceler_Fast_") and Name.endswith("Stats")}
    return dict(State=_Snapshot(Values), Error=Error, Native=Native, Seconds=getattr(Module, "elapsed", Duration), Import_Seconds=Duration, Output=Output.getvalue())

def Main():
    if sys.argv[1] == "--probe":
        print(json.dumps(_Probe(Path(sys.argv[2]), json.loads(sys.argv[3]))))
        return
    Source, Binary, Destination = map(Path, sys.argv[1:4])
    Fields = json.loads(sys.argv[4])
    Results = {"Python": [], "Native": []}
    for Batch in range(4):
        for Name, File in (("Python", Source), ("Native", Binary)) if Batch % 2 == 0 else (("Native", Binary), ("Python", Source)):
            Result = subprocess.run([sys.executable, "-I", "-B", __file__, "--probe", str(File), json.dumps(Fields)], capture_output=True, text=True, timeout=180)
            if Result.returncode:
                raise RuntimeError(Result.stdout + Result.stderr)
            Report = json.loads(Result.stdout)
            assert Report["Error"] is None, Report
            if Name == "Native":
                assert sum(Stats["Native_Elements"] for Stats in Report["Native"].values()) > 0, Report
            Results[Name].append(Report)
            print(Name, Batch, Report["Seconds"], flush=True)
    assert len({Item["State"] for Rows in Results.values() for Item in Rows}) == 1, "Results, mutations or aliases differ"
    Summary = {}
    for Name, Rows in Results.items():
        Samples = [Row["Seconds"] for Row in Rows[1:]]
        Summary[Name] = dict(Samples=Samples, Median=statistics.median(Samples), Minimum=min(Samples), Maximum=max(Samples), CV=statistics.pstdev(Samples) / statistics.mean(Samples))
    Summary["Speedup"] = Summary["Python"]["Median"] / Summary["Native"]["Median"]
    Destination.write_text(json.dumps(dict(Summary=Summary, Runs=Results), indent=2), encoding="utf-8")
    print(json.dumps(Summary, indent=2))

if __name__ == "__main__":
    Main()
