import ast
import importlib.util
import json
import sys
from pathlib import Path

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Graph(Values):
    Nodes = []
    Descriptions = []
    def _Visit(Value):
        Number = len(Nodes)
        Aliases = tuple(Index for Index, Previous in enumerate(Nodes) if Value is Previous)
        Nodes.append(Value)
        Kind = type(Value).__name__
        if type(Value) in (tuple, list):
            Descriptions.append((Kind, len(Value), Aliases))
            for Child in Value:
                _Visit(Child)
        else:
            Descriptions.append((Kind, Value.hex() if type(Value) is float else Value, Aliases))
        return Number
    for Value in Values:
        _Visit(Value)
    return Descriptions

def _Outcome(Function, Inputs, Callback):
    Args = (*Inputs, []) if Callback else Inputs
    try:
        Result = Function(*Args)
    except Exception as Error:
        return "error", type(Error).__name__, Error.args, _Graph(Args)
    return "value", _Graph((*Args, Result))

def _Positive_Cases(Source):
    Families = dict(Sum=24, Ordered=12, Callback=6)
    Names = {Family + "_" + str(Number) for Family, Count in Families.items() for Number in range(Count)}
    Functions = {Node.name: Node for Node in ast.parse(Source).body if isinstance(Node, ast.FunctionDef)}
    assert Names <= set(Functions), sorted(Names - set(Functions))
    Inputs = (2, 1, 7)
    Environment = dict(Count=Inputs[0], Value=Inputs[1], Divisor=Inputs[2])
    for Name in sorted(Names):
        Function = Functions[Name]
        Loops = [Node for Node in ast.walk(Function) if isinstance(Node, (ast.For, ast.While))]
        assert len(Loops) == 1, Name
        Loop = Loops[0]
        if isinstance(Loop, ast.For):
            assert isinstance(Loop.iter, ast.Call) and isinstance(Loop.iter.func, ast.Name) and Loop.iter.func.id == "range", Name
            Arguments = [eval(compile(ast.Expression(Node), "Witness_Bound.py", "eval"), {"__builtins__": {}}, Environment) for Node in Loop.iter.args]
            Indices = tuple(range(*Arguments))
            assert 0 < len(Indices) <= 2 and all(-2 <= Index <= 2 for Index in Indices), (Name, Indices)
        else:
            Position = Function.body.index(Loop)
            assert Position > 0 and ast.dump(Function.body[Position - 1]) == ast.dump(ast.parse("Index = 0").body[0]), Name
            assert ast.dump(Loop.test) == ast.dump(ast.parse("Index < Count", mode="eval").body), Name
            assert ast.dump(Loop.body[0]) == ast.dump(ast.parse("Index += 1").body[0]), Name
        for Node in ast.walk(Function):
            if not isinstance(Node, (ast.BinOp, ast.UnaryOp)):
                continue
            Expression = compile(ast.Expression(Node), "Witness_Expression.py", "eval")
            for Index in range(-2, 3):
                Result = eval(Expression, {"__builtins__": {}}, dict(Environment, Index=Index))
                assert type(Result) is int and abs(Result) < 2**50, (Name, Index, Result)
    return {Name: Inputs for Name in sorted(Names)}

def _Statistics(Module, Suffix):
    Hooks = [Value for Name, Value in vars(Module).items() if Name.startswith("_Pyceler_") and Name.endswith(Suffix) and callable(Value)]
    assert len(Hooks) <= 1, Suffix
    return Hooks[0] if Hooks else None

