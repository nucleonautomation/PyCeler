import ast
import importlib.util
import unittest
from pathlib import Path

Root = Path(__file__).resolve().parents[1]
Spec = importlib.util.spec_from_file_location("_Binary_Math_Plan_Test", Root / "PyCeler/Fast_Math.py")
Fast = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Fast)

def _Plan(Expression, Imports="import math", Names=("Left", "Right", "Output")):
    Tree = ast.parse(Imports + "\ndef Compute(" + ", ".join(Names) + "):\n    for Index in range(len(Left)):\n        Output[Index] = " + Expression + "\n    return Output\n")
    Function = Tree.body[-1]
    return Fast._Fast_Math_Plan(dict(Loops=[Function.body[0]], Indices=["Index"], Scalars=[], Locals=[], Output="Output", Names=list(Names), Math_Imports=Imports.splitlines()))

class Fast_Binary_Plan(unittest.TestCase):
    def test_Exact_Arity_And_Ordered_Argument_Nodes(self):
        Plan = _Plan("math.fmod(math.sqrt(Left[Index]), math.log(Right[Index]))")
        self.assertEqual(Plan["Version"], 3)
        self.assertEqual(Plan["Inputs"], ("Left", "Right"))
        self.assertEqual(Plan["Expression"], ("call", "fmod", (("call", "sqrt", (("input", 0),)), ("call", "log", (("input", 1),)))))
        self.assertIn(("fmod", 2, "float", "Binary_Nonzero_Remainder"), Plan["Call_Contracts"])

    def test_Emit_Evaluates_Each_Argument_Once_In_Source_Order(self):
        Plan = _Plan("math.fmod(math.sqrt(Left[Index]), math.log(Right[Index]))")
        Lines, Variables = [], []
        Fast._Fast_Emit(Plan["Expression"], Lines, Variables, Plan["Functions"], "_Test_")
        Source = "\n".join(Lines)
        self.assertEqual(Source.count("_Test_sqrt("), 1)
        self.assertEqual(Source.count("_Test_log("), 1)
        self.assertEqual(Source.count("_Test_fmod("), 1)
        self.assertLess(Source.index("_Test_sqrt("), Source.index("_Test_log("))
        self.assertLess(Source.index("_Test_log("), Source.index("_Test_fmod("))
        Call = next(Line for Line in Lines if "_Test_fmod(" in Line)
        self.assertRegex(Call, r"_Test_fmod\(T\d+, T\d+\)")

    def test_Arity_Keywords_Starred_And_Numpy_Arithmetic_Fail_Closed(self):
        for Expression in ("math.copysign(Left[Index])", "math.fmod(Left[Index], Right[Index], 2.0)", "math.copysign(x=Left[Index], y=Right[Index])", "math.fmod(*(Left[Index], Right[Index]))", "math.copysign(Left[Index] + Right[Index], Right[Index])", "math.pow(Left[Index], Right[Index])", "math.atan2(Left[Index], Right[Index])"):
            with self.subTest(Expression=Expression):
                self.assertIsNone(_Plan(Expression))

    def test_Aliases_And_Erf_Backend_Requirements_Are_Preserved(self):
        Plan = _Plan("Copy(Remain(Left[Index], Right[Index]), Right[Index])", "from math import copysign as Copy, fmod as Remain")
        self.assertEqual(Plan["Bindings"], (("Copy", "copysign", False), ("Remain", "fmod", False)))
        self.assertEqual(Plan["Backend_Requirements"], ())
        Plan = _Plan("math.copysign(math.erf(Left[Index]), Right[Index])")
        self.assertEqual(Plan["Backend_Requirements"], ("Runtime_CPython_Libm_Erf",))

    def test_Integer_Zero_Normalization_And_Float_Negative_Zero_Are_Distinct(self):
        Integer = _Plan("math.copysign(math.fmod(Left[Index], Right[Index]), -0)")
        Floating = _Plan("math.copysign(math.fmod(Left[Index], Right[Index]), -0.0)")
        Boolean = _Plan("math.copysign(Left[Index], -math.isinf(Right[Index]))")
        self.assertEqual(Integer["Expression"][2][1][0], "integer_negative")
        self.assertEqual(Boolean["Expression"][2][1][0], "integer_negative")
        self.assertEqual(Floating["Expression"][2][1][0], "negative")

    def test_Binary_Guards_And_Unary_Arithmetic_Stay_Separate(self):
        for Expression in ("math.copysign(Left[Index], Right[Index])", "math.fmod(Left[Index], Right[Index])"):
            Plan = _Plan(Expression)
            Source = Fast._Fast_Math_Kernel(Plan, 4, True)
            self.assertIn("const double[::1] I0, const double[::1] I1", Source)
            self.assertIn("_Pyceler_Fast_4_Prange", Source)
            self.assertIn("_Pyceler_Fast_4_signbit(T", Source)
        Plan = _Plan("math.sin(Left[Index])", Names=("Left", "Output"))
        self.assertEqual(Plan["Expression"], ("call", "sin", (("input", 0),)))
        self.assertEqual(Plan["Inputs"], ("Left",))
