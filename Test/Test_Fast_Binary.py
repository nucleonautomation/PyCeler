import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Compile, Convert
from Test import Test_Fast_Math
from Test.Workspace import Temporary_Directory

class Fast_Binary_Math(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Binary_Exact_Bits_Flags_Argument_Order_Prefixes_And_Worker_State(self):
        Fixture = self._Root / "Test/Fast_Binary_Loops.py"
        Original_Bytes = Fixture.read_bytes()
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            for Parallel in (False, True):
                with self.subTest(Parallel=Parallel):
                    Source = Fixture
                    if Parallel:
                        Source = Folder / "Fast_Binary_Loops.py"
                        Source.write_text("_Pyceler_Marker = '_Pyceler_literal'\n" + Fixture.read_text(encoding="utf-8"), encoding="utf-8")
                    with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                        Converted = Convert(Source, Folder / ("Parallel_Source" if Parallel else "Serial_Source"), Select=False, OpenMP=Parallel)
                        Text = Converted.read_text(encoding="utf-8")
                        self.assertIn("copysign as ", Text)
                        self.assertIn("fmod as ", Text)
                        self.assertIn("const double[::1] I0, const double[::1] I1", Text)
                        if Parallel:
                            self.assertIn("_Pyceler_XFast_", Text)
                            self.assertIn("'_Pyceler_literal'", Text)
                        Text = Text.replace("    Scratch = <double*>", "    Scratch = NULL if _Test_Allocation_Failure else <double*>")
                        Text += Test_Fast_Math.Unboxed_Math._Rounding_Probe
                        if Parallel:
                            Text += Test_Fast_Math.Unboxed_Math._Worker_Probe
                        Converted.write_text(Text, encoding="utf-8")
                        Binary = Compile(Converted, Folder / ("Parallel" if Parallel else "Serial"), Convert=False, OpenMP=Parallel)
                        Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Fast_Binary_Probe.py"), str(Binary), str(Source), "parallel" if Parallel else "serial"], capture_output=True, text=True, timeout=180)
                    self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
                    Report = json.loads(Result.stdout)
                    self.assertGreaterEqual(Report["Comparisons"], 130)
                    self.assertEqual(len(Report["Native_Functions"]), 9)
                    self.assertEqual(len(Report["Parallel_Functions"]), 9 if Parallel else 0)
                    self.assertTrue(Report["Exact_Bits"] and Report["Caller_Flags"] and Report["Output_Identity"] and Report["Error_Identity"])
        self.assertEqual(Fixture.read_bytes(), Original_Bytes)
