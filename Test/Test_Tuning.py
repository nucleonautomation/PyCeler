import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from Test.Workspace import Temporary_Directory
from Test.Survey_Source import _Stencil
from PyCeler import Compile
from PyCeler.Selection_Policy import _Normalize_Tuning, _Selection_Table, _Candidate_Code, _Candidate_Name

class Candidate_Tuning(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Bounded_Configuration_And_Candidate_Codes(self):
        self.assertEqual(_Normalize_Tuning(None), {})
        self.assertEqual(_Normalize_Tuning({}), {})
        for Value in (dict(Threads=[0]), dict(Threads=[True]), dict(Tiles=[17]), dict(Budget_Seconds=float("inf")), dict(Budget_Seconds=0), dict(Unknown=1)):
            with self.assertRaises(ValueError):
                _Normalize_Tuning(Value)
        for Name in ("Python", "Serial", "Optimized", "Tiled", "OpenMP", "Tiled_16", "OpenMP_4"):
            self.assertEqual(_Candidate_Name(_Candidate_Code(Name)), Name)
        Timings = {Name: dict(Samples_Ns=[Value] * 5) for Name, Value in (("Python", 1000), ("Serial", 500), ("Tiled_16", 300), ("Tiled_32", 295), ("OpenMP_2", 200), ("OpenMP_4", 195))}
        Cases = [dict(Key="<i4", Size=4096, Validation={Name: "valid" for Name in Timings}, Timings=Timings)]
        self.assertEqual(_Selection_Table(Cases, 1.1)["<i4"], [(4096, _Candidate_Code("OpenMP_2"))])

    def test_Tuned_Filter_Profiles_Validates_And_Explains_Candidates(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Folder:
            Work = Path(Folder)
            Source = Work / "Filter.py"
            Source.write_text("import numpy as Numpy\n" + _Stencil("Filter", ((1, 1, 1), (1, 1, 1), (1, 1, 1)), 9), encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Work / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                Binary = Compile(Source, Work / "Native", Tuning=dict(Threads=[2, 4], Tiles=[16, 32], Budget_Seconds=60), Profile=True, Cache=Work / "Cache")
            Report = json.loads(Binary.with_suffix(".selection.json").read_text(encoding="utf-8"))
            self.assertEqual(set(Report["Builds"]), {"Serial", "Tiled_16", "Tiled_32", "OpenMP_2", "OpenMP_4"})
            self.assertTrue(all(Value["Status"] == "built" for Value in Report["Builds"].values()), Report["Builds"])
            Item = Report["Items"][0]
            self.assertTrue(Item["Cases"], Item)
            self.assertTrue(all(Value["Extrapolates"] and Value["Native_Size_Ceiling"] is None for Value in Item["Coverage"].values()))
            self.assertIn("extrapolate", Item["Dispatch_Validation"])
            for Key, Bands in Item["Dispatch"].items():
                Maximum = max(Case["Size"] for Case in Item["Cases"] if Case["Key"] == Key)
                self.assertNotIn([Maximum + 1, 0], Bands)
            for Name in Report["Builds"]:
                self.assertTrue(any(Case["Validation"].get(Name) == "valid" for Case in Item["Cases"]), (Name, Item))
            self.assertTrue(any(Case.get("Profile") for Case in Item["Cases"]))
            self.assertIn("Decisions", Item["Summary"])
            self.assertIn("Measured_Priorities", Report)
            Artifact = Path(Report["Cache"]["Directory"]) / "Artifacts"
            Program = "\n".join(("import sys, numpy as N", "sys.path.insert(0,sys.argv[1])", "from Filter import Filter",
                "A = (N.arange(33*35) % 17).astype(N.int32).reshape(33,35)", "M = N.ones(A.shape,dtype=bool); M[13,17] = False",
                "Expected = N.full(A.shape,-99,dtype=N.int64)", "for Y in range(1,32):", "    for X in range(1,34):",
                "        if M[Y-1:Y+2,X-1:X+2].all(): Expected[Y,X] = int(A[Y-1:Y+2,X-1:X+2].sum())//9",
                "assert N.array_equal(Filter(A,M,-99),Expected)",
                "sys.path.insert(0,sys.argv[2]); import Probe_OpenMP_4 as P", "Observed = []",
                "def Range(*Args):", "    Observed.append(P._Probe_Threads()); return range(*Args)", "P.range = Range",
                "Name = sys.argv[3]", "O = N.full(A.shape,-99,dtype=N.int64)", "getattr(P,Name)(A,M,O,*A.shape)",
                "assert Observed and set(Observed) == {2}, Observed", "assert P._Probe_Threads() == 2"))
            Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent), str(Artifact), Item["Probe"]], capture_output=True, text=True,
                                    env=dict(os.environ, OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"))
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)

    def test_Tuned_Fills_Maps_Structures_And_Medians_Validate(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Folder:
            Work = Path(Folder)
            Source = Work / "Kernels.py"
            Text = (self._Root / "Test" / "Numeric_Extensions.py").read_text(encoding="utf-8")
            Text += "\ndef Clear(Values):\n    for Index in range(len(Values)):\n        Values[Index] = 0\n    return Values\n"
            Text += "\ndef Threshold(Input, Output):\n    for Index in range(len(Input)):\n        if Input[Index] > 3:\n            Output[Index] = 1\n        else:\n            Output[Index] = 0\n    return Output\n"
            Source.write_text(Text, encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Work / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                Binary = Compile(Source, Work / "Native", Tuning=dict(Threads=[2], Budget_Seconds=60), Elide_Temporaries=True)
            Report = json.loads(Binary.with_suffix(".selection.json").read_text(encoding="utf-8"))
            self.assertTrue(all(Value["Status"] == "built" for Value in Report["Builds"].values()), Report["Builds"])
            self.assertEqual({Item["Function"] for Item in Report["Items"]}, {"Clipped_Median", "Channel_Distance", "Clear", "Threshold"})
            for Item in Report["Items"]:
                self.assertTrue(any(Case["Validation"].get("OpenMP_2") == "valid" for Case in Item["Cases"]), Item)
