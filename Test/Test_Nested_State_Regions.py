import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from Test.Workspace import Temporary_Directory

class Nested_State_Regions(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Body = """for Outer in range(Outer_Count):
    for Inner in range(Inner_Count):
        Value = (Outer * Outer + Inner * 17) % Modulus
        if Value % 7 == 0:
            Total += Value * 3
        elif Value % 5 == 0:
            Total -= Value * 2
        elif Value % 3 == 0:
            Total += Value // 2
        else:
            Total += Value % 97
        if Total % 100003 == 0:
            Total += Outer ^ Inner
"""

    def setUp(self):
        (self._Root / "Test_Run").mkdir(exist_ok=True)
        Folder = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Folder.cleanup)
        self._Folder = Path(Folder.name)

    def _Observe(self, File, Fields):
        Command = [sys.executable, "-I", "-B", str(self._Root / "Test/Module_Scalar_Probe.py"), str(File), File.stem, json.dumps(Fields)]
        Result = subprocess.run(Command, capture_output=True, text=True, timeout=120)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
        return json.loads(next(Line.removeprefix("PYCELER_MODULE_RESULT=") for Line in Result.stdout.splitlines() if Line.startswith("PYCELER_MODULE_RESULT=")))

    def test_Nested_Branch_Modulo_Emits_An_Ordered_Native_Region(self):
        Source = self._Folder / "Nested_State.py"
        Source.write_text("raise AssertionError('Source must not execute during conversion')\nOuter_Count = 5000\nInner_Count = 2000\nModulus = 999983\nTotal = 0\n" + self._Body, encoding="utf-8")
        Original = Source.read_bytes()
        Loops = [Node for Node in ast.walk(ast.parse(Original)) if isinstance(Node, ast.For)]
        Findings = {Item.Line: Item for Item in Analyze(Source, OpenMP=True)}
        self.assertEqual(Findings[Loops[1].lineno].Classification, "Module_Scalar_Region")
        self.assertNotIn("Exact OpenMP reduction spans", Findings[Loops[1].lineno].Transformations)
        Output = Convert(Source, self._Folder / "Converted", Select=False, OpenMP=True)
        Text = Output.read_text(encoding="utf-8")
        self.assertIn(f"_Pyceler_Module_Span_{Loops[1].lineno}", Text)
        self.assertIn("_Pyceler_Modulo(", Text)
        self.assertIn("_Pyceler_Bit_Xor(", Text)
        self.assertNotIn(f"_Pyceler_Module_Reduction_{Loops[1].lineno}", Text)
        self.assertEqual(Source.read_bytes(), Original)

    def test_Native_Branches_Empty_Ranges_Overflow_And_Exceptions(self):
        Cases = [(5, 257, 0, 999983), (0, 3, 123, 999983), (4, 0, 123, 999983), (2, 7, 0, -999983), (2, 7, 0, 0), (3, 65, -(2**70), 999983), (3, 31, 2**63 - 1, 999983)]
        Source = self._Folder / "Nested_States.py"
        Body = "Results = []\n"
        for Outer, Inner, Initial, Modulus in Cases:
            Body += f"Outer_Count = {Outer}\nInner_Count = {Inner}\nTotal = {Initial}\nModulus = {Modulus}\nOuter = -11\nInner = -13\nValue = -17\ntry:\n"
            Body += "".join("    " + Line + "\n" for Line in self._Body.splitlines())
            Body += "except ZeroDivisionError:\n    Error = 'ZeroDivisionError'\nelse:\n    Error = None\nResults.append((Total, Outer, Inner, Value, Error))\n"
        Source.write_text(Body, encoding="utf-8")
        Expected = self._Observe(Source, ["Results"])
        for Parallel in (False, True):
            with self.subTest(Parallel=Parallel), patch.dict(os.environ, PYCELER_BUILD_DIR=str(self._Folder / "Build"), OMP_NUM_THREADS="2"):
                Binary = Compile(Source, self._Folder / ("OpenMP" if Parallel else "Serial"), Select=False, OpenMP=Parallel)
                Actual = self._Observe(Binary, ["Results"])
                self.assertEqual(Actual["Values"], Expected["Values"])
                self.assertEqual(Actual["Error"], Expected["Error"])
                self.assertGreater(Actual["Native"]["Native"], 0)
                self.assertEqual(Actual["Native"]["Parallel"], 0)
                self.assertEqual(Actual["Native"]["Team"], 1)
                self.assertGreater(Actual["Native"]["Fallbacks"], 0)

    def test_Modulo_Of_Existing_Object_And_Partial_Binding_Stay_Python(self):
        Source = self._Folder / "Identity.py"
        Source.write_text("Original = int('1099511627777')\nModulus = 2 ** 61\nfor Index in range(4):\n    Value = Original % Modulus\nSame = Value is Original\n", encoding="utf-8")
        self.assertEqual(Analyze(Source)[0].Change, "Keep original loop")
        Partial = self._Folder / "Partial.py"
        Partial.write_text("Total = 1000\nfor Index in range(20):\n    if Index % 2:\n        Total += Index\n", encoding="utf-8")
        self.assertEqual(Analyze(Partial)[0].Change, "Keep original loop")
