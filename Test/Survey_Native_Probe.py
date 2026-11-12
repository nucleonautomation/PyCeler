import hashlib
import json
import sys
from pathlib import Path

def _Pipeline(Module, Arguments, Parallel, Observe):
    Hooks = [Value for Name, Value in vars(Module).items() if Name.startswith("_Pyceler_") and Name.endswith("Dispatch_Stats") and callable(Value)]
    assert len(Hooks) == 1, "The compiled survey must expose dispatch telemetry"
    Statistics = Hooks[0]
    Bank = Module.Filter_Bank
    Observations = []
    def _Wrap(Name, Function):
        def _Call(*Args):
            Statistics(True, Reset=True)
            assert Statistics() == {}, (Name, "stale execution evidence")
            try:
                Result = Function(*Args)
            finally:
                Execution = dict(Statistics().get("Execution", {}))
                Statistics(False, Reset=True)
            assert Execution.get("Native_Entry") is True, (Name, Execution)
            assert Execution.get("Reason") == ("native_parallel" if Parallel else "native_serial"), (Name, Execution)
            assert Execution.get("Actual_Team") == (2 if Parallel else 1), (Name, Execution)
            Observations.append(dict(Function=Name, **Execution))
            return Result
        return _Call
    Module.Filter_Bank = tuple((Name, _Wrap(Name, Function)) for Name, Function in Bank)
    try:
        Actual = Observe(Module.Process_Survey, Arguments)
    finally:
        Module.Filter_Bank = Bank
        Statistics(False, Reset=True)
    assert [Entry["Function"] for Entry in Observations] == [Name for Name, Function in Bank]
    return Actual, Observations

def _Run():
    Source, Binary = map(Path, sys.argv[1:3])
    Parallel = bool(int(sys.argv[3]))
    sys.path.insert(0, str(Path(sys.argv[4]).resolve()))
    import numpy as Numpy
    from Survey_Verification import _Check_Constant_Survey, _Check_Filters, _Edges, _Equal, _Load, _Observe
    Before = Source.read_bytes()
    Modules = dict(Python=_Load("Reference_Survey", Source), Native=_Load(Binary.stem.split(".", 1)[0], Binary))
    _Check_Constant_Survey(Modules)
    Oracle_Cases = _Check_Filters(Modules)
    Edge_Cases = _Edges(Modules)
    Random = Numpy.random.default_rng(20261111)
    Pattern = Random.integers(-60, 61, (3, 33, 35), dtype=Numpy.int32)
    Pattern[0, ::11, ::5] = -128
    Cases = ((Numpy.full((2, 33, 35), 10, dtype=Numpy.int32), 10, 2), (Pattern, 13, 7))
    Observations = []
    for Volume, Threshold, Offset in Cases:
        Expected_Inputs = (Volume.copy(), Threshold, Offset, 1)
        Uninstrumented_Inputs = (Volume.copy(), Threshold, Offset, 1)
        Actual_Inputs = (Volume.copy(), Threshold, Offset, 1)
        Expected_Inputs[0].flags.writeable = Uninstrumented_Inputs[0].flags.writeable = Actual_Inputs[0].flags.writeable = False
        Expected = _Observe(Modules["Python"].Process_Survey, Expected_Inputs)
        Uninstrumented = _Observe(Modules["Native"].Process_Survey, Uninstrumented_Inputs)
        Actual, Entries = _Pipeline(Modules["Native"], Actual_Inputs, Parallel, _Observe)
        assert Expected[0][0] == "return", Expected
        _Equal(Expected, Uninstrumented, "uninstrumented full survey")
        _Equal(Expected, Actual, "native full survey")
        Observations.append(Entries)
    assert Source.read_bytes() == Before
    print(json.dumps(dict(Source_SHA256=hashlib.sha256(Before).hexdigest(), Constant_Survey=True,
                         Oracle_Filter_Cases=Oracle_Cases, Edge_Cases=len(Edge_Cases), Pipeline_Cases=len(Cases),
                         Uninstrumented_Pipeline_Cases=len(Cases),
                         Native_Filter_Calls=sum(len(Case) for Case in Observations),
                         Native_Filter_Names=[Name for Name, Function in Modules["Native"].Filter_Bank],
                         Pipeline_Observations=Observations)))

if __name__ == "__main__":
    _Run()
