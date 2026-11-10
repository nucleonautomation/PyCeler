import importlib.util
import json
import math
import random
import statistics
import sys
import warnings
from pathlib import Path
from time import perf_counter_ns

def _Load(File, Name=None):
    Spec = importlib.util.spec_from_file_location(Name or File.stem, File)
    Module = importlib.util.module_from_spec(Spec)
    sys.modules[Spec.name] = Module
    Spec.loader.exec_module(Module)
    return Module

class _Fragmented_Input:
    def __init__(self, Size):
        self._Data = bytes(range(251)) * (Size // 251 + 1)
        self._Position = 0
        self._Requests = []

    def recv(self, Amount):
        self._Requests.append(Amount)
        End = self._Position + min(Amount, 113)
        Chunk = self._Data[self._Position:End]
        self._Position = End
        return Chunk

def _Cases(Item):
    if Item["Kind"] == "span":
        for Size in (16, 2048, 65536):
            Output = bytearray([11]) * Size
            if Item["Mode"] == "copy":
                Args = (bytes(range(251)) * (Size // 251 + 2), Output, 3, Size)
            else:
                Args = (Output, Size // 4, Size)[:Item["Arguments"]]
            yield "bytearray", Size, (Size,), Args
        return
    if Item["Kind"] == "receive":
        for Size in (16, 4096, 131072):
            Args = [_Fragmented_Input(Size), Size]
            if Item["Reader"] == 1:
                Args.reverse()
            yield "int", Size, (), tuple(Args)
        return
    if Item["Kind"] == "scalar":
        Depth = len(Item["Size_Arguments"])
        Sizes = sorted({max(1, round(Target ** (1 / Depth))) for Target in (16, 1024, 36864)}) if Depth > 1 else (4, 256, 32768)
        for Size in Sizes if Item["Arguments"] else (1,):
            Args = tuple(Size if Index in Item["Size_Arguments"] else 2 for Index in range(Item["Arguments"]))
            yield "int", Size ** Depth, (), Args
        return
    import numpy as Numpy
    if Item["Kind"] == "median":
        for Dtype in (Numpy.int8, Numpy.uint8, Numpy.int16, Numpy.uint16, Numpy.int32, Numpy.int64):
            for Side in (4, 24, 64):
                Input = (Numpy.arange(Side * Side) % 17).astype(Dtype).reshape(Side, Side)
                yield Input.dtype.str, Input.size, Input.shape, (Input, Numpy.zeros_like(Input))
        return
    if Item["Kind"] == "row_selection":
        for Dtype in (Numpy.int32, Numpy.int64, Numpy.float32, Numpy.float64):
            for Rows in (4, 256, 4096):
                A = ((Numpy.arange(Rows * 8) % 19) - 9).astype(Dtype).reshape(Rows, 8)
                O = Numpy.full(Rows, 255, dtype=Numpy.uint8)
                yield A.dtype.str, A.size, A.shape, (A, O, *(A.shape[Axis] for Axis in Item["Named"]))
        return
    if Item["Kind"] == "projection":
        for Dtype in (Numpy.float32, Numpy.float64):
            for Size in (16, 2048, 32768):
                Points = ((Numpy.arange(Size * 2) % 97) - 47).astype(Dtype).reshape(Size, 2)
                Args = [Points]
                if Item["Indirect"]:
                    Args.append(Numpy.arange(Size - 1, -1, -1, dtype=Numpy.int64))
                Args.extend((1.0, -2.0, 0.6, -0.8, 9.0))
                for Flag in Item["Gates"]:
                    if Flag:
                        Args.append(True)
                    Args.extend((Numpy.arange(Size, dtype=Numpy.int32) % 3, 1))
                if Item["Named_Size"]:
                    Args.append(Size)
                yield Points.dtype.str, Size, Points.shape, tuple(Args)
        return
    if Item["Kind"] == "stencil":
        for Dtype in (Numpy.uint8, Numpy.int16, Numpy.uint16, Numpy.int32):
            for Side in (8, 24, 64):
                Raw = ((Numpy.arange(Side * Side * 2) % 37) - (18 if Numpy.dtype(Dtype).kind == "i" else 0)).astype(Dtype).reshape(Side, 2 * Side)
                Frame = Raw[:, ::2]
                Mask = (Frame % 17 != 0)
                Output = Numpy.full(Frame.shape, -19, dtype=Numpy.int64)
                yield Frame.dtype.str, Frame.size, Frame.shape, (Frame, Mask, Output, Side, Side)
        return
    if Item["Kind"] == "count":
        for Dtype in (Numpy.int32, Numpy.int64, Numpy.float32, Numpy.float64):
            for Size in (16, 2048, 65536):
                Data = (Numpy.arange(Size) % 13).astype(Dtype)
                yield Data.dtype.str, Size, Data.shape, (Data, 4)
        return
    if "Byte_Copy" in Item:
        for Size in (16, 2048, 65536):
            Args = [None, None]
            Source, Output = Item["Byte_Copy"]
            Args[Source] = bytes((Index % 251 for Index in range(Size)))
            Args[Output] = bytearray(Size)
            yield "bytearray", Size, (Size,), tuple(Args)
    Dimensions = Item["Dimensions"]
    Dtypes = (Numpy.int32, Numpy.int64, Numpy.float32, Numpy.float64)
    if Item.get("Pixel_Dtypes"):
        Dtypes += (Numpy.int8, Numpy.uint8, Numpy.int16, Numpy.uint16)
    for Dtype in Dtypes:
        for Size in (16, 2048, 65536):
            Power = Size.bit_length() - 1
            Shape = tuple(2 ** (Power // Dimensions + (Index < Power % Dimensions)) for Index in range(Dimensions))
            Offset = 0 if Numpy.dtype(Dtype).kind == "u" else 4
            Args = tuple((Numpy.zeros(Shape, dtype=Dtype) if Index in Item.get("Outputs", ()) else ((Numpy.arange(Size) + Index) % 9 - Offset).astype(Dtype).reshape(Shape)) if Index in Item["Arrays"] else 2 for Index in range(Item["Arguments"]))
            if "Dimension_Args" in Item:
                Args = list(Args)
                for Position, Axis in Item["Dimension_Args"]:
                    Args[Position] = Shape[Axis]
                Args = tuple(Args)
            yield Numpy.dtype(Dtype).str, Size, Shape, Args

def _Factory_Cases(Spec):
    Paths = sys.path[:]
    try:
        File = Path(Spec["File"])
        sys.path.insert(0, str(File.parent))
        Module = _Load(File, "_Pyceler_Workload")
        Factory = getattr(Module, Spec["Factory"])
        Cases = []
        for Case in Factory():
            if len(Cases) == 128:
                raise ValueError("A workload factory may supply at most 128 cases per region")
            Cases.append(Case)
        return Cases
    finally:
        sys.path[:] = Paths

def _Representative_Cases(Item):
    Spec = Item.get("Representative_Workload")
    if Spec is None:
        return []
    Result = []
    for Index, Case in enumerate(_Factory_Cases(Spec)):
        if type(Case) is not dict or set(Case) - {"Args", "Label", "Holdout"}:
            raise ValueError("A workload case requires Args and optional Label/Holdout")
        Args = Case.get("Args")
        if type(Args) is not tuple or len(Args) != Item["Arguments"]:
            raise ValueError("Workload Args must be a tuple matching the isolated region arguments")
        Label, Holdout = Case.get("Label", str(Index)), Case.get("Holdout", False)
        if type(Label) is not str or type(Holdout) is not bool:
            raise ValueError("Workload Label must be text and Holdout must be boolean")
        if Item["Kind"] == "scalar":
            Values = [Args[Slot] for Slot in Item["Size_Arguments"]]
            if any(type(Value) is not int for Value in Values):
                raise ValueError("Scalar workload size arguments must be exact integers")
            Key, Size, Shape = "int", math.prod(max(0, Value) for Value in Values), ()
        else:
            Destination = (1 if Item["Mode"] == "copy" else 0) if Item["Kind"] == "span" else Item.get("Destination", 0)
            Value = Args[Destination]
            if type(Value) is bytearray:
                Key, Size, Shape = "bytearray", len(Value), (len(Value),)
            elif hasattr(Value, "dtype"):
                Key, Size, Shape = Value.dtype.str, Value.size, Value.shape
                if Item["Kind"] == "projection" and Item["Indirect"]:
                    Size = Args[1].shape[0]
            else:
                raise ValueError("Representative array workloads require a NumPy array or bytearray dispatch input")
        _Copy(Args)
        Result.append((Key, Size, Shape, Args, dict(Label=Label, Holdout=Holdout, Representative=True)))
    if not Result:
        raise ValueError("A workload factory must supply at least one case")
    return Result

def _Copy(Args):
    Memo = {}
    def _Duplicate(Value):
        if id(Value) in Memo:
            return Memo[id(Value)]
        if isinstance(Value, _Fragmented_Input):
            Result = _Fragmented_Input(0)
            Result._Data = Value._Data
        elif type(Value) is bytearray:
            Result = Value.copy()
        elif hasattr(Value, "dtype"):
            import numpy as Numpy
            if type(Value) is not Numpy.ndarray or Value.dtype.hasobject:
                raise ValueError("Selection supports plain numeric NumPy arrays")
            Owner = Value
            while isinstance(Owner.base, Numpy.ndarray):
                Owner = Owner.base
            if Owner.base is not None or not (Owner.flags.c_contiguous or Owner.flags.f_contiguous):
                raise ValueError("Selection cannot isolate this array's external storage")
            Key = ("storage", id(Owner))
            if Key not in Memo:
                Memo[Key] = Owner.copy(order="K")
            Offset = Value.__array_interface__["data"][0] - Owner.__array_interface__["data"][0]
            Result = Numpy.ndarray(Value.shape, dtype=Value.dtype, buffer=Memo[Key], offset=Offset, strides=Value.strides)
            if not Value.flags.writeable:
                Result.setflags(write=False)
        elif type(Value) is list:
            Result = []
            Memo[id(Value)] = Result
            Result.extend(_Duplicate(Item) for Item in Value)
        elif type(Value) is tuple:
            Result = tuple(_Duplicate(Item) for Item in Value)
        elif type(Value) is dict:
            Result = {}
            Memo[id(Value)] = Result
            Result.update((Key, _Duplicate(Item)) for Key, Item in Value.items())
        elif type(Value) in (int, float, bool, str, bytes, type(None)):
            Result = Value
        else:
            raise ValueError("Selection inputs require arrays, bytearrays or plain scalar/container values")
        Memo[id(Value)] = Result
        return Result
    return _Duplicate(Args)

def _Value(Value):
    if isinstance(Value, _Fragmented_Input):
        return type(Value), Value._Position, tuple(Value._Requests)
    if isinstance(Value, bytearray):
        return type(Value), bytes(Value)
    if hasattr(Value, "dtype"):
        return type(Value), Value.dtype.str, Value.shape, Value.tobytes()
    if type(Value) is float:
        import struct
        return type(Value), struct.pack("!d", Value)
    if type(Value) in (tuple, list):
        return type(Value), tuple(_Value(Item) for Item in Value)
    if type(Value) is dict:
        return type(Value), tuple((Key, _Value(Item)) for Key, Item in Value.items())
    return type(Value), Value

class _Probe_Timeout(Exception):
    pass

def _Preflight(Function, Args):
    Deadline = perf_counter_ns() + 500000000
    def _Limit(Frame, Event, Arg):
        if perf_counter_ns() > Deadline or any(type(Value) is int and Value.bit_length() > 65536 for Value in Frame.f_locals.values()):
            raise _Probe_Timeout()
        return _Limit
    sys.settrace(_Limit)
    try:
        Function(*Args)
    except _Probe_Timeout:
        return False
    except Exception:
        pass
    finally:
        sys.settrace(None)
    return True

def _Observe(Function, Args, Baseline_Name=None):
    Inputs = _Copy(Args)
    Fallback = False
    def _Profile(Frame, Event, Arg):
        nonlocal Fallback
        if Event == "call" and Frame.f_code.co_name == Baseline_Name and Frame.f_code.co_filename == "Reference.py":
            Fallback = True
    if Baseline_Name:
        sys.setprofile(_Profile)
    try:
        with warnings.catch_warnings(record=True) as Notices:
            warnings.simplefilter("always")
            try:
                Result = Function(*Inputs)
                Outcome = ("return", _Value(Result), tuple(Index for Index, Input in enumerate(Inputs) if Input is Result))
            except Exception as Error:
                Outcome = ("raise", type(Error), Error.args)
    finally:
        if Baseline_Name:
            sys.setprofile(None)
    return (Outcome, tuple(_Value(Arg) for Arg in Inputs), tuple((Notice.category, str(Notice.message)) for Notice in Notices)), Fallback

def _Measure(Function, Args, Calls):
    Inputs = [_Copy(Args) for Index in range(Calls)]
    Start = perf_counter_ns()
    for Values in Inputs:
        Function(*Values)
    return (perf_counter_ns() - Start) / Calls

def _Winner(Timings, Gain):
    from .Selection_Policy import _Candidate_Order
    Winner = "Python"
    for Name in _Candidate_Order(Timings):
        if Name not in Timings:
            continue
        Previous, Current = Timings[Winner]["Samples_Ns"], Timings[Name]["Samples_Ns"]
        if statistics.median(Previous) >= Gain * statistics.median(Current) and sum(Left >= Gain * Right for Left, Right in zip(Previous, Current)) >= math.ceil(0.75 * len(Current)):
            Winner = Name
    return Winner

def _Time(Functions, Args, Size, Gain):
    Samples = {Name: [] for Name in Functions}
    Calls = {}
    for Name, Function in Functions.items():
        Warmup = _Measure(Function, Args, 1)
        Calls[Name] = max(1, min(64, 65536 // max(Size, 1), int(150000 / max(Warmup, 1))))
    Random = random.Random(31)
    for Batch in range(10):
        Order = list(Functions)
        Random.shuffle(Order)
        for Name in Order:
            Samples[Name].append(_Measure(Functions[Name], Args, Calls[Name]))
        if Batch == 4:
            Medians = sorted(statistics.median(Values) for Values in Samples.values())
            Close = any(Right < Left * Gain * 1.1 for Left, Right in zip(Medians, Medians[1:]))
            if not Close and all(statistics.pstdev(Values) <= statistics.mean(Values) * 0.1 for Values in Samples.values()):
                break
    Timings = {}
    for Name, Values in Samples.items():
        Timings[Name] = dict(Samples_Ns=Values, Median_Ns=statistics.median(Values), Min_Ns=min(Values), Calls_Per_Batch=Calls[Name],
                             CV=statistics.pstdev(Values) / statistics.mean(Values), Speedup_Vs_Python=statistics.median(Samples["Python"]) / statistics.median(Values))
        if "Serial" in Samples:
            Timings[Name]["Speedup_Vs_Serial"] = statistics.median(Samples["Serial"]) / statistics.median(Values)
    return Timings

def _Check(Item, Modules, Threads, Gain, Teams=None):
    from .Selection_Policy import _Candidate_Order
    Name = Item["Probe"]
    Reference = getattr(Modules["Python"], Name)
    Cases = []
    Invalid = set()
    Inputs = [(Key, Size, Shape, Args, {}) for Key, Size, Shape, Args in _Cases(Item)]
    Inputs.extend(_Representative_Cases(Item))
    Deadline = perf_counter_ns() + int(Item.get("Tuning", {}).get("Budget_Seconds", 3600) * 1000000000)
    for Key, Size, Shape, Args, Metadata in Inputs:
        if perf_counter_ns() > Deadline:
            Cases.append(dict(Key=Key, Size=Size, Shape=Shape, Validation={"Python": "inconclusive: tuning budget exhausted"}, Timings={}, Winner="Python", **Metadata))
            continue
        if Item["Kind"] == "scalar" and not _Preflight(Reference, Args):
            Case = dict(Key=Key, Size=Size, Arguments=Args, Shape=Shape, Validation={"Python": "inconclusive: reference exceeded time budget"}, Timings={}, Winner="Python")
            Case.update(Metadata)
            Cases.append(Case)
            continue
        Expected, Ignored = _Observe(Reference, Args)
        Functions = {"Python": Reference}
        Status = {"Python": "valid"}
        for Variant in _Candidate_Order(Item["Eligible"]):
            if Variant not in Modules or Variant not in Item["Eligible"]:
                continue
            if Variant.startswith("OpenMP") and Key == "bytearray":
                Status[Variant] = "unsupported: byte buffer copy runs serially"
                continue
            if Variant.startswith("OpenMP") and (Teams or {}).get(Variant, Threads) < 2:
                Status[Variant] = "unsupported: OpenMP runtime supplied fewer than two threads"
                continue
            Function = getattr(Modules[Variant], Name)
            Actual, Fallback = _Observe(Function, Args, Name)
            if Actual != Expected:
                Invalid.add(Variant)
                Status[Variant] = "invalid: result, exception, identity, mutation or warnings differ"
            elif Fallback:
                Status[Variant] = "unsupported: runtime guard selected Python"
            else:
                Functions[Variant] = Function
                Status[Variant] = "valid"
        Timings = _Time(Functions, Args, Size, Gain) if Expected[0][0] == "return" else {}
        Arguments = [Size] if Item["Kind"] == "receive" else (list(Args) if Key == "int" else None)
        Case = dict(Key=Key, Size=Size, Arguments=Arguments, Shape=Shape, Validation=Status, Timings=Timings, Winner="Python")
        Case.update(Metadata)
        if Item.get("Profile") and Expected[0][0] == "return":
            import cProfile
            Profiler = cProfile.Profile()
            Profiler.runcall(Reference, *_Copy(Args))
            Entries = sorted(Profiler.getstats(), key=lambda Entry: -Entry.totaltime)[:8]
            Case["Profile"] = [dict(Function=Entry.code.co_name if hasattr(Entry.code, "co_name") else str(Entry.code),
                                    Calls=Entry.callcount, Total_Seconds=Entry.totaltime, Self_Seconds=Entry.inlinetime) for Entry in Entries]
        if Expected[0][0] == "raise":
            Case["Reason"] = "Reference raised " + Expected[0][1].__name__
        Cases.append(Case)
    for Case in Cases:
        Valid = {Name: Data for Name, Data in Case["Timings"].items() if Name not in Invalid}
        Case["Winner"] = _Winner(Valid, Gain)
    return Cases

def _Run(Request):
    from PyCeler.Selection_Environment import _Pyceler_Environment
    Spec = json.loads(Request.read_text(encoding="utf-8"))
    Directory = Request.parent
    Modules = {}
    Errors = {}
    Threads = 0
    Teams = {}
    Original_Teams = {}
    for Name, File in Spec["Modules"].items():
        try:
            Module = _Load(Path(File))
            if Name.startswith("OpenMP"):
                Original_Teams[Name] = Module._Probe_Threads()
                Teams[Name] = Module._Probe_Threads(int(Name.split("_")[1]) if "_" in Name else 0)
                Threads = max(Threads, Teams[Name])
            Modules[Name] = Module
        except (ImportError, OSError, ValueError) as Error:
            Errors[Name] = str(Error)
    Cases = _Check(Spec["Item"], Modules, Threads, Spec["Gain"], Teams)
    if any(Modules[Name]._Probe_Threads() != Count for Name, Count in Original_Teams.items()):
        raise RuntimeError("A candidate changed the caller's OpenMP thread configuration")
    Environment = dict(Host=_Pyceler_Environment(),
                       NumPy=getattr(sys.modules.get("numpy"), "__version__", None))
    (Directory / (Request.stem + ".result")).write_text(json.dumps(dict(Cases=Cases, Environment=Environment, Threads=Threads, Teams=Teams, Import_Errors=Errors)), encoding="utf-8")

if __name__ == "__main__":
    _Run(Path(sys.argv[1]))
