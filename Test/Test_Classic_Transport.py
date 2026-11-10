import json
import os
import subprocess
import sys
from Test.Workspace import Temporary_Directory
import unittest
from pathlib import Path
from unittest.mock import patch
import PyCeler
from Survey_Source import _Filters, _Stencil

class Classic_Transport(unittest.TestCase):
    _Directory = Path(__file__).resolve().parent

    def test_Shared_Writes_Ordered_Sums_And_Clipped_Medians(self):
        Root = self._Directory.parent / "Test_Run"
        Root.mkdir(exist_ok=True)
        Source = self._Directory / "Classic_Dependencies.py"
        Findings = PyCeler.Analyze(Source, OpenMP=True)
        self.assertTrue(Findings and all(Loop.Change == "Keep original loop" for Loop in Findings))
        with Temporary_Directory(dir=Root) as Folder, patch.dict(os.environ, PYCELER_BUILD_DIR=str(Path(Folder) / "Build")):
            Binary = PyCeler.Compile(Source, Path(Folder) / "Native")
            Report = json.loads(Binary.with_suffix(".selection.json").read_text(encoding="utf-8"))
            self.assertEqual(Report["Items"], [])
            self.assertEqual(len(Report["Skipped"]), len(Findings))
            Command = [sys.executable, "-I", "-B", str(self._Directory / "Classic_Dependencies_Probe.py"), str(Source), str(Binary)]
            Result = subprocess.run(Command, capture_output=True, text=True, timeout=30)
            self.assertEqual(Result.returncode, 0, Result.stderr)

    def test_Region_Selection_And_Native_Behavior(self):
        Root = self._Directory.parent / "Test_Run"
        Root.mkdir(exist_ok=True)
        with Temporary_Directory(dir=Root) as Folder, patch.dict(os.environ, OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE", PYCELER_BUILD_DIR=str(Path(Folder) / "Build")):
            Work = Path(Folder)
            Source = Work / "Mixed.py"
            Stencil = next(Filter for Filter in _Filters() if Filter[0] == "Sobel_East")
            Source.write_text("import numpy as Numpy\n" + (self._Directory / "Classic_Transport_Loops.py").read_text(encoding="utf-8") + "\n" + _Stencil(*Stencil) + "\n", encoding="utf-8")
            Findings = PyCeler.Analyze(Source, OpenMP=True)
            self.assertTrue(all(Loop.Classification != "Unknown" for Loop in Findings if Loop.Change.startswith("Extract")))
            self.assertTrue(any(Loop.Function == "Visible_Counter" and "Index" in Loop.Reason for Loop in Findings))
            self.assertTrue(any(Loop.Function == "Pump" and Loop.Classification == "Ordered_IO_Loop" for Loop in Findings))
            self.assertTrue(all(Loop.Change == "Keep original loop" for Loop in Findings if Loop.Function in ("Visible_Counter", "Partial_Count")))
            Text = PyCeler.Convert(Source, Work / "Cython", Select=False, OpenMP=True).read_text(encoding="utf-8")
            for Token in ("_Pyceler_Filter_Row_", "_Pyceler_Inlier_", "_Pyceler_Copy_Span", "_Pyceler_Fill_Tail", "_Pyceler_Copy_Bytes", "_Pyceler_Chunks"):
                self.assertIn(Token, Text)
            for Name, Options in (("Serial", dict(Select=False, OpenMP=False)), ("OpenMP", dict(Select=False, OpenMP=True)), ("Selected", {})):
                with self.subTest(Layout=Name):
                    Binary = PyCeler.Compile(Source, Work / Name, **Options)
                    Command = [sys.executable, "-I", "-B", str(self._Directory / "Classic_Transport_Probe.py"), str(Source), str(Binary)]
                    Result = subprocess.run(Command, capture_output=True, text=True, timeout=40)
                    self.assertEqual(Result.returncode, 0, Result.stderr)
                    if Name == "Selected":
                        Report = json.loads(Binary.with_suffix(".selection.json").read_text(encoding="utf-8"))
                        Items = Report["Items"]
                        self.assertEqual({Item["Kind"] for Item in Items}, {"array", "projection", "row_selection", "stencil", "receive", "count", "span"})
                        self.assertEqual(sum(Item["Function"] == "Load_Fragment" for Item in Items), 2)
                        Frame = next(Item for Item in Items if Item["Function"] == "Frame_Processor.Process")
                        self.assertEqual(sorted(Axis for Position, Axis in Frame["Dimension_Args"]), [0, 1])
                        for Item in Items:
                            self.assertTrue(Item["Cases"], Item)
                            self.assertTrue(any("Serial" in Case["Timings"] for Case in Item["Cases"]), Item["Function"])
                            if "OpenMP" in Item["Eligible"]:
                                self.assertTrue(any("OpenMP" in Case["Timings"] for Case in Item["Cases"]), Item["Function"])
                            else:
                                self.assertIn("OpenMP", Item["Skipped_Candidates"])
                            self.assertFalse(any("invalid:" in Status for Case in Item["Cases"] for Status in Case["Validation"].values()))
                        Pump = next(Item for Item in Items if Item["Function"] == "Pump")
                        self.assertTrue(any(Case["Key"] == "bytearray" and "Serial" in Case["Timings"] for Case in Pump["Cases"]))
