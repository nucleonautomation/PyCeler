import json
import math
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from PyCeler.Selection_Policy import _Selection_Table
from PyCeler.Selection_Worker import _Cases, _Representative_Cases
from Test.Workspace import Temporary_Directory

class Dynamic_Scalar_Strides(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test" / "Dynamic_Scalar_Strides.py"

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, PYCELER_BUILD_DIR=str(self._Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
        Environment.start()
        self.addCleanup(Environment.stop)

    def test_Dynamic_Function_And_Module_Strides_Are_Native_Candidates(self):
        Original = self._Fixture.read_bytes()
        Findings = Analyze(self._Fixture)
        Functions = {Item.Function: Item for Item in Findings if Item.Function is not None}
        for Name in ("Mixed", "Control", "Fraction", "Header", "Unbound", "Partial"):
            self.assertEqual(Functions[Name].Classification, "Scalar_Numeric_Region", Functions[Name])
            self.assertIn("Snapshotted runtime stride", Functions[Name].Transformations)
        Modules = [Item for Item in Findings if Item.Function is None and Item.Classification == "Module_Scalar_Region"]
        self.assertEqual(len(Modules), 1, Findings)
        Generated = Convert(self._Fixture, self._Folder / "Converted", Select=False, OpenMP=True).read_text(encoding="utf-8")
        self.assertIn(".step", Generated)
        self.assertIn("while (", Generated)
        self.assertNotIn("Module_Reduction_", Generated)
        self.assertEqual(self._Fixture.read_bytes(), Original)

    def test_Native_Strides_Preserve_Range_Snapshots_And_Continuation(self):
        for Parallel in (False, True):
            with self.subTest(OpenMP=Parallel):
                Binary = Compile(self._Fixture, self._Folder / ("OpenMP" if Parallel else "Serial"), Select=False, OpenMP=Parallel)
                Process = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test" / "Dynamic_Scalar_Strides_Probe.py"), str(Binary), str(self._Fixture)], capture_output=True, text=True, timeout=120)
                self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
                Report = json.loads(Process.stdout)
                self.assertGreater(Report["Comparisons"], 300)
                self.assertGreater(Report["Module_Statistics"]["Native"], 0)
                self.assertEqual(Report["Module_Statistics"]["Parallel"], 0)

    def test_Runtime_Stride_Selection_Cases_Have_Exact_Iteration_Sizes(self):
        for Period in (None, 1, 6, 7):
            Item = dict(Kind="scalar", Arguments=4, Size_Arguments=(0,), Range_Start_Argument=1, Range_Step=None, Range_Step_Argument=3, Range_Period=Period, Span_Maximum=None)
            Cases = list(_Cases(Item))
            self.assertEqual({Args[3] for Key, Size, Shape, Args in Cases}, {1, -1, 2, -3})
            for Key, Size, Shape, Args in Cases:
                self.assertEqual(Size, len(range(Args[1], Args[0], Args[3])))
                if Period is not None:
                    self.assertLessEqual(Size, Period // math.gcd(Args[3], Period))
        Item["Representative_Workload"] = dict(File="unused", Factory="Cases")
        for Stride in (-7, 3, 2**80):
            Args = (11, -5, 2, Stride)
            with patch("PyCeler.Selection_Worker._Factory_Cases", return_value=[dict(Args=Args)]):
                Case, = _Representative_Cases(Item)
            self.assertEqual(Case[1], len(range(Args[1], Args[0], Stride)))
        for Stride in (0, True, 1.5):
            with patch("PyCeler.Selection_Worker._Factory_Cases", return_value=[dict(Args=(10, 0, 2, Stride))]):
                with self.assertRaisesRegex(ValueError, "nonzero exact integers"):
                    _Representative_Cases(Item)

    def test_Measured_Region_Does_Not_Run_Outer_Code_Or_Callbacks(self):
        Source = self._Folder / "Measured_Dynamic_Stride.py"
        Source.write_text("raise RuntimeError('outer module executed')\ndef Compute(Begin, End, Stride, Events):\n    Total = 0\n    for Index in range(Begin, End, Stride):\n        Total += Index * Index\n        if Index % 12 == 0:\n            Events.append(Total)\n    Events.append(Total)\n", encoding="utf-8")
        Converted = Convert(Source, self._Folder / "Measured", OpenMP=True, Minimum_Speedup=1e12)
        Report = json.loads(Converted.with_suffix(".selection.json").read_text(encoding="utf-8"))
        Item, = Report["Items"]
        self.assertTrue(Item["Extracted"])
        self.assertIsNone(Item["Range_Step"])
        self.assertEqual(Item["Range_Period"], 12)
        self.assertIn("Range_Step_Argument", Item)
        self.assertEqual(Item["Eligible"], ["Python", "Serial"])
        Valid = [Case for Case in Item["Cases"] if Case["Validation"].get("Serial") == "valid"]
        self.assertTrue(Valid, Item)
        self.assertEqual({Case["Arguments"][Item["Range_Step_Argument"]] for Case in Valid}, {1, -1, 2, -3}, Item)
        self.assertTrue(all(Case["Observations"]["Serial"]["Native_Entry"] for Case in Valid), Valid)

    def test_Equal_Size_Strides_All_Contribute_To_Selection(self):
        Cases = [dict(Key="int", Size=16, Arguments=[16 * Step, 0, 2, Step], Validation=dict(Python="valid", Serial="valid"), Timings=dict(Python=dict(Samples_Ns=[100] * 5), Serial=dict(Samples_Ns=[40] * 5))) for Step in (1, -1, 2, -3)]
        self.assertEqual(_Selection_Table(Cases, 1.1), {"int": [(16, 1)]})
        for Position in range(len(Cases)):
            for Status in ("slow", "unsupported: runtime guard selected Python", "inconclusive: case pending within worker budget", "invalid: results differ"):
                with self.subTest(Stride=Cases[Position]["Arguments"][-1], Status=Status):
                    Rows = json.loads(json.dumps(Cases))
                    if Status == "slow":
                        Rows[Position]["Timings"]["Serial"]["Samples_Ns"] = [101] * 5
                    else:
                        Rows[Position]["Validation"]["Serial"] = Status
                        Rows[Position]["Timings"].pop("Serial")
                    self.assertEqual(_Selection_Table(Rows, 1.1), {"int": [(16, 0)]})

    def test_Module_Dynamic_Stride_Exceptions_Preserve_Partial_Globals(self):
        Source = self._Folder / "Dynamic_Module_Error.py"
        Source.write_text("Stride = 3\nTotal = 0\nCount = 0\nIndex = -23\nEvents = []\ntry:\n    for Index in range(0, 20, Stride):\n        Count += 1\n        Total += 20 // (9 - Index)\n        if Index % 6 == 0:\n            Events.append((Index, Total, Count))\n    else:\n        Events.append('unexpected else')\nexcept ZeroDivisionError:\n    Events.append(('error', Index, Total, Count))\nResult = (Total, Count, Index, Events)\n", encoding="utf-8")
        Binary = Compile(Source, self._Folder / "Partial", Select=False, OpenMP=True)
        Rows = []
        for File in (Source, Binary):
            Process = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test" / "Module_Scalar_Probe.py"), str(File), File.name.split(".")[0], json.dumps(["Result"])], capture_output=True, text=True, timeout=120)
            self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
            Rows.append(json.loads(next(Line for Line in Process.stdout.splitlines() if Line.startswith("PYCELER_MODULE_RESULT=")).split("=", 1)[1]))
        self.assertEqual(Rows[1]["Values"], Rows[0]["Values"])
        self.assertIsNone(Rows[1]["Error"])
        self.assertGreater(Rows[1]["Native"]["Native"], 0)
        self.assertGreater(Rows[1]["Native"]["Fallbacks"], 0)

if __name__ == "__main__":
    unittest.main()
