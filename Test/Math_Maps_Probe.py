import importlib.util
import json
import math
import re
import signal
import sys
import threading
import time
import warnings
from pathlib import Path
import numpy as N

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Observe(Function, Source, Output):
    Error = None
    Result = None
    with warnings.catch_warnings(record=True) as Warnings:
        warnings.simplefilter("always")
        try:
            Result = Function(Source, Output)
        except Exception as Failure:
            Error = (type(Failure).__name__, Failure.args)
    return Error, [(Item.category.__name__, str(Item.message)) for Item in Warnings], Output.tobytes() if isinstance(Output, N.ndarray) else Output, Result is Output

def _Await_Progress(Output, Sentinel, Ready, Stopped, Audit):
    Started = time.perf_counter()
    Deadline = Started + 10.0
    Audit.update(Started=Started, Attempts=0, First=None, Last=None, Progress=None)
    Ready.set()
    while not Stopped.wait(0.001) and time.perf_counter() < Deadline:
        First, Last = float(Output[0]), float(Output[-1])
        Sample = dict(Elapsed=time.perf_counter() - Started, First=First, Last=Last)
        Audit["Attempts"] += 1
        if Audit["First"] is None:
            Audit["First"] = Sample
        Audit["Last"] = Sample
        if First != Sentinel and Last == Sentinel:
            Audit["Progress"] = Sample
            return True
    Audit.update(Stopped=Stopped.is_set(), Elapsed=time.perf_counter() - Started)
    return False

def _Fast_Changes(Statistics, Before):
    Current = {Name: Function() for Name, Function in Statistics.items()}
    return {Name: dict(Before=Before[Name], After=Value) for Name, Value in Current.items() if Value != Before[Name]}

