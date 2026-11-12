import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile
from PyCeler.Common_Analysis import _Definite_Bindings
from Test.Workspace import Temporary_Directory

class Branch_Bindings(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Common_Binding_Transfer_Is_Conservative(self):
        Cases = (("if Flag:\n    Value = First\nelse:\n    Value = Second", {"Value"}),
                 ("if Flag:\n    Value = First", set()),
                 ("if Flag:\n    Value: object = First\nelse:\n    Value: object = Second", {"Value"}),
                 ("if Flag:\n    Value: object\nelse:\n    Value: object", set()),
                 ("if Flag:\n    Temporary = False and (Value := First)\nelse:\n    Temporary = False and (Value := Second)", {"Temporary"}),
                 ("if Flag:\n    Left, *Middle, Right = First\nelse:\n    Left, *Middle, Right = Second", {"Left", "Middle", "Right"}),
                 ("if Flag:\n    if Other:\n        Value = First\n    else:\n        Value = Second\nelse:\n    Value = Third", {"Value"}))
        for Source, Expected in Cases:
            with self.subTest(Source=Source):
                self.assertEqual(_Definite_Bindings(ast.parse(Source).body), frozenset(Expected))
                self.assertEqual(_Definite_Bindings(ast.parse(Source).body, {"Existing"}), frozenset(Expected | {"Existing"}))
        for Source in ("for Item in First:\n    Value = Item", "try:\n    Value = First\nexcept Exception:\n    Value = Second", "with First:\n    Value = Second", "if Flag:\n    return First\nelse:\n    Value = Second", "del Value", "Value += 1", "yield First", "Value = yield First", "Value = await First"):
            self.assertIsNone(_Definite_Bindings(ast.parse(Source).body), Source)

    def test_Both_Branches_Enable_Existing_Regions_Without_Changing_Barriers(self):
        Findings = Analyze(self._Root / "Test/Branch_Bindings.py", OpenMP=True)
        for Name in ("Choose", "Nested", "Annotated", "Processor.Choose"):
            Rows = [Finding for Finding in Findings if Finding.Function == Name]
            self.assertTrue(Rows and all(Finding.Change.startswith("Extract guarded") for Finding in Rows), Rows)
        for Name in ("Partial", "Annotation_Only", "Walrus_Only", "Returning_Branch"):
            Rows = [Finding for Finding in Findings if Finding.Function == Name]
            self.assertTrue(Rows and all(Finding.Change == "Keep original loop" for Finding in Rows), Rows)

    def test_Native_Regions_Preserve_Conditions_Callbacks_And_Empty_Ranges(self):
        Source = self._Root / "Test/Branch_Bindings.py"
        Before = Source.read_bytes()
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                for Parallel in (False, True):
                    Binary = Compile(Source, Folder / ("Parallel" if Parallel else "Serial"), Select=False, OpenMP=Parallel)
                    Process = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Branch_Bindings_Probe.py"), str(Binary), str(Source), "parallel" if Parallel else "serial"], capture_output=True, text=True, timeout=180)
                    self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
                    Report = json.loads(Process.stdout)
                    self.assertEqual(Report["Comparisons"], 160)
                    self.assertEqual(Report["Native_Entries"], 32)
        self.assertEqual(Source.read_bytes(), Before)

if __name__ == "__main__":
    unittest.main()
