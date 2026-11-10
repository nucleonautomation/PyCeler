import importlib.util
import itertools
import json
import random
import sys
from pathlib import Path

_Minimum = -(2**63)
_Maximum = 2**63 - 1

def _Evaluate(Node, Values):
    Kind = Node[0]
    if Kind == "arg":
        return Values[Node[1]]
    if Kind == "constant":
        return Node[1]
    if Kind == "negative" and Node[1] == ("constant", 2**63):
        return _Minimum
    Left = _Evaluate(Node[1], Values)
    if Kind == "negative":
        Result = -Left
    else:
        Right = _Evaluate(Node[2], Values)
        if Kind == "add":
            Result = Left + Right
        elif Kind == "subtract":
            Result = Left - Right
        elif Kind == "multiply":
            Result = Left * Right
        elif Kind == "floor":
            Result = Left // Right
        elif Kind == "modulo":
            Result = Left % Right
        else:
            raise AssertionError(Kind)
    assert _Minimum <= Result <= _Maximum, (Node, Values, Result)
    return Result

def _Recipe(Random, Depth, Arguments):
    if not Depth or Random.randrange(4) == 0:
        if Random.randrange(2):
            return ("arg", Random.randrange(Arguments))
        return ("constant", Random.choice((-7, -1, 0, 1, 2, 11, _Minimum, _Maximum)))
    Kind = Random.choice(("add", "subtract", "multiply", "floor", "modulo", "negative"))
    Left = _Recipe(Random, Depth - 1, Arguments)
    return (Kind, Left) if Kind == "negative" else (Kind, Left, _Recipe(Random, Depth - 1, Arguments))

def _Intervals(Module, Random):
    Accepted = 0
    for Case in range(400):
        Recipe = _Recipe(Random, 3, 2)
        Bounds = tuple(tuple(sorted((Random.randrange(-7, 8), Random.randrange(-7, 8)))) for Index in range(2))
        Actual = Module._Test_Reduction_Interval(Recipe, Bounds)
        if Actual is None:
            continue
        Accepted += 1
        for Values in itertools.product(*(range(Low, High + 1) for Low, High in Bounds)):
            Expected = _Evaluate(Recipe, Values)
            assert Actual[0] <= Expected <= Actual[1], (Recipe, Bounds, Actual, Values, Expected)
    assert Accepted >= 40, Accepted
    return Accepted

def _Proofs(Module, Random):
    Accepted = 0
    Terms = (("arg", 2), ("multiply", ("arg", 2), ("arg", 2)),
             ("modulo", ("arg", 2), ("constant", 7)),
             ("floor", ("arg", 2), ("constant", -3)),
             ("subtract", ("multiply", ("arg", 2), ("constant", 3)), ("constant", 5)))
    for Begin, Stop, Step, Initial in itertools.product(range(-8, 9, 4), range(-8, 9, 4), (-3, -1, 1, 3), (0, 17, 256)):
        for Term in Terms:
            Plan = dict(Begin=("arg", 0), Stop=("arg", 1), Step=Step, Term=Term, Initial=Initial)
            Proof = Module._Test_Reduction_Allowed((Begin, Stop), Plan)
            assert Proof == (Begin, len(range(Begin, Stop, Step))), (Plan, Proof)
            Accepted += 1
            Values = [_Evaluate(Term, (Begin, Stop, Index)) for Index in range(Begin, Stop, Step)]
            Expected = Initial + sum(Values)
            for Trial in range(4):
                Random.shuffle(Values)
                Total = 0
                for Value in Values:
                    Total += Value
                    assert _Minimum <= Total <= _Maximum
                assert Initial + Total == Expected and _Minimum <= Initial + Total <= _Maximum
    return Accepted

def _Boundaries(Module):
    Plan = dict(Begin=("arg", 0), Stop=("arg", 1), Step=1, Term=("arg", 2), Initial=0)
    assert Module._Test_Reduction_Allowed((_Minimum, _Maximum), Plan) is None
    assert Module._Test_Reduction_Allowed((_Maximum - 1, _Maximum), Plan) == (_Maximum - 1, 1)
    assert Module._Test_Reduction_Allowed((_Minimum, _Minimum + 1), Plan) == (_Minimum, 1)
    assert Module._Test_Reduction_Allowed((True, 5), Plan) is None
    assert Module._Test_Reduction_Allowed((0, 5.0), Plan) is None
    assert Module._Test_Reduction_Allowed((0, _Maximum + 1), Plan) is None
    Plan.update(Step=-1)
    assert Module._Test_Reduction_Allowed((_Maximum, _Minimum), Plan) is None
    assert Module._Test_Reduction_Allowed((_Minimum + 1, _Minimum), Plan) == (_Minimum + 1, 1)
    Bounds = ((_Minimum, _Minimum),)
    assert Module._Test_Reduction_Interval(("floor", ("arg", 0), ("constant", -1)), Bounds) is None
    assert Module._Test_Reduction_Interval(("modulo", ("arg", 0), ("constant", -1)), Bounds) == (0, 0)
    assert Module._Test_Reduction_Interval(("negative", ("constant", 2**63)), ()) == (_Minimum, _Minimum)
    for Kind in ("floor", "modulo"):
        assert Module._Test_Reduction_Interval((Kind, ("constant", 4), ("arg", 0)), ((-1, 1),)) is None
    Plan.update(Step=1, Term=("constant", _Maximum), Initial=1)
    assert Module._Test_Reduction_Allowed((0, 1), Plan) is None
    Plan.update(Initial=0)
    assert Module._Test_Reduction_Allowed((0, 2), Plan) is None

def _Run(Binary):
    Spec = importlib.util.spec_from_file_location(Binary.name.split(".")[0], Binary)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    Random = random.Random(73131)
    Intervals = _Intervals(Module, Random)
    Proofs = _Proofs(Module, Random)
    _Boundaries(Module)
    print(json.dumps(dict(Status="passed", Interval_Proofs=Intervals, Reduction_Proofs=Proofs, Seed=73131)))

if __name__ == "__main__":
    _Run(Path(sys.argv[1]))