def _Run(Binary, Source_File, Recipe_File):
    Native = _Load("Math_Coverage", Binary)
    Reference = _Load("Math_Reference", Source_File)
    Recipes = json.loads(Recipe_File.read_text(encoding="utf-8"))
    Statistics = next(Value for Name, Value in vars(Native).items() if Name.startswith("_Pyceler_") and Name.endswith("Dispatch_Stats") and callable(Value))
    Count = 0
    for Recipe in Recipes:
        Name = Recipe["Function"]
        Values = [1, 2, 3] if Recipe["Domain"] == "integer" else [1.25, 1.5, 2.0] if Recipe["Domain"] == "acosh" else [0.25, 0.5, 0.75]
        Data = N.array(Values, dtype=Recipe["Input"])
        Original = N.full(len(Data), 7, dtype=Recipe["Output"])
        Output = Original.copy()
        Expected = _Observe(getattr(Reference, Name), Data.copy(), Original)
        Statistics(True, Reset=True)
        Actual = _Observe(getattr(Native, Name), Data.copy(), Output)
        assert Actual == Expected, (Name, Actual, Expected)
        assert Statistics().get("Execution", {}).get("Native_Entry") is True, (Name, Statistics())
        Count += 1
    for Name, Data, Dtype in (
        ("Composite", N.array([0.1, 0.25, 1, 2], dtype="float64"), "float64"),
        ("Float32_Intermediates", N.array([0.1, 0.25, 1, 2], dtype="float32"), "float32"),
        ("Nested", N.array([[1, -2, 4], [9, 16, 25]], dtype="float64"), "float64"),
        ("Fraction", N.array([-0.0, 0.125, 1, 2], dtype="float64"), "int64"),
        ("Literal_Identity", N.array([-0.0, 0.0, -2, 3], dtype="float64"), "float64"),
        ("Infinite_Literal", N.array([-0.0, 0.0, -2, 3], dtype="float64"), "float64"),
        ("Collision", N.array([0, 1, 4, 9], dtype="float64"), "float64"),
        ("Real_factorial", N.array([1, 30, 100, 2], dtype="int64"), "float64"),
        ("Real_fsum", N.array([1e16, 1e-300, 0.0, -0.0], dtype="float64"), "float64"),
        ("Complex_sqrt", N.array([complex(-4, 0.0), complex(-4, -0.0), complex(0.0, -0.0)], dtype="complex128"), "complex128"),
        ("Real_sqrt", N.array([1, 4, -1, 9], dtype="float64"), "float64"),
        ("Real_exp", N.array([1, 2, 1000, 3], dtype="float64"), "float64"),
        ("Real_sin", N.array([-0.0, float("nan"), float("inf"), 2], dtype="float64"), "float64"),
        ("Numpy_sqrt", N.array([1, -1, float("nan"), 4], dtype="float64"), "float64"),
        ("Real_sqrt", N.array([1, 4, 9, 16], dtype="float64")[::2], ">f8"),
        ("Real_sqrt", N.array([], dtype="float64"), "float64"),
    ):
        Original = N.full(Data.shape, 7, dtype=Dtype)
        Output = Original.copy()
        Expected = _Observe(getattr(Reference, Name), Data.copy(), Original)
        Statistics(True, Reset=True)
        Actual = _Observe(getattr(Native, Name), Data.copy(), Output)
        assert Actual == Expected, (Name, Actual, Expected)
        assert Statistics().get("Execution", {}).get("Native_Entry") is True, (Name, Statistics())
        Count += 1
    for Name in ("Composite", "Real_sqrt", "Literal_Identity"):
        First = N.array([0.25, 0.5, 1, 4], dtype="float64")
        Second = First.copy()
        Expected = _Observe(getattr(Reference, Name), First, First)
        Statistics(True, Reset=True)
        Actual = _Observe(getattr(Native, Name), Second, Second)
        assert Actual == Expected, (Name, "alias", Actual, Expected)
        assert Statistics()["Execution"]["Native_Entry"]
    Identity_Cases = 0
    for Name, Attribute, Operation in (("Identity_Finite", "Literal_Finite", "copysign"), ("Identity_Zero", "Literal_Zero", "copysign"), ("Identity_Infinite", "Literal_Infinite", "copysign"), ("Identity_Tuple", "Literal_Tuple", "prod")):
        Original_Operation = getattr(math, Operation)
        try:
            for Fallback in (False, True):
                Observations = []
                for Module in (Reference, Native):
                    Expected_Literal = getattr(Module, Attribute)
                    if Operation == "prod":
                        def Inspect_Literal(Values, *, start=1):
                            return 1.0 if Values is Expected_Literal else 0.0
                    else:
                        def Inspect_Literal(Value, Sign):
                            return 1.0 if Sign is Expected_Literal else 0.0
                    setattr(math, Operation, Inspect_Literal)
                    Data = [1.0, 2.0] if Fallback else N.array([1.0, 2.0])
                    Output = [7.0, 7.0] if Fallback else N.array([7.0, 7.0])
                    Statistics(True, Reset=True)
                    Observation = _Observe(getattr(Module, Name), Data, Output)
                    assert Observation[0] is None and all(Value == 1.0 for Value in Output), (Name, Fallback, Observation, Output)
                    Observations.append(Observation)
                assert Observations[0] == Observations[1], (Name, Fallback, Observations)
                assert Statistics()["Execution"]["Native_Entry"] is not Fallback, (Name, Fallback, Statistics())
                Identity_Cases += 1
        finally:
            setattr(math, Operation, Original_Operation)
    Original_Sqrt = math.sqrt
    try:
        Traces = []
        for Module in (Reference, Native):
            Events = []
            def Changed(Value):
                Events.append(("changed", float(Value)))
                return 11.0
            def Initial(Value):
                Events.append(("initial", float(Value)))
                math.sqrt = Changed
                return Original_Sqrt(Value)
            math.sqrt = Initial
            Statistics(True, Reset=True)
            Data = N.array([1, 4, 9], dtype="float64")
            Output = N.zeros(3)
            Observation = _Observe(Module.Real_sqrt, Data, Output)
            Traces.append((Events, Observation))
        assert Traces[0] == Traces[1], Traces
        assert Statistics()["Execution"]["Native_Entry"]
    finally:
        math.sqrt = Original_Sqrt
    Original_Sin = math.sin
    Fast_Statistics = {Name: Value for Name, Value in vars(Native).items() if re.fullmatch(r"_Pyceler_X*Fast_\d+_Stats", Name) and callable(Value)}
    assert Fast_Statistics, ("No unboxed math statistics discovered", tuple(Name for Name in vars(Native) if Name.endswith("Stats")))
    Fast_Before = {Name: Function() for Name, Function in Fast_Statistics.items()}
    Mutation_Audit = dict(Fast_Hooks=len(Fast_Statistics))
    Mutated = threading.Event()
    Ready = threading.Event()
    Stopped = threading.Event()
    def Replace_Sin():
        if _Await_Progress(Output, 0.0, Ready, Stopped, Mutation_Audit):
            math.sin = lambda Value: 7.0
            Mutated.set()
    Worker = threading.Thread(target=Replace_Sin)
    try:
        Data = N.full(1000000, 0.25)
        Output = N.zeros_like(Data)
        Worker.start()
        assert Ready.wait(5), "Mutation observer did not become ready."
        time.sleep(0.03)
        Mutation_Audit.update(Call_Started=time.perf_counter(), Frames_Before=len(sys._current_frames()))
        Native.Real_sin(Data, Output)
        Mutation_Audit["Call_Finished"] = time.perf_counter()
        Stopped.set()
        Worker.join(timeout=5)
        Mutation_Audit.update(Fast_Changes=_Fast_Changes(Fast_Statistics, Fast_Before), Output_First=float(Output[0]), Output_Last=float(Output[-1]), Execution=Statistics().get("Execution"))
        assert not Mutation_Audit["Fast_Changes"], ("The competing Python observer did not disable unboxed math", Mutation_Audit)
        assert Mutated.is_set() and N.any(Output == 7.0), ("Observer did not replace the binding during native progress", Mutation_Audit)
        Done = int(N.count_nonzero(Output != 7.0))
        assert 0 < Done < len(Output), ("mutation prefix", Done)
        assert N.all(Output[:Done] == Original_Sin(0.25)) and N.all(Output[Done:] == 7.0), "Binding replacement did not preserve the original prefix and replacement suffix."
        Mutation_Prefix = Done
    finally:
        Stopped.set()
        Worker.join(timeout=5)
        assert not Worker.is_alive(), "Mutation observer failed to stop."
        math.sin = Original_Sin
    Previous_Handler = signal.getsignal(signal.SIGINT)
    Requested = threading.Event()
    Signal_Audit = dict(Fast_Hooks=len(Fast_Statistics))
    Ready = threading.Event()
    Stopped = threading.Event()
    def Interrupt(Signum, Frame):
        raise RuntimeError("ordered math interrupted")
    def Send_Interrupt():
        if _Await_Progress(Output, 7.0, Ready, Stopped, Signal_Audit):
            Requested.set()
            signal.raise_signal(signal.SIGINT)
    Interrupt_Worker = threading.Thread(target=Send_Interrupt)
    try:
        signal.signal(signal.SIGINT, Interrupt)
        Data = N.full(1000000, 0.25)
        Output = N.full_like(Data, 7.0)
        Interrupt_Worker.start()
        assert Ready.wait(5), "Signal observer did not become ready."
        time.sleep(0.03)
        Signal_Audit.update(Call_Started=time.perf_counter(), Frames_Before=len(sys._current_frames()))
        Observation = _Observe(Native.Real_sin, Data, Output)
        Signal_Audit["Call_Finished"] = time.perf_counter()
        Stopped.set()
        Interrupt_Worker.join(timeout=5)
        Signal_Audit.update(Fast_Changes=_Fast_Changes(Fast_Statistics, Fast_Before), Output_First=float(Output[0]), Output_Last=float(Output[-1]), Execution=Statistics().get("Execution"))
        assert not Signal_Audit["Fast_Changes"], ("The signal observer did not disable unboxed math", Signal_Audit)
        assert Requested.is_set(), ("Signal observer did not observe native progress", Signal_Audit)
        assert Observation[0] == ("RuntimeError", ("ordered math interrupted",)), Observation[:2]
        Done = int(N.count_nonzero(Output != 7.0))
        assert 0 < Done < len(Output), ("cancellation prefix", Done)
        assert N.all(Output[:Done] == Original_Sin(0.25)) and N.all(Output[Done:] == 7.0), "Cancellation did not preserve the committed prefix."
        Cancellation_Prefix = Done
    finally:
        Stopped.set()
        Interrupt_Worker.join(timeout=5)
        assert not Interrupt_Worker.is_alive(), "Signal observer failed to stop."
        signal.signal(signal.SIGINT, Previous_Handler)
    for Module in (Reference, Native):
        Module.range = lambda Count: iter((0, 2))
    try:
        First, Second = N.full(3, 7.0), N.full(3, 7.0)
        Data = N.array([1, 4, 9], dtype="float64")
        Expected = _Observe(Reference.Real_sqrt, Data, First)
        Statistics(True, Reset=True)
        Actual = _Observe(Native.Real_sqrt, Data, Second)
        assert Actual == Expected, ("range replacement", Actual, Expected)
        assert Statistics()["Execution"]["Native_Entry"]
    finally:
        del Reference.range
        del Native.range
    for Data, Output in (([1, 4, 9], [7, 7, 7]), (N.array([1, 4, 9], dtype=object), N.array([7, 7, 7], dtype=object))):
        Original = Output.copy()
        Expected = _Observe(Reference.Real_sqrt, Data, Original)
        Statistics(True, Reset=True)
        Actual = _Observe(Native.Real_sqrt, Data, Output)
        if isinstance(Output, N.ndarray):
            assert N.array_equal(Output, Original)
            assert Actual[:2] == Expected[:2] and Actual[-1] == Expected[-1]
        else:
            assert Actual == Expected
        assert Statistics()["Execution"]["Native_Entry"] is False, Statistics()
    Statistics(False)
    return dict(Functions=len(Recipes), Native_Cases=Count, Aliasing_Cases=3, Dynamic_Bindings=3, Signal_Cases=1, Literal_Identity_Cases=Identity_Cases, Fallbacks=2, Mutation_Prefix=Mutation_Prefix, Cancellation_Prefix=Cancellation_Prefix, Mutation_Observer=Mutation_Audit, Signal_Observer=Signal_Audit)

if __name__ == "__main__":
    print(json.dumps(_Run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))))
