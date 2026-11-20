import importlib.util
import json
import math
import random
import statistics
import sys
import warnings
from pathlib import Path
from time import perf_counter_ns
from .Selection_Inputs import _Copy, _Value, _Storage_Bytes, _Isolation_Limit, _Fragmented_Input, _Probe_Resource
# Validate outcomes before timing isolated calls; native counters prevent fallback from masquerading as speedup.
def _Load(File, Name=None):
    Spec = importlib.util.spec_from_file_location(Name or File.stem, File)
    Module = importlib.util.module_from_spec(Spec)
    sys.modules[Spec.name] = Module
    Spec.loader.exec_module(Module)
    return Module

def _Range_Span(Item, Namespace, Expression=None):
    Context = dict(__builtins__=dict(__import__=__import__, range=range, len=len, int=int, float=float, abs=abs, min=min, max=max))
    for Import in Item.get('Math_Imports', ()):
        exec(Import, Context)
    for Name, Source in Item.get('Helper_Sources', ()):
        exec(Source, Context)
    Context.update(Namespace)
    State = random.getstate()
    try:
        return eval(Item['Range'] if Expression is None else Expression, Context)
    finally:
        random.setstate(State)

def _Cases(Item):
    yield from _Primary_Cases(Item)
    if Item.get('List_Alternative'):
        Alternative = dict(Item['List_Alternative'], Math_Imports=Item.get('Math_Imports', ()), Helper_Sources=Item.get('Helper_Sources', ()))
        Kinds = ('float', 'integer') if Alternative['Integer'] else (Alternative['Read_Kind'],)
        for Kind in Kinds:
            for Key, Size, Shape, Args in _Primary_Cases(dict(Alternative, Read_Kind=Kind)):
                yield 'list_' + Kind, Size, Shape, Args

