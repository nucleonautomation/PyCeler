import ast
import builtins
import contextlib
import hashlib
import importlib.util
import io
import json
import random
import struct
import sys
from pathlib import Path
from time import perf_counter
import numpy as np
# Measurement harness for pipeline.
def Snapshot(Values):
    Memo, Nodes, Held, Arrays = {}, [], [], []
    def Visit(Value):
        if id(Value) in Memo:
            return Memo[id(Value)]
        Index = len(Nodes)
        Memo[id(Value)] = Index
        Held.append(Value)
        Nodes.append(None)
        if isinstance(Value, np.ndarray):
            Arrays.append(Value)
            Record = type(Value).__name__, Value.dtype.str, Value.shape, Value.strides, hashlib.sha256(Value.tobytes()).hexdigest()
        elif isinstance(Value, np.generic):
            Record = type(Value).__name__, Value.dtype.str, Value.tobytes().hex()
        elif type(Value) in (list, tuple):
            Record = type(Value).__name__, [Visit(Part) for Part in Value]
        elif type(Value) is dict:
            Record = 'dict', [(Key, Visit(Part)) for Key, Part in sorted(Value.items())]
        elif type(Value) is float:
            Record = 'float', struct.pack('!d', Value).hex()
        elif type(Value).__name__ == 'PointCloud':
            Record = 'PointCloud', [Visit(np.asarray(getattr(Value, Name))) for Name in ('points', 'colors', 'normals')]
        elif type(Value).__name__ == 'DataFrame':
            Record = 'DataFrame', repr(Value.index), repr(Value.columns), [str(Dtype) for Dtype in Value.dtypes], Visit(Value.to_numpy())
        elif type(Value).__name__ == 'cKDTree':
            Record = 'cKDTree', Visit(Value.data), Value.n, Value.m, Value.leafsize
        else:
            Record = type(Value).__name__, repr(Value)
        Nodes[Index] = Record
        return Index
    Visit(Values)
    Aliases = [(A, B) for A, Left in enumerate(Arrays) for B, Right in enumerate(Arrays[:A]) if np.shares_memory(Left, Right)]
    return hashlib.sha256(json.dumps((Nodes, Aliases), separators=(',', ':')).encode()).hexdigest()

def Probe(File, Source, Profile=False):
    sys.path.insert(0, str(File.parent))
    Tree = ast.parse(Source.read_text())
    Fields = sorted({Node.id for Statement in Tree.body if not isinstance(Statement, (ast.FunctionDef, ast.ClassDef)) for Node in ast.walk(Statement) if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Store)} - {'start', 'elapsed'})
    Spec = importlib.util.spec_from_file_location(File.name.split('.')[0], File)
    Module = importlib.util.module_from_spec(Spec)
    sys.modules[Spec.name] = Module
    Output = io.StringIO()
    Error = None
    Timings = {}
    Original_Print = builtins.print
    def Print(*Args, **Keywords):
        if len(Args) == 2 and type(Args[0]) is str and Args[0] == 'Processing frame:' and type(Args[1]) is int and Args[1] == 0:
            for Name in ('generate_sensor_frame', 'process_image', 'generate_point_cloud', 'process_geometry', 'numerical_simulation', 'process_metrics'):
                Function = getattr(Module, Name)
                def Timed(*Values, _Function=Function, _Name=Name, **Options):
                    Started = perf_counter()
                    try:
                        return _Function(*Values, **Options)
                    finally:
                        Timings[_Name] = Timings.get(_Name, 0.0) + perf_counter() - Started
                setattr(Module, Name, Timed)
        Original_Print(*Args, **Keywords)
    Begin = perf_counter()
    if Profile:
        builtins.print = Print
    with contextlib.redirect_stdout(Output):
        try:
            Spec.loader.exec_module(Module)
        except Exception as Failure:
            Error = type(Failure).__name__, str(Failure)
        finally:
            builtins.print = Original_Print
    Duration = perf_counter() - Begin
    Values = {Name: vars(Module)[Name] for Name in Fields if Name in vars(Module)}
    Values['Python_Random_State'] = random.getstate()
    Values['NumPy_Random_State'] = np.random.get_state()
    Stats = {Name: Value() for Name, Value in vars(Module).items() if Name.startswith('_Pyceler_Fast_') and Name.endswith('Stats')}
    return dict(State=Snapshot(Values), Fields={Name: Snapshot(Value) for Name, Value in Values.items()}, Error=Error, Seconds=getattr(Module, 'elapsed', Duration), Import_Seconds=Duration, Native=Stats, Output=Output.getvalue(), Stage_Seconds=Timings)

if __name__ == '__main__':
    Report = Probe(Path(sys.argv[1]), Path(sys.argv[2]), '--profile' in sys.argv[4:])
    Path(sys.argv[3]).write_text(json.dumps(Report, indent=2))
    print(json.dumps(dict(Seconds=Report['Seconds'], State=Report['State'], Error=Report['Error'], Native=Report['Native'])), flush=True)
