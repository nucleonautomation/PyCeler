import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Compile, Convert
from PyCeler.Scalar_Math import _Scalar_Math_Plan
from Test.Workspace import Temporary_Directory
# Regression checks for scalar math call boundaries and observer behavior.
class Scalar_Math(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Recognition_And_Float_Selection_Inputs(self):
        from PyCeler.Selection_Worker import _Cases
        Source = self._Root / "Test/Scalar_Math_Loops.py"
        Findings = Analyze(Source)
        Changed = [Finding for Finding in Findings if Finding.Change != "Keep original loop"]
        self.assertEqual(len(Changed), 10, Findings)
        Item = dict(Kind="scalar", Arguments=5, Size_Arguments=(0,), Range_Start_Argument=1, Range_Step=1, Float_Arguments=(2, 3, 4))
        self.assertTrue(all(all(type(Value) is float for Value in Args[2:]) for Key, Size, Shape, Args in _Cases(Item)))

    def test_Unsafe_Output_Identities_And_Calls_Are_Not_Specialized(self):
        Bodies = ("Y = math.sin(X)\nZ = X", "Y = math.sin(X)\nZ = 1.0", "Y = math.sin(X)\nif X > 0.0:\n    Z = X + 0.25", "Y = custom(X)", "Y = math.sin(X)\nX = 3.0", "Y = math.sin(X)\nX = Y")
        for Body in Bodies:
            Tree = ast.parse("def Compute(N, X):\n    for I in range(N):\n" + "\n".join("        " + Line for Line in Body.splitlines()))
            self.assertIsNone(_Scalar_Math_Plan(Tree.body[0], Tree.body[0].body[0], {"N", "X"}, "Compute"), Body)

    def test_Compiled_Math_State_And_Fallback(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Source = self._Root / "Test/Scalar_Math_Loops.py"
            Generated = Convert(Source, Folder / "Cython", Select=False, OpenMP=True)
            Status = '\ncdef extern from "fenv.h":\n    int _Nearest "FE_TONEAREST"\n    int _Downward "FE_DOWNWARD"\n    int _All "FE_ALL_EXCEPT"\n    int _Get "fegetround"()\n    int _Set "fesetround"(int)\n    int _Flags "fetestexcept"(int)\n    int _Clear "feclearexcept"(int)\n\ndef Test_Rounding(Down):\n    _Set(_Downward if Down else _Nearest)\n\ndef Test_Flags(Clear=False):\n    Result = _Flags(_All)\n    if Clear:\n        _Clear(_All)\n    return Result\n'
            Generated.write_text(Generated.read_text(encoding="utf-8") + Status, encoding="utf-8")
            Binary = Compile(Generated, Folder / "Native", Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Scalar_Math_Probe.py"), str(Source), str(Binary), str(Folder / "Results.json")], capture_output=True, text=True, timeout=180)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
            Report = json.loads((Folder / "Results.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(Report["Comparisons"], 70)
            self.assertGreaterEqual(Report["Positive_Native_Cases"], 10)

    def test_Direct_And_Nested_Math_Families(self):
        from Test.Scalar_Math_Families import Source, Families
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Fixture = Folder / "Scalar_Families.py"
            Fixture.write_text(Source(), encoding="utf-8")
            Findings = Analyze(Fixture)
            self.assertEqual(sum(Item.Change != "Keep original loop" for Item in Findings), 2 * len(Families))
            Binary = Compile(Fixture, Folder / "Native", Select=False, OpenMP=True)
            Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Scalar_Math_Families.py"), str(Fixture), str(Binary)], capture_output=True, text=True, timeout=180)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
            Report = json.loads(Result.stdout)
            self.assertEqual(Report["Comparisons"], 14 * len(Families))