def _Primary_Cases(Item):
    if Item['Kind'] == 'indexed_filter':
        import numpy as Numpy
        Width = max(Item['Columns']) + 1
        for Size in (1, 2, 4, 16, 128, 1024):
            Values = Numpy.arange((Size + 1) * Width, dtype=Numpy.float64).reshape(-1, Width) % 7
            yield 'int', Size, (Size,), (list(range(1, Size + 1)), Values, 0, 3.5, [])
        return
    if Item['Kind'] == 'array_region':
        import numpy as Numpy
        Depth = max(1, max(sum(Axis is None for Axis in Item.get('Array_Axes', {}).get(Name, (None,) * Value[1])) for Name, Value in Item['Buffers'].items()))
        Sizes = (8, 128, 512, 2048, 8192, 65536) if Depth == 1 else tuple(sorted({max(1, int(Target ** (1 / Depth))) for Target in (256, 4096, 16384, 131072)}))
        for Side in Sizes:
            Namespace = {}
            for Name in Item['Names']:
                if Name in Item['Buffers']:
                    Dimensions = Item['Buffers'][Name][1]
                    Padding = Item.get('Array_Padding', {}).get(Name, (0,) * Dimensions)
                    Shape = tuple(Side + Padding[Index] if Axis is None else Axis for Index, Axis in enumerate(Item.get('Array_Axes', {}).get(Name, (None,) * Dimensions)))
                    if Name in Item['Array_Rows']:
                        Shape = (Side, Item['Array_Rows'][Name])
                    Size = Numpy.prod(Shape).item()
                    if Item['Buffers'][Name][2] == 'integer':
                        Namespace[Name] = (Numpy.arange(Size, dtype=Numpy.int64) % (Side + max(Padding))).reshape(Shape) if Name in Item['Reads'] else Numpy.zeros(Shape, dtype=Numpy.int64)
                    else:
                        Namespace[Name] = (((Numpy.arange(Size, dtype=Numpy.float64) % 13) + 1) * 0.01).reshape(Shape) if Name in Item['Reads'] else Numpy.zeros(Shape, dtype=Numpy.float64)
                else:
                    Namespace[Name] = {'size': Side, 'step': 3, 'zero': 0}[Item['Probe_Inputs'].get(Name, 'size')] if Item['Input_Types'][Name] == 'integer' else 0.125
            Span = _Range_Span(Item, Namespace)
            yield 'int', len(Span), (Side,), tuple(Namespace[Name] for Name in Item['Names'])
        return
    if Item["Kind"] == "numeric_region":
        Depth = max(Value[1] for Value in Item["Buffers"].values())
        if Depth > 3:
            Sizes = tuple(sorted({1, max(1, int(128 ** (1 / Depth))), max(1, int(32768 ** (1 / Depth)))}))
        elif Depth == 3:
            Sizes = (4, 12, 32)
        elif Depth == 2:
            Sizes = (8, 32, 128)
        elif not Item.get("Flat"):
            Sizes = (8, 32, 128, 512, 2048)
        else:
            Sizes = (8, 128, 512, 2048, 8192, 65536)
        for Side in Sizes:
            Namespace = {}
            for Name in Item["Names"]:
                if Name in Item["Buffers"]:
                    Slot, Dimensions, Kind = Item["Buffers"][Name]
                    Value = lambda Index: (Index % 5 if Item.get("Read_Kind") == "integer" else (Index * 7 + 1) * 0.01) if Name in Item["Reads"] else False if Kind == "boolean" else 0 if Kind == "integer" else 0.0
                    def Array(Depth, Offset=0):
                        return [Value(Offset + Index) if Depth == 1 else Array(Depth - 1, (Offset + Index) * Side) for Index in range(Side)]
                    Namespace[Name] = Array(Dimensions)
                else:
                    Namespace[Name] = ({"size": Side, "step": 3, "zero": 0}[Item.get("Probe_Inputs", {}).get(Name, "size")] if Item["Input_Types"][Name] == "integer" else 0.125)
            Span = _Range_Span(Item, Namespace)
            yield "int", len(Span), (Side,), tuple(Namespace[Name] for Name in Item["Names"])
        return
    if Item["Kind"] == "list_grid":
        for Side in (8, 32, 128):
            Namespace = {Name: ([[0.0 if Name == Item["Output"] else (Row * 7 + Column * 3 + 1) * 0.001 for Column in range(Side)] for Row in range(Side)] if Name in Item["Grids"] else Side) for Name in Item["Names"]}
            Rows, Columns = (_Range_Span(Item, Namespace, Expression) for Expression in Item["Ranges"])
            yield "int", len(Rows) * len(Columns), (Side, Side), tuple(Namespace[Name] for Name in Item["Names"])
        return
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
        if "Size_Plan" in Item:
            from .Engine import _Scalar_Size_Cases
            yield from _Scalar_Size_Cases(Item)
            return
        Depth = len(Item["Size_Arguments"])
        Sizes = sorted({max(1, round(Target ** (1 / Depth))) for Target in (16, 1024, 36864)}) if Depth > 1 else (4, 256, 32768)
        if Item.get("Float_Arguments") and Depth == 1:
            Sizes = (4, 16, 64, 256, 32768)
        if Item.get("Span_Maximum") is not None:
            Sizes = sorted({min(Size, Item["Span_Maximum"]) for Size in Sizes})
        Steps = (1, -1, 2, -3) if "Range_Step_Argument" in Item else (Item.get("Range_Step", 1),)
        for Step in Steps:
            Span_Maximum = Item.get("Range_Period")
            Span_Maximum = Span_Maximum // math.gcd(Step, Span_Maximum) if Span_Maximum is not None else None
            Span_Sizes = sorted({min(Size, Span_Maximum) for Size in Sizes}) if Span_Maximum is not None else Sizes
            for Size in Span_Sizes if Item["Arguments"] else (1,):
                Args = tuple(Step if Index == Item.get("Range_Step_Argument") else Size * Step if Index in Item["Size_Arguments"] else 0 if Index == Item.get("Range_Start_Argument") else 2.0 if Index in Item.get("Float_Arguments", ()) else 2 for Index in range(Item["Arguments"]))
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
    if Item.get("Unboxed_Math"):
        Dtypes = (Numpy.float64, *(Dtype for Dtype in Dtypes if Dtype is not Numpy.float64))
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

