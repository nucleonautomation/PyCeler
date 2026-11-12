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

class Math_Unary_Signs(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Integer_And_Boolean_Negation_Preserve_Zero_Signs_And_Flags(self):
        Fixture = self._Root / "Test/Math_Unary_Sign_Loops.py"
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            for Parallel in (False, True):
                with self.subTest(Parallel=Parallel):
                    with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                        Converted = Convert(Fixture, Folder / ("Parallel_Source" if Parallel else "Serial_Source"), Select=False, OpenMP=Parallel)
                        Converted.write_text(Converted.read_text(encoding="utf-8") + Test_Fast_Math.Unboxed_Math._Rounding_Probe, encoding="utf-8")
                        Binary = Compile(Converted, Folder / ("Parallel" if Parallel else "Serial"), Convert=False, OpenMP=Parallel)
                        Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Math_Unary_Sign_Probe.py"), str(Binary), str(Fixture), "parallel" if Parallel else "serial"], capture_output=True, text=True, timeout=120)
                    self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
                    Report = json.loads(Result.stdout)
                    self.assertEqual(Report["Comparisons"], 110)
                    self.assertEqual(len(Report["Native_Functions"]), 10)
                    self.assertEqual(len(Report["Parallel_Functions"]), 10 if Parallel else 0)
                    self.assertTrue(Report["Exact_Bits"] and Report["Caller_Flags"] and Report["Output_Identity"])
