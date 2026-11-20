import importlib.util
import json
import sys
from pathlib import Path
# Test support/workload for scalar math call boundaries and observer behavior.
Families = dict(acos=0.2, acosh=1.2, asin=0.2, asinh=-0.2, atan=0.2, atanh=0.2, cbrt=1.2, cos=0.2, cosh=0.2,
                sin=-0.2, sinh=0.2, tan=0.2, tanh=0.2, sqrt=1.2, exp=0.2, exp2=0.2, expm1=-0.2, log=1.2,
                log10=1.2, log1p=0.2, fabs=-1.2, erf=0.2, erfc=0.2, copysign=-0.2, fmod=1.2)

def Source():
    Lines = ["import math as Operations"]
    for Name in Families:
        for Nested in (False, True):
            Suffix = "Nested" if Nested else "Direct"
            Input, Total, Index, Result = ("Signal", "Accumulator", "Position", "Term") if Nested else ("X", "Sum", "Index", "Result")
            Lines.extend([f"def {Name}_{Suffix}(Count, {Input}):", f"    {Total} = 0.0", f"    {Index} = -1", f"    {Result} = None"])
            if Nested:
                Lines.append("    for Pass in range(3):")
            Indent = "        " if Nested else "    "
            Argument = Input + (", 1.7" if Name in ("copysign", "fmod") else "")
            Lines.extend([Indent + f"for {Index} in range(Count):", Indent + f"    {Result} = Operations.{Name}({Argument})", Indent + f"    {Total} += {Result} * 0.001", f"    return {Total}, {Index}, {Result}"])
    return "\n".join(Lines) + "\n"

def _Load(Path, Name):
    Spec = importlib.util.spec_from_file_location(Name, Path)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Run():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from Test.Scalar_Math_Probe import _Observe, _Native
    Original = _Load(sys.argv[1], "Reference")
    Native = _Load(sys.argv[2], "Scalar_Families")
    Comparisons, Entered = 0, 0
    for Name, Value in Families.items():
        for Nested in (False, True):
            Function = Name + ("_Nested" if Nested else "_Direct")
            for Count, Input in ((64, Value), (8193, Value), (0, Value), (1, -0.0), (2, float("inf")), (2, float("nan")), (2, 0.2)):
                Before = _Native(Native)
                Expected = _Observe(getattr(Original, Function), (Count, Input))
                Actual = _Observe(getattr(Native, Function), (Count, Input))
                assert Actual == Expected, (Function, Count, Input, Actual, Expected)
                if Count in (64, 8193) and (Name not in ("erf", "erfc") or sys.version_info >= (3, 12)):
                    assert _Native(Native) - Before == Count * (3 if Nested else 1), (Function, Before, _Native(Native))
                    Entered += 1
                Comparisons += 1
    print(json.dumps(dict(Families=len(Families), Functions=2 * len(Families), Comparisons=Comparisons, Positive_Native_Cases=Entered)))

if __name__ == "__main__":
    _Run()
