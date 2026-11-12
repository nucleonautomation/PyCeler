import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Compile
from Test.Survey_Source import Write_Survey, _Filters
from Test.Workspace import Temporary_Directory

class Compiled_Survey(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Complete_Survey_Uses_Native_Filters_With_Exact_Behavior(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Write_Survey(Folder / "Survey_Workload.py")
            Original = Source.read_bytes()
            self.assertTrue(1000 <= len(Original.splitlines()) <= 2000)
            Names = [Name for Name, Weights, Divisor in _Filters()]
            self.assertEqual(len(Names), 22)
            Environment = dict(PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
            with patch.dict(os.environ, Environment):
                for Parallel in (False, True):
                    with self.subTest(OpenMP=Parallel):
                        Binary = Compile(Source, Folder / ("Parallel" if Parallel else "Serial"), Select=False, OpenMP=Parallel)
                        Command = [sys.executable, "-I", "-B", str(self._Root / "Test" / "Survey_Native_Probe.py"),
                                   str(Source), str(Binary), str(int(Parallel)), str(self._Root / "Test")]
                        Process = subprocess.run(Command, capture_output=True, text=True, timeout=180)
                        self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
                        Report = json.loads(Process.stdout)
                        self.assertEqual(Report["Source_SHA256"], hashlib.sha256(Original).hexdigest())
                        self.assertEqual(Report["Oracle_Filter_Cases"], 44)
                        self.assertEqual(Report["Edge_Cases"], 12)
                        self.assertTrue(Report["Constant_Survey"])
                        self.assertEqual(Report["Pipeline_Cases"], 2)
                        self.assertEqual(Report["Uninstrumented_Pipeline_Cases"], 2)
                        self.assertEqual(Report["Native_Filter_Calls"], 44)
                        self.assertEqual(Report["Native_Filter_Names"], Names)
                        for Case in Report["Pipeline_Observations"]:
                            self.assertEqual([Entry["Function"] for Entry in Case], Names)
                            for Entry in Case:
                                self.assertTrue(Entry["Native_Entry"], Entry)
                                self.assertEqual(Entry["Reason"], "native_parallel" if Parallel else "native_serial", Entry)
                                self.assertEqual(Entry["Actual_Team"], 2 if Parallel else 1, Entry)
            self.assertEqual(Source.read_bytes(), Original)