def _Observe(Module, Name, Inputs):
    Dispatch = _Statistics(Module, "Dispatch_Stats")
    Region = _Statistics(Module, "Region_Stats")
    Reduction = _Statistics(Module, "Reduction_Stats")
    Before_Region = tuple(Region()) if Region else (0, 0)
    Before_Reduction = dict(Reduction()) if Reduction else {}
    Execution = {}
    if Dispatch:
        Dispatch(True, Reset=True)
        assert Dispatch() == {}, (Name, "dispatch reset did not clear previous evidence")
    try:
        Outcome = _Outcome(getattr(Module, Name), Inputs, Name.startswith("Callback_"))
    finally:
        if Dispatch:
            Execution = dict(Dispatch().get("Execution", {}))
            Dispatch(False, Reset=True)
    After_Region = tuple(Region()) if Region else (0, 0)
    After_Reduction = dict(Reduction()) if Reduction else {}
    Changes = dict(Region_Attempts=After_Region[0] - Before_Region[0], Region_Fallbacks=After_Region[1] - Before_Region[1])
    Changes.update({Key: After_Reduction.get(Key, 0) - Before_Reduction.get(Key, 0) for Key in ("Serial_Calls", "Parallel_Calls")})
    assert all(Value >= 0 for Value in Changes.values()), (Name, Changes)
    Entered = Execution.get("Native_Entry") is True and Execution.get("Reason") in ("native_serial", "native_parallel")
    Entered = Entered or Changes["Serial_Calls"] > 0 or Changes["Parallel_Calls"] > 0
    Entered = Entered or Changes["Region_Attempts"] > Changes["Region_Fallbacks"]
    Fallback = Execution.get("Reason") == "python_fallback" or Changes["Region_Fallbacks"] > 0
    return Outcome, dict(Native_Entry=bool(Entered), Python_Fallback=bool(Fallback), Execution=Execution, Counter_Deltas=Changes)

def _Run():
    Source, Binary = map(Path, sys.argv[1:3])
    Original = _Load("Original_Generated", Source)
    Native = _Load(Binary.stem.split(".", 1)[0], Binary)
    Names = sorted(Name for Name in vars(Original) if Name.startswith(("Sum_", "Ordered_", "Aliases_", "Callback_")))
    Values = (int("1000"), int("-1000"), 0, 1, -1, 2**63 - 1, -(2**63), 2**80)
    Cases = [(Count, Value, Divisor) for Count in (-2, 0, 1, 7, 19, 301) for Value in Values for Divisor in (0, 1, -7, 2**50)]
    Witnesses = _Positive_Cases(Source.read_text(encoding="utf-8"))
    Native_Programs = {}
    Checks = 0
    for Name in Names:
        for Inputs in Cases:
            Expected = _Outcome(getattr(Original, Name), Inputs, Name.startswith("Callback_"))
            Actual = _Outcome(getattr(Native, Name), Inputs, Name.startswith("Callback_"))
            if Actual != Expected:
                raise AssertionError((Name, Inputs, Expected, Actual))
            Checks += 1
    for Name, Inputs in Witnesses.items():
        Expected = _Outcome(getattr(Original, Name), Inputs, Name.startswith("Callback_"))
        Actual, Observation = _Observe(Native, Name, Inputs)
        assert Expected[0] == "value" and Actual == Expected, (Name, Inputs, Expected, Actual)
        assert Observation["Native_Entry"] and not Observation["Python_Fallback"], (Name, Inputs, Observation)
        Native_Programs[Name] = dict(Inputs=Inputs, **Observation)
    Original.range = Native.range = lambda *Args: [2, 7, -3]
    for Name in Names:
        Inputs = (7, int("1000"), 2**50)
        Expected = _Outcome(getattr(Original, Name), Inputs, Name.startswith("Callback_"))
        Actual = _Outcome(getattr(Native, Name), Inputs, Name.startswith("Callback_"))
        if Actual != Expected:
            raise AssertionError((Name, "custom range", Expected, Actual))
        Checks += 1
    print(json.dumps(dict(Generated_Programs=len(Names), Differential_Cases=Checks, Exact_Values_Types_Aliases_Exceptions_And_Callbacks=True,
                         Native_Witness_Comparisons=len(Native_Programs), Native_Programs=Native_Programs,
                         Native_Families={Family: sum(Name.startswith(Family + "_") for Name in Native_Programs) for Family in ("Sum", "Ordered", "Callback")},
                         Behavior_Only_Programs=sorted(set(Names) - set(Witnesses)))))

if __name__ == "__main__":
    _Run()
