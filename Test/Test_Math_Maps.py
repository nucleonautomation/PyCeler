import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from PyCeler.Math_Maps import _Math_Map_Plans
from PyCeler.Math_Registry import _Math_Registry
from Test.Math_Map_Corpus import _Math_Map_Corpus
from Test.Workspace import Temporary_Directory

class Ordered_Math_Maps(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Corpus_Plans_All_Library_Families_Without_Executing(self):
        Source, Recipes = _Math_Map_Corpus()
        Tree = ast.parse(Source)
        Before = ast.dump(Tree, include_attributes=True)
        Plans = _Math_Map_Plans(Tree, Source)
        Functions = {Edit[2].name for Edit in Plans.values()}
        self.assertTrue({Recipe["Function"] for Recipe in Recipes}.issubset(Functions))
        Prefixes = {"math": "Real_", "cmath": "Complex_", "numpy": "Numpy_", "builtins": "Builtin_"}
        Expected = {Prefixes[Record["Module"]] + Record["Name"] for Record in _Math_Registry() if Record["Kind"] == "Function" and Record["Available"] is not False and hasattr(__import__(Record["Module"]), Record["Name"])}
        self.assertEqual({Recipe["Function"] for Recipe in Recipes}, Expected)
        self.assertTrue({"Composite", "Nested", "Float32_Intermediates", "Fraction", "Literal_Identity", "Infinite_Literal", "Collision"}.issubset(Functions))
        self.assertEqual(Before, ast.dump(Tree, include_attributes=True))
        for Edit in Plans.values():
            self.assertEqual(Edit[3]["Kind"], "math_map")
            self.assertIn("GIL", Edit[3]["Numerical_Contract"])

    def test_Unproven_Control_Flow_And_Constant_Folding_Retain_Python(self):
        Sources = (
            "import math\ndef F(A, B):\n    for I in range(len(B)):\n        B[I] = math.sin(1.0 + 2.0)\n    return B\n",
            "import math\ndef F(A, B):\n    for I in range(len(B)):\n        B[I] = Unknown(math.sin(A[I]))\n    return B\n",
            "import math\ndef F(A, B):\n    for I in range(len(B)):\n        B[I] = math.sqrt(A[I - 1])\n    return B\n",
            "import math\ndef F(A, B):\n    for I in range(len(B)):\n        if I:\n            Value = math.sqrt(A[I])\n        B[I] = Value\n    return B\n",
        )
        for Source in Sources:
            with self.subTest(Source=Source):
                self.assertEqual(_Math_Map_Plans(ast.parse(Source), Source), {})

    def test_All_Math_Families_Native_Entry_And_Observable_Behavior(self):
        Source_Text, Recipes = _Math_Map_Corpus()
        (self._Root / "Test_Run").mkdir(exist_ok=True)
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Math_Coverage.py"
            Source.write_text(Source_Text, encoding="utf-8")
            Recipe_File = Folder / "Recipes.json"
            Recipe_File.write_text(json.dumps(Recipes), encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build")):
                Binary = Compile(Source, Folder / "Native", Select=False, OpenMP=False)
            for Repeat in range(3):
                with self.subTest(Repeat=Repeat):
                    Process = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test" / "Math_Maps_Probe.py"), str(Binary), str(Source), str(Recipe_File)], capture_output=True, text=True, timeout=120)
                    self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
                    Report = json.loads(Process.stdout)
                    self.assertEqual(Report["Functions"], len(Recipes))
                    self.assertGreater(Report["Functions"], 150)
                    self.assertGreater(Report["Native_Cases"], Report["Functions"])
                    self.assertGreater(Report["Mutation_Prefix"], 0)
                    self.assertGreater(Report["Cancellation_Prefix"], 0)

    def test_Shared_Checkpoint_Is_Python_And_Private_Prefix_Safe(self):
        Source_Text = "import math\n_Pyceler_User = 'literal _Pyceler_marker'\nTotal = 0\nfor Index in range(16):\n    Total += Index * Index\ndef Compute(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.sin(Source[Index])\n    return Output\ndef Ordered(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.fsum([Source[Index], 1.0])\n    return Output\n"
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Yield_Prefix.py"
            Source.write_text(Source_Text, encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build")):
                Converted = Convert(Source, Folder / "Converted", Select=False, OpenMP=False)
                Code = Converted.read_text(encoding="utf-8")
                self.assertEqual(Code.count("cdef object _Pyceler_XScheduler_Yield ="), 1)
                self.assertIn("_Pyceler_XScheduler_Yield()", Code)
                self.assertNotIn("_Pyceler_Scheduler_Yield", Code)
                self.assertIn("_Pyceler_XModule_Checkpoint(True)", Code)
                self.assertIn("_Pyceler_XModule_Checkpoint()", Code)
                Converted.write_text(Code + "\ndef _Test_Cooperate():\n    return _Pyceler_XScheduler_Yield\n", encoding="utf-8")
                Binary = Compile(Converted, Folder / "Native", Convert=False, OpenMP=False)
            Program = "import importlib.util,math,sys,types,numpy as N; S=importlib.util.spec_from_file_location('Yield_Prefix',sys.argv[1]); M=importlib.util.module_from_spec(S); S.loader.exec_module(M); assert type(M._Test_Cooperate()) is types.FunctionType; assert M._Test_Cooperate()() is None; assert M.Total==1240; A=N.array([0.25,0.5]); assert M.Compute(A,N.zeros_like(A)).tolist()==[math.sin(V) for V in A]; assert M.Ordered(A,N.zeros_like(A)).tolist()==[1.25,1.5]; assert M._Pyceler_User=='literal _Pyceler_marker'"
            Process = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)

    def test_Selection_Reports_Ordered_Math_And_Excludes_OpenMP(self):
        Source_Text = "import math\ndef Compute(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.fsum([math.sin(Source[Index]), math.cos(Source[Index])])\n    return Output\n"
        (self._Root / "Test_Run").mkdir(exist_ok=True)
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Math_Selection.py"
            Source.write_text(Source_Text, encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build")):
                Converted = Convert(Source, Folder / "Converted", OpenMP=True)
            Report = json.loads(Converted.with_suffix(".selection.json").read_text(encoding="utf-8"))
            self.assertEqual(len(Report["Items"]), 1)
            Item = Report["Items"][0]
            self.assertEqual(Item["Eligible"], ["Python", "Serial"])
            self.assertIn("OpenMP", Item["Skipped_Candidates"])
            self.assertTrue(Item.get("Cases"))
            self.assertNotEqual(Item.get("Reason"), "No native candidate built")
            self.assertIn("GIL", Item["Numerical_Contract"])

    def test_Python_Only_Selection_Preserves_Original_Constants(self):
        Source_Text = "import math\nLiteral = 1.25\ndef Compute(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.copysign(Source[Index], 1.25)\n    return Output\n"
        Probe = "import importlib.util, math, sys; S=importlib.util.spec_from_file_location('Math_Python_Only',sys.argv[1]); M=importlib.util.module_from_spec(S); S.loader.exec_module(M); Original=math.copysign; math.copysign=lambda Value,Sign: 1.0 if Sign is M.Literal else 0.0; Output=[7.0,7.0]; M.Compute([1.0,2.0],Output); math.copysign=Original; assert Output==[1.0,1.0], Output; assert not any('Math_Map_' in Name for Name in vars(M)); print('original Python retained')"
        (self._Root / "Test_Run").mkdir(exist_ok=True)
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Math_Python_Only.py"
            Source.write_text(Source_Text, encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build")):
                Binary = Compile(Source, Folder / "Native", OpenMP=False, Minimum_Speedup=1000000000)
            Process = subprocess.run([sys.executable, "-I", "-B", "-c", Probe, str(Binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
            self.assertIn("original Python retained", Process.stdout)

if __name__ == "__main__":
    unittest.main()