def _Factory_Cases(Spec, Deadline=None):
    Paths = sys.path[:]
    try:
        File = Path(Spec["File"])
        sys.path.insert(0, str(File.parent))
        Module = _Load(File, "_Pyceler_Workload")
        Factory = getattr(Module, Spec["Factory"])
        Cases = []
        for Case in Factory():
            _Budget(Deadline)
            if len(Cases) == 128:
                raise ValueError("A workload factory may supply at most 128 cases per region")
            Cases.append(Case)
        return Cases
    finally:
        sys.path[:] = Paths

def _Representative_Cases(Item, Deadline=None):
    Spec = Item.get("Representative_Workload")
    if Spec is None:
        return []
    Result = []
    for Index, Case in enumerate(_Factory_Cases(Spec, Deadline)):
        if type(Case) is not dict or set(Case) - {"Args", "Label", "Holdout"}:
            raise ValueError("A workload case requires Args and optional Label/Holdout")
        Args = Case.get("Args")
        if type(Args) is not tuple or len(Args) != Item["Arguments"]:
            raise ValueError("Workload Args must be a tuple matching the isolated region arguments")
        Label, Holdout = Case.get("Label", str(Index)), Case.get("Holdout", False)
        if type(Label) is not str or type(Holdout) is not bool:
            raise ValueError("Workload Label must be text and Holdout must be boolean")
        if Item['Kind'] == 'indexed_filter':
            if type(Args[0]) is not list:
                raise ValueError('An indexed filter workload requires a candidate list')
            Key, Size, Shape = 'int', len(Args[0]), (len(Args[0]),)
        elif Item['Kind'] in ('array_region', 'numeric_region'):
            Namespace = dict(zip(Item['Names'], Args))
            Span = _Range_Span(Item, Namespace)
            if type(Span) is not range:
                raise ValueError('Numeric workload bounds must produce an exact range')
            Key, Size, Shape = 'int', len(Span), ()
            Alternative = Item.get('List_Alternative')
            if Alternative and all(type(Namespace[Name]) is list for Name in Alternative['Buffers']):
                Kind = Alternative['Read_Kind']
                if Alternative['Reads']:
                    Cell = Namespace[Alternative['Reads'][0]]
                    for Axis in range(Alternative['Buffers'][Alternative['Reads'][0]][1]):
                        if type(Cell) is not list or not Cell:
                            break
                        Cell = Cell[0]
                    Kind = 'integer' if type(Cell) in (int, bool) else 'float'
                Key = 'list_' + Kind
        elif Item["Kind"] == "scalar":
            Values = [Args[Slot] for Slot in Item["Size_Arguments"]]
            if any(type(Value) is not int for Value in Values):
                raise ValueError("Scalar workload size arguments must be exact integers")
            Key, Size, Shape = "int", math.prod(max(0, Value) for Value in Values), ()
            if "Size_Plan" in Item:
                from .Engine import _Scalar_Workload_Size
                Size = _Scalar_Workload_Size(Item["Size_Plan"], Args)
            elif "Range_Start_Argument" in Item:
                Begin, End = Args[Item["Range_Start_Argument"]], Args[0]
                Step = Args[Item["Range_Step_Argument"]] if "Range_Step_Argument" in Item else Item.get("Range_Step", 1)
                if type(Begin) is not int:
                    raise ValueError("Scalar workload range starts must be exact integers")
                if type(Step) is not int or Step == 0:
                    raise ValueError("Scalar workload range strides must be nonzero exact integers")
                Size = max(0, 1 + ((End - 1 - Begin) // Step if Step > 0 else (Begin - 1 - End) // -Step))
        else:
            Destination = (1 if Item["Mode"] == "copy" else 0) if Item["Kind"] == "span" else Item.get("Destination", 0)
            Value = Args[Destination]
            if type(Value) is list and Item.get('List_Alternative'):
                Alternative = Item['List_Alternative']
                Namespace = dict(zip(Alternative['Names'], Args))
                Span = _Range_Span(Item, Namespace, Alternative['Range'])
                if type(Span) is not range:
                    raise ValueError('List workload bounds must produce an exact range')
                Kind = Alternative['Read_Kind']
                if Alternative['Reads']:
                    Cell = Namespace[Alternative['Reads'][0]]
                    for Axis in range(Alternative['Buffers'][Alternative['Reads'][0]][1]):
                        if type(Cell) is not list or not Cell:
                            break
                        Cell = Cell[0]
                    Kind = 'integer' if type(Cell) in (int, bool) else 'float'
                Key, Size, Shape = 'list_' + Kind, len(Span), ()
            elif type(Value) is bytearray:
                Key, Size, Shape = "bytearray", len(Value), (len(Value),)
            elif hasattr(Value, "dtype"):
                Key, Size, Shape = Value.dtype.str, Value.size, Value.shape
                if Item["Kind"] == "projection" and Item["Indirect"]:
                    Size = Args[1].shape[0]
            else:
                raise ValueError("Representative array workloads require a NumPy array or bytearray dispatch input")
        Result.append((Key, Size, Shape, Args, dict(Label=Label, Holdout=Holdout, Representative=True)))
    if not Result:
        raise ValueError("A workload factory must supply at least one case")
    return Result

class _Probe_Timeout(Exception):
    pass

def _Budget(Deadline):
    if Deadline is not None and perf_counter_ns() >= Deadline:
        raise _Probe_Timeout("Validation and measurement budget exhausted")
# Bound speculative validation so pathological arithmetic cannot consume the complete worker budget.
def _Preflight(Function, Args, Deadline=None, Random_State=False):
    Deadline = min(Deadline or math.inf, perf_counter_ns() + 500000000)
    Inputs = _Copy(Args)  # Isolate each candidate from mutations made by the reference or earlier candidates.
    Previous = sys.gettrace()
    State = random.getstate() if Random_State else None
    Events = 7
    def _Limit(Frame, Event, Arg):
        nonlocal Events
        Events += 1
        if Events & 7:
            return _Limit
        if perf_counter_ns() > Deadline or any(type(Value) is int and Value.bit_length() > 65536 for Value in Frame.f_locals.values()):
            raise _Probe_Timeout()
        return _Limit
    sys.settrace(_Limit)
    try:
        Function(*Inputs)
    except _Probe_Timeout:  # An exhausted budget is inconclusive evidence, not a correctness or speedup pass.
        return False
    except Exception:
        pass
    finally:
        sys.settrace(Previous)
        if Random_State:
            random.setstate(State)
    return True
# Compare results, mutations, types, identities and exceptions; successful compilation alone is insufficient.
def _Observe(Function, Args, Baseline_Name=None, Observation=None, Random_State=False):
    Inputs = _Copy(Args)
    Random_Before = random.getstate() if Random_State else None  # RNG state is observable output and must be compared and restored.
    Fallback = False
    Statistics = next((Value for Name, Value in getattr(Function, "__globals__", {}).items() if Name.startswith("_Pyceler_") and Name.endswith("Region_Stats") and callable(Value)), None)
    Before = Statistics() if Statistics else (0, 0)
    Reduction = next((Value for Name, Value in getattr(Function, "__globals__", {}).items() if Name.startswith("_Pyceler_") and Name.endswith("Reduction_Stats") and callable(Value)), None)
    Previous = Reduction() if Reduction else None
    Module = next((Value for Name, Value in getattr(Function, "__globals__", {}).items() if Name.startswith("_Pyceler_") and Name.endswith("Module_Stats") and callable(Value)), None)
    Module_Before = Module() if Module else None
    Dispatch = next((Value for Name, Value in getattr(Function, "__globals__", {}).items() if Name.startswith("_Pyceler_") and Name.endswith("Dispatch_Stats") and callable(Value)), None) if Observation is not None else None
    Execution, Guards, Totals = {}, {}, {}
    if Dispatch:
        Dispatch(True, Reset=True)
    def _Profile(Frame, Event, Arg):
        nonlocal Fallback
        if Event == "call" and Frame.f_code.co_name == Baseline_Name and Frame.f_code.co_filename == "Reference.py":
            Fallback = True
    Profiled = bool(Baseline_Name and Dispatch is None)
    if Profiled:
        sys.setprofile(_Profile)
    try:
        with warnings.catch_warnings(record=True) as Notices:
            warnings.simplefilter("always")
            try:
                Result = Function(*Inputs)
            except Exception as Error:
                Outcome = ("raise", type(Error), _Value((Inputs, Error.args)))
            else:
                Outcome = ("return", _Value(Result), _Value((Inputs, Result)))
    finally:
        if Random_State:
            Random_After = random.getstate()
            random.setstate(Random_Before)
        if Profiled:
            sys.setprofile(None)
        if Dispatch:
            Dispatch_Report = Dispatch()
            Execution = Dispatch_Report.get("Execution", {})
            Guards = Dispatch_Report.get("Guard", {})
            Totals = Dispatch_Report.get('Totals', {})
            Dispatch(False)
    Region_Current = Statistics() if Statistics else (0, 0)
    Region_Entered = Region_Current[0] > Before[0]
    Current = Reduction() if Reduction else None
    Reduction_Entered = Reduction is not None and any(Current.get(Key, 0) > Previous.get(Key, 0) for Key in ("Serial_Calls", "Parallel_Calls"))
    Module_Current = Module() if Module else None
    Module_Entered = Module is not None and Module_Current.get("Native", 0) > Module_Before.get("Native", 0)
    Module_Fallback = Module is not None and Module_Current.get("Fallbacks", 0) > Module_Before.get("Fallbacks", 0)
    Accumulated_Entry = Totals.get('Native_Entries', 0) > 0
    Missing_Execution = bool(Dispatch and not Execution and not (Module_Entered or Reduction_Entered or Region_Entered or Accumulated_Entry))
    Fallback = Fallback or Region_Current[1] > Before[1] or Module_Fallback or Execution.get("Reason") == "python_fallback" or Missing_Execution
    if Observation is not None:
        Observation.update(Python_Fallback=bool(Fallback), Native_Entry=None, Actual_Team=None)
        if Execution:
            Observation.update(Native_Entry=Execution.get("Native_Entry"), Actual_Team=Execution.get("Actual_Team"),
                               Actual_Mode=Execution.get("Reason"), Fallback_Reason=Guards.get("Reason", "runtime_guard") if Fallback else None)
            if Guards:
                Observation["Guard_Region"] = Guards["Region"]
        elif Module_Entered or Module_Fallback:
            Observation.update(Native_Entry=Module_Entered, Actual_Team=Module_Current.get("Team") if Module_Entered else 0,
                               Actual_Mode="native_parallel" if Module_Entered and Module_Current.get("Team", 0) > 1 else "native_serial" if Module_Entered else "python_fallback",
                               Fallback_Reason="runtime_guard" if Fallback else None)
        elif Reduction_Entered:
            Observation.update(Native_Entry=True, Actual_Team=Current.get("Last_Team"),
                               Actual_Mode=Current.get("Last_Mode"), Fallback_Reason=Current.get("Fallback_Reason"))
        elif Region_Entered:
            Observation.update(Native_Entry=not Fallback, Actual_Mode="python" if Fallback else "serial")
        elif Reduction and Observation.get("Proof_Reduction"):
            Observation.update(Native_Entry=False, Actual_Mode="python_fallback" if Fallback else None, Fallback_Reason="runtime_guard" if Fallback else None)
        if Module_Entered:
            Observation["Native_Entry"] = True
            if not Execution or not Execution.get("Native_Entry"):
                Observation["Actual_Team"] = Module_Current.get("Team")
        if Accumulated_Entry:
            Observation.update(Native_Entry=True, Actual_Team=max(Observation.get('Actual_Team') or 0, Totals.get('Maximum_Team', 1)), Native_Spans=Totals['Native_Entries'], Parallel_Spans=Totals.get('Parallel_Entries', 0))
    Observed = (Outcome, tuple(_Value(Arg) for Arg in Inputs), tuple((Notice.category, str(Notice.message)) for Notice in Notices))
    return (Observed + (Random_After,) if Random_State else Observed), Fallback
# Time only isolated valid calls, keeping correctness observations separate from timing noise.
def _Measure(Function, Args, Calls, Deadline=None):
    _Budget(Deadline)
    if _Storage_Bytes(Args) * Calls > _Isolation_Limit:
        raise _Probe_Resource("The timing batch exceeds the backing-storage byte budget")
    Inputs = [_Copy(Args) for Index in range(Calls)]
    _Budget(Deadline)
    Start = perf_counter_ns()
    for Values in Inputs:
        Function(*Values)
    return (perf_counter_ns() - Start) / Calls
# A faster number is usable only after validity and actual-native-entry checks have passed.
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

def _Time(Functions, Args, Size, Gain, Deadline=None):
    Samples = {Name: [] for Name in Functions}
    Calls = {}
    Maximum_Copies = max(1, _Isolation_Limit // max(1, _Storage_Bytes(Args)))
    for Name, Function in Functions.items():
        Warmup = _Measure(Function, Args, 1, Deadline)
        Calls[Name] = max(1, min(64, Maximum_Copies, 65536 // max(Size, 1), int(150000 / max(Warmup, 1))))
    Random = random.Random(31)
    for Batch in range(10):
        Order = list(Functions)
        Random.shuffle(Order)
        try:
            Values = {Name: _Measure(Functions[Name], Args, Calls[Name], Deadline) for Name in Order}
        except _Probe_Timeout:
            break
        for Name, Value in Values.items():
            Samples[Name].append(Value)
        if Batch == 4:
            Medians = sorted(statistics.median(Values) for Values in Samples.values())
            Close = any(Right < Left * Gain * 1.1 for Left, Right in zip(Medians, Medians[1:]))
            if not Close and all(statistics.pstdev(Values) <= statistics.mean(Values) * 0.1 for Values in Samples.values()):
                break
    Timings = {}
    if any(len(Values) < 3 for Values in Samples.values()):
        return Timings
    for Name, Values in Samples.items():
        Timings[Name] = dict(Samples_Ns=Values, Median_Ns=statistics.median(Values), Min_Ns=min(Values), Calls_Per_Batch=Calls[Name],
                             CV=statistics.pstdev(Values) / statistics.mean(Values), Speedup_Vs_Python=statistics.median(Samples["Python"]) / statistics.median(Values))
        if "Serial" in Samples:
            Timings[Name]["Speedup_Vs_Serial"] = statistics.median(Samples["Serial"]) / statistics.median(Values)
    return Timings

def _Check_Case(Item, Modules, Threads, Gain, Teams, Input, Deadline, Invalid):
    from .Selection_Policy import _Candidate_Order
    Key, Size, Shape, Args, Metadata = Input
    Name = Item["Probe"]
    Reference = getattr(Modules["Python"], Name)
    _Budget(Deadline)
    Storage = _Storage_Bytes(Args)
    if (Item['Kind'] in ('scalar', 'numeric_region', 'array_region') or Item.get('List_Alternative')) and not Metadata.get('Representative') and not _Preflight(Reference, Args, Deadline, Item.get('Random', False)):
        raise _Probe_Timeout("Synthetic reference exceeded its 0.5-second preflight budget")
    Expected, Ignored = _Observe(Reference, Args, Random_State=Item.get('Random', False))
    Functions = {"Python": Reference}
    Status = {"Python": "valid"}
    Observations = {}
    for Variant in _Candidate_Order(Item["Eligible"]):
        _Budget(Deadline)
        if Variant not in Modules or Variant not in Item["Eligible"]:
            continue
        if Variant.startswith("OpenMP") and Key == "bytearray":
            Status[Variant] = "unsupported: byte buffer copy runs serially"
            continue
        if Variant.startswith("OpenMP") and (Teams or {}).get(Variant, Threads) < 2:
            Status[Variant] = "unsupported: OpenMP runtime supplied fewer than two threads"
            continue
        Function = getattr(Modules[Variant], Name)
        Observation = dict(Proof_Reduction="Serial_Contract" in Item)
        Actual, Fallback = _Observe(Function, Args, Name, Observation, Random_State=Item.get('Random', False))
        Observations[Variant] = Observation
        if Actual != Expected:
            Invalid.add(Variant)
            Status[Variant] = "invalid: result, exception, identity graph, mutation or warnings differ"
        elif Fallback:
            Status[Variant] = "unsupported: runtime guard selected Python"
        elif Variant.startswith("OpenMP") and Observation.get("Actual_Team") is not None and Observation["Actual_Team"] < 2:
            Status[Variant] = "unsupported: kernel entered with fewer than two OpenMP workers"
        else:
            Functions[Variant] = Function
            Status[Variant] = "valid"
    try:
        Timings = _Time(Functions, Args, Size, Gain, Deadline) if Expected[0][0] == "return" else {}
    except _Probe_Timeout:
        Timings = {}
    Arguments = [Size] if Item["Kind"] == "receive" else (list(Args) if Key == "int" and Item["Kind"] not in ("list_grid", "numeric_region", "array_region", "indexed_filter") else None)
    Case = dict(Key=Key, Size=Size, Arguments=Arguments, Shape=Shape, Validation=Status, Timings=Timings,
                Observations=Observations, Isolation_Bytes=Storage, Winner="Python", Reference_Outcome=Expected[0][0], **Metadata)
    if Expected[0][0] == "return" and not Timings:
        Case["Reason"] = "Inconclusive: fewer than three complete paired samples within the measurement budget"
        Case['Probe_Constraint'] = 'measurement_budget'
    if Item.get("Profile") and Expected[0][0] == "return" and perf_counter_ns() < Deadline:
        import cProfile
        Profiler = cProfile.Profile()
        Profiler.runcall(Reference, *_Copy(Args))
        Entries = sorted(Profiler.getstats(), key=lambda Entry: -Entry.totaltime)[:8]
        Case["Profile"] = [dict(Function=Entry.code.co_name if hasattr(Entry.code, "co_name") else str(Entry.code),
                                Calls=Entry.callcount, Total_Seconds=Entry.totaltime, Self_Seconds=Entry.inlinetime) for Entry in Entries]
    if Expected[0][0] == "raise":
        Case["Reason"] = "Reference raised " + Expected[0][1].__name__
    return Case

def _Check(Item, Modules, Threads, Gain, Teams=None, Deadline=None, Checkpoint=None):
    Cases = []
    Invalid = set()
    Deadline = Deadline or perf_counter_ns() + int(Item.get("Tuning", {}).get("Budget_Seconds", 30) * 1000000000)
    Representative = sorted(_Representative_Cases(Item, Deadline), key=lambda Case: (not Case[4]["Holdout"], -Case[1]))
    Inputs = Representative + [(Key, Size, Shape, Args, {}) for Key, Size, Shape, Args in _Cases(Item)]
    Cases = [dict(Key=Key, Size=Size, Shape=Shape, Validation={"Python": "inconclusive: case pending within worker budget"},
                  Timings={}, Winner="Python", Probe_Constraint='worker_budget', **Metadata) for Key, Size, Shape, Args, Metadata in Inputs]
    if Checkpoint is not None:
        Checkpoint(Cases)
    Remaining = len(Representative)
    for Position, Input in enumerate(Inputs):
        Key, Size, Shape, Args, Metadata = Input
        Now = perf_counter_ns()
        Case_Deadline = Now + max(0, Deadline - Now) // max(1, Remaining) if Metadata.get("Representative") else Deadline
        Remaining -= bool(Metadata.get("Representative"))
        try:
            Case = _Check_Case(Item, Modules, Threads, Gain, Teams, Input, Case_Deadline, Invalid)
        except (_Probe_Timeout, _Probe_Resource) as Error:
            Case = dict(Key=Key, Size=Size, Shape=Shape, Validation={"Python": "inconclusive: " + str(Error)},
                        Timings={}, Winner="Python", Probe_Constraint='storage_budget' if isinstance(Error, _Probe_Resource) else 'worker_budget', **Metadata)
        Cases[Position] = Case
        if Checkpoint is not None:
            Checkpoint(Cases)
    for Case in Cases:
        Valid = {Name: Data for Name, Data in Case["Timings"].items() if Name not in Invalid}
        Case["Winner"] = _Winner(Valid, Gain)
    return Cases

def _Run(Request):
    from PyCeler.Selection_Environment import _Pyceler_Environment
    Spec = json.loads(Request.read_text(encoding="utf-8"))
    Budget = Spec["Item"].get("Tuning", {}).get("Budget_Seconds", 30)
    Deadline = perf_counter_ns() + int(Budget * 1000000000)
    Directory = Request.parent
    Modules = {}
    Errors = {}
    Threads = 0
    Teams = {}
    Original_Teams = {}
    Settings = None
    for Name, File in Spec["Modules"].items():
        try:
            Module = _Load(Path(File))
            if Name.startswith("OpenMP"):
                Current = list(Module._Probe_Settings())
                if Settings is not None and Current != Settings:
                    raise ValueError("OpenMP candidates disagree about their live runtime settings")
                Settings = Current
                Original_Teams[Name] = Module._Probe_Threads()
                Teams[Name] = Module._Probe_Threads(int(Name.split("_")[1]) if "_" in Name else 0)
                Threads = max(Threads, Teams[Name])
            Modules[Name] = Module
        except (ImportError, OSError, ValueError) as Error:
            Errors[Name] = str(Error)
    def _Checkpoint(Cases):
        Environment = dict(Host=_Pyceler_Environment(), NumPy=getattr(sys.modules.get("numpy"), "__version__", None), OpenMP_Settings=Settings)
        Result = dict(Cases=Cases, Environment=Environment, Threads=Threads, Teams=Teams, Import_Errors=Errors,
                      Worker_Budget=dict(Seconds=Budget, Scope="Imports, workload factory, isolation, validation, profiling and timing; excludes compilation",
                                         Process_Limit_Seconds=Budget + 5, Isolation_Byte_Limit=_Isolation_Limit, Minimum_Paired_Samples=3))
        Temporary = Request.with_suffix(".pending")
        Temporary.write_text(json.dumps(Result), encoding="utf-8")
        Temporary.replace(Request.with_suffix(".result"))
    Cases = _Check(Spec["Item"], Modules, Threads, Spec["Gain"], Teams, Deadline, _Checkpoint)
    if any(Modules[Name]._Probe_Threads() != Count for Name, Count in Original_Teams.items()):
        raise RuntimeError("A candidate changed the caller's OpenMP thread configuration")
    _Checkpoint(Cases)

if __name__ == "__main__":
    _Run(Path(sys.argv[1]))
