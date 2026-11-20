import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from Test.Scalar_Flow_Corpus import Corpus
from Test.Workspace import Temporary_Directory
# Regression checks for scalar data flow and equivalent source rewrites.
class Scalar_Flow(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Folder = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Folder.cleanup)
        self._Folder = Path(Folder.name)
        Environment = patch.dict(os.environ, PYCELER_BUILD_DIR=str(self._Folder / "Build"), OMP_NUM_THREADS="2")
        Environment.start()
        self.addCleanup(Environment.stop)
        self._Source = self._Folder / "Flow_Corpus.py"
        Text, self._Names = Corpus()
        self._Source.write_text(Text, encoding="utf-8")

    def test_Composed_Shapes_Reach_Existing_Native_Lowering(self):
        Original = self._Source.read_bytes()
        Findings = Analyze(self._Source, OpenMP=True)
        Regions = [Item for Item in Findings if Item.Classification == "Scalar_Numeric_Region"]
        self.assertEqual(sorted(Item.Function for Item in Regions), sorted(self._Names))
        self.assertEqual(sum(Item.Classification == "Module_Scalar_Region" for Item in Findings), 12)
        Output = Convert(self._Source, self._Folder / "Generated", Select=False, OpenMP=True)
        Text = Output.read_text(encoding="utf-8")
        self.assertIn("Assign0", Text)
        self.assertEqual(self._Source.read_bytes(), Original)

    def test_Compiled_Combinations_And_Fallbacks_Match_Python(self):
        Binary = Compile(self._Source, self._Folder / "Native", Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
        Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Scalar_Flow_Probe.py"), str(self._Source), str(Binary)], capture_output=True, text=True, timeout=120)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
        Report = json.loads(Result.stdout)
        self.assertEqual(Report["Functions"], 48)
        self.assertEqual(Report["Comparisons"], 384)
        self.assertGreaterEqual(Report["Confirmed_Native_Entries"], 144)

    def test_Final_Aliases_And_Partial_Bindings_Are_Not_Reboxed(self):
        Bodies = ["Value = Initial\n", "Value = Index + 1\nValue = Initial\n", "if Index % 2:\n    Value = Index + 1\nelse:\n    Value = Initial\n", "if Index % 2:\n    Value = Index + 1\n", "Value, Other = Index + 1, Initial\n", "Value = Index + 1\nOther = Value\n", "Value = Index + 1\nValue %= Modulus\n"]
        for Position, Body in enumerate(Bodies):
            with self.subTest(Position=Position):
                Source = self._Folder / f"Identity_{Position}.py"
                Source.write_text("Initial = int('1099511627777')\nModulus = 2 ** 61\nValue = Initial\nOther = Initial\nfor Index in range(4):\n" + "".join("    " + Line + "\n" for Line in Body.splitlines()) + "Result = (Value is Initial, Other is Initial, Value is Other)\n", encoding="utf-8")
                self.assertEqual(Analyze(Source)[0].Change, "Keep original loop")

    def test_Measured_Nested_Region_Does_Not_Execute_Outer_Work(self):
        Source = self._Folder / "Nested_Selection.py"
        Source.write_text("raise RuntimeError('module must not execute')\ndef Compute(Count, Events):\n    Total = 0\n    for Outer in range(2):\n        Events.append(Outer)\n        for Index in range(Count):\n            Value = Index + 11 if Index % 2 else Index * 3 + 5\n            Total += Value\n    Events.append(Total)\n", encoding="utf-8")
        Output = Convert(Source, self._Folder / "Measured", OpenMP=False, Minimum_Speedup=1e12)
        Report = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        Item, = Report["Items"]
        self.assertTrue(Item["Extracted"])
        self.assertTrue(any(Case["Validation"].get("Serial") == "valid" and Case["Observations"]["Serial"]["Native_Entry"] for Case in Item["Cases"]), Item)

    def test_Branch_Bindings_And_Outer_Indices_Flow_Into_Inner_Regions(self):
        Source = self._Folder / "Bound_Region.py"
        Source.write_text("def Compute(Count, Flag, Events):\n    if Flag:\n        Factor = 7\n    else:\n        Factor = 11\n    Total = 0\n    for Outer in range(3):\n        for Index in range(Count):\n            Total += Index * Factor + Outer\n        Events.append((Outer, Total))\n    return Total\n", encoding="utf-8")
        Findings = Analyze(Source)
        self.assertEqual(sum(Item.Classification == "Scalar_Numeric_Region" for Item in Findings), 1)
        Binary = Compile(Source, self._Folder / "Bindings", Select=False, OpenMP=False)
        Program = "import sys\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nfrom Test.Scalar_Flow_Probe import Load\nOriginal = Load(Path(sys.argv[2]), 'Reference')\nNative = Load(Path(sys.argv[3]), 'Bound_Region')\nfor Count in (0, 17):\n    for Flag in (False, True):\n        Expected, Actual = [], []\n        Before = Native._Pyceler_Region_Stats()\n        assert Original.Compute(Count, Flag, Expected) == Native.Compute(Count, Flag, Actual)\n        assert Actual == Expected\n        After = Native._Pyceler_Region_Stats()\n        if Count:\n            assert After[0] - Before[0] == 3 and After[1] == Before[1], (Before, After)\n"
        Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(self._Root), str(Source), str(Binary)], capture_output=True, text=True, timeout=120)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
