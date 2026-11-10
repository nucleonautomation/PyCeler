import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from Test.Workspace import Temporary_Directory
from PyCeler import Analyze, Compile, Convert

class Parallel_Reductions(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test" / "Parallel_Reductions.py"

    def setUp(self):
        Runs = self._Root / "Test_Run"
        Runs.mkdir(exist_ok=True)
        Workspace = Temporary_Directory(dir=Runs)
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build"), "OMP_NUM_THREADS": "2", "OMP_DYNAMIC": "FALSE"})
        Environment.start()
        self.addCleanup(Environment.stop)

    def test_Parallel_Eligibility_Requires_Exact_Independent_Integer_Terms(self):
        Findings = {Item.Function: Item for Item in Analyze(self._Fixture, OpenMP=True)}
        for Name in ("Modulo_Total", "Signed_Total", "Reverse_Total", "Constant_Total", "Intermediate_Overflow"):
            self.assertEqual(Findings[Name].Classification, "Scalar_Integer_Reduction")
        for Name in ("Ordered_Float", "Dependent_Total", "Rebound_Index"):
            self.assertNotEqual(Findings[Name].Classification, "Scalar_Integer_Reduction")
        Text = Convert(self._Fixture, self._Folder / "Converted", Select=False, OpenMP=True).read_text(encoding="utf-8")
        self.assertIn("Result += _Pyceler_Reduction_Term_", Text)
        self.assertIn("_Pyceler_Prange(Start, End, nogil=True, schedule='static')", Text)
        Serial = Convert(self._Fixture, self._Folder / "Serial", Select=False, OpenMP=False).read_text(encoding="utf-8")
        self.assertNotIn("_Pyceler_Prange", Serial)
        self.assertIn("_Pyceler_Reduction_Serial_", Serial)
        self.assertIn("for Position in range(Start, End):", Serial)
        self.assertIn("_Pyceler_Reduction_Allowed", Serial)

    def test_Actual_OpenMP_And_Exact_Fallback(self):
        Converted = Convert(self._Fixture, self._Folder / "Converted", Select=False, OpenMP=True)
        Wrappers = "\ndef _Test_Reduction_Interval(Node, Values):\n    return _Pyceler_Reduction_Interval(Node, Values)\n\ndef _Test_Reduction_Allowed(Args, Plan):\n    return _Pyceler_Reduction_Allowed(Args, Plan)\n"
        Converted.write_text(Converted.read_text(encoding="utf-8") + Wrappers, encoding="utf-8")
        Binary = Compile(Converted, self._Folder / "Native", Convert=False, OpenMP=True)
        Program = (self._Root / "Test" / "Parallel_Reductions_Probe.py").read_text(encoding="utf-8")
        Program = "import sys\nsys.path.insert(0, sys.argv[1])\nParallel_Enabled = True\nReference_Path = " + repr(str(self._Fixture)) + "\n" + Program
        Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent)], text=True, capture_output=True, timeout=120)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
        Proof = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test" / "Scalar_Parallel_Proof_Probe.py"), str(Binary)], text=True, capture_output=True, timeout=120)
        self.assertEqual(Proof.returncode, 0, Proof.stdout + Proof.stderr)

    def test_Proof_Based_Serial_Uses_The_Same_Arithmetic_And_Guards(self):
        Binary = Compile(self._Fixture, self._Folder / "Serial", Select=False, OpenMP=False)
        Program = (self._Root / "Test" / "Parallel_Reductions_Probe.py").read_text(encoding="utf-8")
        Program = "import sys\nsys.path.insert(0, sys.argv[1])\nParallel_Enabled = False\nReference_Path = " + repr(str(self._Fixture)) + "\n" + Program
        Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent)], text=True, capture_output=True, timeout=120)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)

    def test_Measured_Team_Candidates_And_Numerical_Contract(self):
        Source = self._Folder / "Reduction.py"
        Source.write_text(self._Fixture.read_text(encoding="utf-8").split("\ndef Signed_Total", 1)[0], encoding="utf-8")
        Converted = Convert(Source, self._Folder / "Measured", OpenMP=True,
                            Workloads={"Modulo_Total": {"File": str(self._Fixture), "Factory": "Workloads"}},
                            Tuning={"Threads": [2], "Budget_Seconds": 30})
        Report = json.loads(Converted.with_suffix(".selection.json").read_text(encoding="utf-8"))
        Item, = Report["Items"]
        self.assertIn("OpenMP_2", Item["Eligible"])
        self.assertIn("Exact integer", Item["Numerical_Contract"])
        self.assertIn("proof", Item["Serial_Contract"].lower())
        self.assertEqual(Report["Builds"]["OpenMP_2"]["Status"], "built")
        self.assertTrue(any(Case.get("Validation", {}).get("OpenMP_2") == "valid" for Case in Item["Cases"]), Item)
        self.assertFalse(Item["Coverage"]["int"]["Extrapolates"])
        self.assertEqual(Item["Coverage"]["int"]["Native_Size_Ceiling"], max(Case["Size"] for Case in Item["Cases"] if Case["Key"] == "int"))
        for Case in Item["Cases"]:
            if Case.get("Validation", {}).get("OpenMP_2") == "valid":
                Observation = Case["Observations"]["OpenMP_2"]
                self.assertTrue(Observation["Native_Entry"])
                self.assertGreaterEqual(Observation["Actual_Team"], 2)
