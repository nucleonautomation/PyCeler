import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from Test.Workspace import Temporary_Directory
from PyCeler import Analyze, Compile, Convert

class Scalar_Arithmetic(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test" / "Scalar_Arithmetic.py"

    def setUp(self):
        Runs = self._Root / "Test_Run"
        Runs.mkdir(exist_ok=True)
        Workspace = Temporary_Directory(dir=Runs)
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build")})
        Environment.start()
        self.addCleanup(Environment.stop)

    def test_Integer_And_Division_Candidates(self):
        Findings = Analyze(self._Fixture)
        self.assertEqual(len(Findings), 10)
        self.assertTrue(all(Item.Change != "Keep original loop" for Item in Findings))
        Text = Convert(self._Fixture, self._Folder / "Converted", Select=False).read_text(encoding="utf-8")
        self.assertIn("_Pyceler_Modulo", Text)
        self.assertIn("_Pyceler_Floor_Divide", Text)
        self.assertIn("_Pyceler_True_Divide", Text)
        self.assertIn("_Pyceler_Scalar_Rounding", Text)

    def test_Native_Arithmetic_Preserves_Python(self):
        Binary = Compile(self._Fixture, self._Folder / "Native", Select=False, OpenMP=False)
        Program = (self._Root / "Test" / "Scalar_Arithmetic_Probe.py").read_text(encoding="utf-8")
        Program = "import sys\nsys.path.insert(0, sys.argv[1])\nReference_Path = " + repr(str(self._Fixture)) + "\n" + Program
        Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent)], text=True, capture_output=True)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)

    def test_Division_With_Unsupported_Dynamic_Types_Stays_Python(self):
        Source = self._Folder / "Unsupported_Division.py"
        Source.write_text("def Dynamic(Count):\n    Total = 0\n    for Index in range(Count):\n        Total += Total + Index / 7\n    return Total\n", encoding="utf-8")
        Finding, = Analyze(Source)
        self.assertEqual(Finding.Change, "Keep original loop")
