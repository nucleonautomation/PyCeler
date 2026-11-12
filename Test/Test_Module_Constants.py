import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from PyCeler.Math_Maps import _Module_Constant_Anchor, _Native_Prefix
from Test.Workspace import Temporary_Directory
from Test import Test_Fast_Math

class Module_Constants(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test" / "Module_Constant_Loops.py"

    def test_Empty_And_Repeated_Module_Loops_Preserve_Floating_Status(self):
        Fixture = self._Root / "Test/Module_Constant_Flags.py"
        self.assertTrue(any(Item.Classification == "Module_Scalar_Region" for Item in Analyze(Fixture)))
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            for Parallel in (False, True):
                with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                    Converted = Convert(Fixture, Folder / ("Parallel_Source" if Parallel else "Serial_Source"), Select=False, OpenMP=Parallel)
                    Converted.write_text(Converted.read_text(encoding="utf-8") + Test_Fast_Math.Unboxed_Math._Rounding_Probe, encoding="utf-8")
                    Binary = Compile(Converted, Folder / ("Parallel" if Parallel else "Serial"), Convert=False, OpenMP=Parallel)
                Command = [sys.executable, "-I", "-B", str(self._Root / "Test/Module_Constant_Flags_Probe.py"), str(Binary), str(Fixture)]
                Result = subprocess.run(Command, capture_output=True, text=True, timeout=120)
                self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
                self.assertEqual(json.loads(Result.stdout)["Comparisons"], 16)

    def _Probe(self, File, Fields):
        Command = [sys.executable, "-I", "-B", str(self._Root / "Test" / "Module_Scalar_Probe.py"), str(File), File.name.split(".")[0], json.dumps(Fields)]
        Result = subprocess.run(Command, text=True, capture_output=True, timeout=120)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
        Line = next(Line for Line in Result.stdout.splitlines() if Line.startswith("PYCELER_MODULE_RESULT="))
        return json.loads(Line.split("=", 1)[1])

    def test_Private_Name_Renaming_Preserves_User_Text_And_Embedded_Code(self):
        Source = 'cdef object _Pyceler_Run():\n    return {"_Pyceler_User": "literal _Pyceler_marker"}\ncdef extern from *:\n    """\n    static void _Pyceler_C(void) {}\n    """\n    void _Pyceler_C()\n'
        Rewritten = _Native_Prefix(Source, "_Pyceler_X")
        self.assertIn("cdef object _Pyceler_XRun()", Rewritten)
        self.assertIn('return {"_Pyceler_User": "literal _Pyceler_marker"}', Rewritten)
        self.assertEqual(Rewritten.count("_Pyceler_XC"), 2)
        Loop = ast.parse('for _Pyceler_Index in range(2):\n    _Pyceler_Total += _Pyceler_Index\n    if _Pyceler_Index % 2 == 0:\n        from math import *\n        Events.append("literal _Pyceler_marker")\n').body[0]
        Before = ast.dump(Loop, include_attributes=True)
        Anchor = _Module_Constant_Anchor(Loop, 1, "_Pyceler_X")
        self.assertTrue(Anchor.startswith("def _Pyceler_XModule_Constants_1():"))
        self.assertIn("for _Pyceler_Index", Anchor)
        self.assertIn("literal _Pyceler_marker", Anchor)
        self.assertNotIn("import *", Anchor)
        self.assertEqual(ast.dump(Loop, include_attributes=True), Before)
        compile(Anchor, "anchor.py", "exec")

    def test_Reporting_Literal_Identity_Uses_The_Source_Constant_Pool(self):
        Findings = Analyze(self._Fixture)
        self.assertEqual(sum(Item.Classification == "Module_Scalar_Region" for Item in Findings), 4, Findings)
        Original = self._Fixture.read_bytes()
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            with patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(Folder / "Build"), "OMP_NUM_THREADS": "2"}):
                Binary = Compile(self._Fixture, Folder / "Native", Select=False, OpenMP=True)
            Results = [self._Probe(File, ["Events", "Total", "Index"]) for File in (self._Fixture, Binary)]
            self.assertIsNone(Results[0]["Error"])
            self.assertIsNone(Results[1]["Error"])
            self.assertEqual(Results[1]["Values"], Results[0]["Values"])
            self.assertTrue(all(all(Event) for Event in Results[1]["Values"]["Events"]))
            self.assertGreater(Results[1]["Native"].get("Native", 0), 0, Results[1])
            self.assertGreater(Results[1]["Native"].get("Fallbacks", 0), 0, Results[1])
        self.assertEqual(self._Fixture.read_bytes(), Original)

    def test_Reporting_Preserves_Future_Annotation_Compilation(self):
        Source_Text = "from __future__ import annotations\nEvents = []\nTotal = 0\nfor Index in range(4):\n    Total += Index * Index\n    if Index % 2 == 0:\n        def Reporter(Value: Missing_Type) -> list[Missing_Type]:\n            return [Value]\n        Events.append(Reporter.__annotations__ == {'Value': 'Missing_Type', 'return': 'list[Missing_Type]'})\n"
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Future_Module.py"
            Source.write_text(Source_Text, encoding="utf-8")
            self.assertEqual(sum(Item.Classification == "Module_Scalar_Region" for Item in Analyze(Source)), 1)
            with patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(Folder / "Build")}):
                Binary = Compile(Source, Folder / "Native", Select=False, OpenMP=False)
            Reference = self._Probe(Source, ["Events", "Total", "Index"])
            Native = self._Probe(Binary, ["Events", "Total", "Index"])
            self.assertIsNone(Native["Error"], Native)
            self.assertEqual(Native["Values"], Reference["Values"])
            self.assertEqual(Native["Values"]["Events"], [True, True])
            self.assertGreater(Native["Native"].get("Native", 0), 0, Native)
