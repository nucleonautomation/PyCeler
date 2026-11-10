import json
import os
import subprocess
import sys
from Test.Workspace import Temporary_Directory
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PyCeler import Compile, Convert
from PyCeler.Native_Build import _Build
from PyCeler.Selection_Worker import _Check, _Winner

class Measured_Selection(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Folder = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Folder.cleanup)
        self._Folder = Path(Folder.name)
        Env = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build"), "OMP_NUM_THREADS": "2"})
        Env.start()
        self.addCleanup(Env.stop)

    def test_Paired_Measurements_Prefer_Simpler_Candidates(self):
        def _Pick(Python, Serial, OpenMP):
            return _Winner({Name: {"Samples_Ns": Times} for Name, Times in zip(("Python", "Serial", "OpenMP"), (Python, Serial, OpenMP))}, 1.1)
        self.assertEqual(_Pick([100] * 5, [99] * 5, [100] * 5), "Python")
        self.assertEqual(_Pick([100] * 5, [45] * 5, [44] * 5), "Serial")
        self.assertEqual(_Pick([100] * 5, [45] * 5, [25] * 5), "OpenMP")
        self.assertEqual(_Pick([100] * 5, [45] * 5, [20, 20, 20, 50, 50]), "Serial")

    def test_Invalid_Mutations_And_Return_Identity_Are_Excluded(self):
        import numpy
        def _Reference(Source, Output):
            Output[:] = Source
            return Output
        def _Wrong(Source, Output):
            Output[:] = Source
            Source[:] = 0
            return Output.copy()
        Modules = {"Python": SimpleNamespace(Item=_Reference), "Serial": SimpleNamespace(Item=_Wrong)}
        Item = dict(Probe="Item", Kind="array", Destination=1, Eligible=list(Modules))
        Cases = [("<i4", 4, (4,), (numpy.arange(4), numpy.zeros(4)))]
        with patch("PyCeler.Selection_Worker._Cases", return_value=Cases):
            Case = _Check(Item, Modules, 0, 1.1)[0]
        self.assertIn("invalid", Case["Validation"]["Serial"])
        self.assertEqual(list(Case["Timings"]), ["Python"])
        self.assertEqual(Case["Winner"], "Python")

    def test_Optional_Build_Failure_And_Stale_Report(self):
        Source = self._Root / "Test" / "Numeric_Loops.py"
        with patch("PyCeler.Engine._Build", side_effect=RuntimeError("simulated compiler failure")):
            Output = Convert(Source, self._Folder)
        Report = Output.with_suffix(".selection.json")
        Data = json.loads(Report.read_text(encoding="utf-8"))
        self.assertEqual({Build["Status"] for Build in Data["Builds"].values()}, {"compilation failed"})
        self.assertEqual(Data["Items"][0]["Fallback"], "Python")
        self.assertIn("return _Pyceler_Original_", Output.read_text(encoding="utf-8"))
        self.assertEqual(Data["Skipped"][0]["Function"], "Prefix_Sum")
        Convert(Source, self._Folder, Select=False)
        self.assertFalse(Report.exists())

    def test_End_To_End_Per_Item_Dispatch(self):
        Source = self._Folder / "Mixed.py"
        Marker = self._Folder / "Imported"
        Fixture = (self._Root / "Test" / "Numeric_Loops.py").read_text(encoding="utf-8")
        Source.write_text(f"from pathlib import Path\ndef Default():\n    Path({str(Marker)!r}).touch()\n    return 4\n" + Fixture +
                          "\ndef Count(Rows=Default(), Columns=2):\n    Total = 0\n    for Row in range(Rows):\n        for Column in range(Columns):\n            Total += Row + Column\n    return Total\n", encoding="utf-8")
        Original = Source.read_bytes()
        Binary = Compile(Source, self._Folder / "Native")
        self.assertFalse(Marker.exists())
        self.assertEqual(Original, Source.read_bytes())
        Data = json.loads(Binary.with_suffix(".selection.json").read_text(encoding="utf-8"))
        Items = {Item["Function"]: Item for Item in Data["Items"]}
        Clear = Items["Clear_Elements"]
        self.assertEqual(Clear["OpenMP_Team"], 2)
        self.assertEqual(len(Clear["Cases"]), 12)
        self.assertTrue(all(set(Case["Timings"]) == {"Python", "Serial", "OpenMP"} for Case in Clear["Cases"]))
        Count = Items["Count"]
        self.assertEqual(len(Count["Loop_Lines"]), 2)
        self.assertEqual(Count["Size_Arguments"], [0, 1])
        self.assertEqual(Count["Eligible"], ["Python", "Serial"])
        self.assertTrue(all("OpenMP" not in Case["Timings"] for Case in Count["Cases"]))
        self.assertEqual(Data["Skipped"][0]["Function"], "Prefix_Sum")
        Program = (self._Root / "Test" / "Selection_Probe.py").read_text(encoding="utf-8")
        for Threads in ("2", "1"):
            Process = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent), Threads], capture_output=True, text=True,
                                     env={**os.environ, "OMP_NUM_THREADS": Threads})
            self.assertEqual(Process.returncode, 0, Process.stderr)
        self.assertTrue(Marker.exists())

    def test_Failed_OpenMP_Still_Measures_Serial(self):
        Source = self._Root / "Test" / "Numeric_Loops.py"
        def _Optional(*Args):
            if Args[-1] is True:
                raise RuntimeError("simulated missing OpenMP runtime")
            return _Build(*Args)
        with patch("PyCeler.Engine._Build", side_effect=_Optional):
            Output = Convert(Source, self._Folder, Minimum_Speedup=1e12)
        Data = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(Data["Builds"]["OpenMP"]["Status"], "compilation failed")
        self.assertEqual(Data["Builds"]["Serial"]["Status"], "built")
        Cases = Data["Items"][0]["Cases"]
        self.assertEqual(len(Cases), 12)
        self.assertTrue(all(Case["Winner"] == "Python" and set(Case["Timings"]) == {"Python", "Serial"} for Case in Cases))
        self.assertNotIn("cdef bint _Pyceler_Clear", Output.read_text(encoding="utf-8"))

    def test_Broken_Item_Does_Not_Exclude_Another_Kernel(self):
        Source = self._Folder / "Two.py"
        Body = "(N):\n    Total = 0\n    for Index in range(N):\n        Total += Index\n    return Total\n"
        Source.write_text("def First" + Body + "\ndef Second" + Body, encoding="utf-8")
        def _Reject_First(Stage, Paths, *Options):
            Code = (Stage / "Sources" / Paths[0]).read_text(encoding="utf-8")
            if "def Item_1(" in Code:
                raise RuntimeError("Cython generation failed for Probe_Serial.pyx")
            return _Build(Stage, Paths, *Options)
        with patch("PyCeler.Engine._Build", side_effect=_Reject_First):
            Output = Convert(Source, self._Folder / "Result")
        Data = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(Data["Builds"]["Serial"]["Status"], "retried per item")
        First, Second = Data["Items"]
        self.assertEqual(First["Cases"], [])
        self.assertTrue(any("Serial" in Case["Timings"] for Case in Second["Cases"]))

    def test_Convert_With_No_OpenMP_And_Unbounded_Loop(self):
        Source = self._Folder / "Never.py"
        Source.write_text("def Forever(N):\n    Count = 0\n    while N > 0:\n        Count += 1\n    return Count\n", encoding="utf-8")
        Output = Convert(Source, self._Folder / "Converted", OpenMP=False)
        Data = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(set(Data["Builds"]), {"Serial"})
        self.assertTrue(Data["Items"][0]["Cases"])
        for Case in Data["Items"][0]["Cases"]:
            self.assertEqual(Case["Winner"], "Python")
            self.assertIn("inconclusive", Case["Validation"]["Python"])
        self.assertNotIn("_Pyceler_Int_Loop_", Output.read_text(encoding="utf-8"))
