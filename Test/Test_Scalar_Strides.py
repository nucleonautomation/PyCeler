import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from Test.Workspace import Temporary_Directory

class Scalar_Strides(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Steps = (-7, -4, -3, -2, -1, 1, 2, 3, 4, 7)

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build")})
        Environment.start()
        self.addCleanup(Environment.stop)

    def _Fixture(self):
        Blocks = []
        for Step in self._Steps:
            Name = "Stride_" + ("Minus_" if Step < 0 else "Plus_") + str(abs(Step))
            Blocks.append(f"def {Name}(Begin, End, Events, Callback):\n    Total = 0\n    Index = -23\n    for Index in range(Begin, End, {Step}):\n        Total += (Index * Index + 7 * Index) % 999983\n        if Index % 6 == 0 and Index != 0:\n            Events.append((Index, Total))\n            Total = Callback(Index, Total)\n            if Total == -777:\n                break\n            if Total == -888:\n                continue\n            Index = -99\n    Events.append(('done', Total, Index))\n")
        Blocks.append("def Fraction(Begin, End, Events):\n    Total = 0\n    Index = -23\n    for Index in range(Begin, End, -3):\n        Total += (Index * Index + 7 * Index) / 999983\n        if Index % 6 == 0:\n            Events.append((Index, Total))\n    Events.append(('done', Total, Index))\n")
        Blocks.append("Module_Events = []\nModule_Total = 0\nModule_Index = -23\nfor Module_Index in range(47, -18, -5):\n    Module_Total += Module_Index * 7\n    if Module_Index % 6 == 0:\n        Module_Events.append((Module_Index, Module_Total))\nModule_Result = (Module_Total, Module_Index, Module_Events)\n")
        Source = self._Folder / "Scalar_Strides.py"
        Source.write_text("\n".join(Blocks), encoding="utf-8")
        return Source

    def test_Span_Boundaries_Match_Independent_Iteration(self):
        Source = (self._Root / "PyCeler" / "Scalar_Region_Runtime.pxi.in").read_text(encoding="utf-8")
        Function = Source[Source.index("def _Pyceler_Region_Divisor("):].replace("object ", "")
        Namespace = {}
        exec(Function, Namespace)
        Spans = Namespace["_Pyceler_Region_Spans"]
        for Begin in range(-13, 14, 3):
            for End in range(-13, 14, 3):
                for Step in self._Steps:
                    for Period in (None, 1, 2, 3, 6, 7, 12):
                        Values = range(Begin, End, Step)
                        Actual = list(Spans(Values, Period))
                        Expected = []
                        Pending = []
                        for Index in Values:
                            Pending.append(Index)
                            if Period is not None and Index % Period == 0:
                                Expected.append(Pending)
                                Pending = []
                        if Pending:
                            Expected.append(Pending)
                        self.assertEqual([list(Span) for Span, Size in Actual], Expected, (Begin, End, Step, Period))
                        self.assertTrue(all(len(Span) == Size for Span, Size in Actual))
        Values = range(10**30, -(10**30), -3)
        Span, Size = next(Spans(Values, 7))
        self.assertEqual(list(Span), [Values[Index] for Index in range(Size)])
        self.assertEqual(Span[-1] % 7, 0)

    def test_Native_Strides_Preserve_Progress_And_Fallbacks(self):
        Source = self._Fixture()
        Findings = Analyze(Source)
        self.assertEqual(len(Findings), 12)
        self.assertTrue(all(Item.Classification == "Scalar_Numeric_Region" for Item in Findings if Item.Function is not None), Findings)
        self.assertTrue(all(Item.Classification == "Module_Scalar_Region" for Item in Findings if Item.Function is None), Findings)
        Binary = Compile(Source, self._Folder / "Native", Select=False, OpenMP=False)
        Program = (self._Root / "Test" / "Scalar_Strides_Probe.py").read_text(encoding="utf-8")
        Prefix = "import sys\nsys.path.insert(0, sys.argv[1])\nReference_Path = " + repr(str(Source)) + "\n"
        Process = subprocess.run([sys.executable, "-I", "-B", "-c", Prefix + Program, str(Binary.parent)], text=True, capture_output=True)
        self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)

    def test_Selection_Uses_Iteration_Counts_For_Descending_Regions(self):
        Source = self._Folder / "Measured_Strides.py"
        Source.write_text("raise RuntimeError('module executed during selection')\ndef Calculate(Events):\n    Total = 0\n    for Index in range(4096, -7, -4):\n        Total += Index % 97\n        if Index % 12 == 0:\n            Events.append(Total)\n    Events.append(Total)\n", encoding="utf-8")
        Output = Convert(Source, self._Folder / "Measured", OpenMP=False, Minimum_Speedup=1e12)
        Report = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(len(Report["Items"]), 1)
        Item = Report["Items"][0]
        self.assertEqual(Item["Range_Step"], -4)
        self.assertEqual(Item["Span_Maximum"], 3)
        self.assertTrue(Item["Cases"], Item)
        self.assertTrue(any(Case["Validation"].get("Serial") == "valid" for Case in Item["Cases"]), Item)
        self.assertTrue(all(Case["Size"] <= 3 for Case in Item["Cases"]), Item)

    def test_Zero_Stride_Remains_Original_And_Dynamic_Stride_Is_Extracted(self):
        Source = self._Folder / "Unknown_Strides.py"
        Source.write_text("def Zero(Events):\n    Total = 0\n    for Index in range(0, 10, 0):\n        Total += Index\n    Events.append(Total)\n\ndef Dynamic(Count, Step, Events):\n    Total = 0\n    for Index in range(0, Count, Step):\n        Total += Index\n    Events.append(Total)\n", encoding="utf-8")
        Findings = {Item.Function: Item for Item in Analyze(Source)}
        self.assertEqual(Findings["Zero"].Change, "Keep original loop")
        self.assertEqual(Findings["Dynamic"].Classification, "Scalar_Numeric_Region")
        self.assertIn("Snapshotted runtime stride", Findings["Dynamic"].Transformations)
