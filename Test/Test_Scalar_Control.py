import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from Test.Workspace import Temporary_Directory

class Scalar_Control(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test" / "Scalar_Control.py"

    def setUp(self):
        Runs = self._Root / "Test_Run"
        Runs.mkdir(exist_ok=True)
        Workspace = Temporary_Directory(dir=Runs)
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, PYCELER_BUILD_DIR=str(self._Folder / "Build"))
        Environment.start()
        self.addCleanup(Environment.stop)

    def test_Analysis_And_Generation(self):
        Findings = Analyze(self._Fixture)
        Supported = {"Dynamic_Stride", "Stride_Snapshot", "For_Else", "While_Else", "Nested_Else", "Early_Return", "Early_Constant",
                     "Tuple_Fibonacci", "Chained_And_Conditional", "Integer_Operators", "Integer_Powers", "Nested_Early_Return", "Conditional_Zero"}
        for Finding in Findings:
            if Finding.Function == "Dynamic_Division":
                self.assertEqual(Finding.Classification, "Scalar_Numeric_Loop", Finding)
            elif Finding.Function in Supported:
                self.assertEqual(Finding.Classification, "Scalar_Integer_Loop", Finding)
            else:
                self.assertNotEqual(Finding.Classification, "Scalar_Integer_Loop", Finding)
        Text = Convert(self._Fixture, self._Folder / "Converted", Select=False, OpenMP=False).read_text(encoding="utf-8")
        self.assertIn("_Pyceler_Range_Step", Text)
        self.assertIn("_Pyceler_Left_Shift", Text)
        self.assertIn("_Pyceler_Power", Text)

    def test_Native_Control_And_Fallbacks(self):
        Binary = Compile(self._Fixture, self._Folder / "Native", Select=False, OpenMP=False)
        Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test" / "Scalar_Control_Probe.py"), str(Binary), str(self._Fixture)],
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
