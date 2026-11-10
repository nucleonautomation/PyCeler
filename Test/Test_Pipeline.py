import os
import shutil
import subprocess
import sys
from Test.Workspace import Temporary_Directory
from Test.Generated_Source import _Python_Source
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert

class Native_Pipeline(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test" / "Numeric_Loops.py"

    def setUp(self):
        Runs = self._Root / "Test_Run"
        Runs.mkdir(exist_ok=True)
        Workspace = Temporary_Directory(dir=Runs)
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        self._Source = self._Folder / "Numeric_Loops.py"
        shutil.copyfile(self._Fixture, self._Source)
        Environment = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build"), "OMP_NUM_THREADS": "2"})
        Environment.start()
        self.addCleanup(Environment.stop)

    def _Probe(self, Output, Program):
        Command = [sys.executable, "-I", "-B", "-c", "import sys\nsys.path.insert(0, sys.argv[1])\n" + Program, str(Output)]
        Result = subprocess.run(Command, text=True, capture_output=True)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)

    def test_Preview_And_Conversion(self):
        Baseline = self._Source.read_bytes()
        Before = sorted(self._Folder.iterdir())
        Serial, Prefix = Analyze(self._Source)
        self.assertEqual(sorted(self._Folder.iterdir()), Before)
        self.assertEqual(Serial.Change, "Guarded serial zero fill")
        self.assertEqual(Prefix.Change, "Keep original loop")
        self.assertIn("OpenMP", Analyze(self._Source, OpenMP=True)[0].Change)
        Serial_Text = Convert(self._Source, Select=False).read_text(encoding="utf-8")
        Parallel_Text = Convert(self._Source, self._Folder / "Parallel", OpenMP=True, Select=False).read_text(encoding="utf-8")
        self.assertIn("cdef Py_ssize_t Size", Serial_Text)
        self.assertNotIn("prange", Serial_Text)
        self.assertIn("prange", Parallel_Text)
        self.assertIn("Values[Index] += Values[Index - 1]", _Python_Source(Parallel_Text))
        self.assertEqual(self._Source.read_bytes(), Baseline)

    def test_Native_Kernels_Against_Python(self):
        for Name, Options in (("Serial", {}), ("Parallel", {"Mode": "simple", "Python_Version": f"{sys.version_info.major}.{sys.version_info.minor}", "OpenMP": True})):
            with self.subTest(Name=Name):
                Binary = Compile(self._Source, self._Folder / Name, Select=False, **Options)
                self.assertEqual(Binary.suffix, ".pyd" if os.name == "nt" else ".so")
                Program = (self._Root / "Test" / "Native_Probe.py").read_text(encoding="utf-8")
                self._Probe(Binary.parent, "Reference_Path = " + repr(str(self._Fixture)) + "\n" + Program)

    def test_Individual_And_Grouped_Imports(self):
        Package = self._Folder / "Example"
        Package.mkdir()
        (Package / "__init__.py").write_text('"""Example."""\nfrom __future__ import annotations\nfrom .Second import Read\n', encoding="utf-8")
        (Package / "Example.py").write_text("Value = 4\n", encoding="utf-8")
        (Package / "Second.py").write_text("from . import Example\ndef Read():\n    return Example.Value\n", encoding="utf-8")
        for Link, Count in ((False, 3), (True, 1)):
            with self.subTest(Link=Link):
                Output = self._Folder / str(Link)
                Results = Compile(Package, Output, Link=Link)
                self.assertEqual(len(Results), Count)
                self.assertEqual(len([File for File in Output.rglob("*.*") if File.suffix in (".pyd", ".so")]), Count)
                self.assertEqual(len(list(Output.rglob("*.selection.json"))), 3)
                self._Probe(Output, "from Example import Read, Example\nassert Read() == 4\nExample.Value = 8\nassert Read() == 8")
        self.assertEqual(sorted(Path(Item).suffix for Item in Package.iterdir()), [".py"] * 3)

    def test_Failed_Conversion_Preserves_Previous_Output(self):
        File = Convert(self._Source, Select=False)
        Previous = File.read_bytes()
        self._Source.write_text("def (", encoding="utf-8")
        with self.assertRaises(SyntaxError):
            Convert(self._Source)
        self.assertEqual(File.read_bytes(), Previous)

    def test_Linked_Flat_Modules_And_ABI_Option(self):
        Sources = self._Folder / "Flat"
        Sources.mkdir()
        (Sources / "Left.py").write_text("Value = 5\n", encoding="utf-8")
        (Sources / "Right.py").write_text("def Call(Function, Key):\n    return Function(**{Key: 7})\n", encoding="utf-8")
        Output = self._Folder / "Linked"
        Results = Compile(Sources, Output, Link=True, Python_Version="0x030B0000")
        self.assertEqual(len(Results), 1)
        self._Probe(Output, "import Left, Right\nassert Left.Value == 5\nassert Right.Call(dict, 'x') == {'x': 7}")

    def test_Typed_Elementwise_Conversion(self):
        Source = self._Root / "Test" / "Map_Loops.py"
        Findings = Analyze(Source, OpenMP=True)
        Changes = {Item.Function: Item.Change for Item in reversed(Findings)}
        self.assertEqual(Changes["Threshold_Grid"], "Guarded 2D OpenMP element-wise kernel")
        self.assertEqual(Changes["Blend"], "Guarded 1D OpenMP element-wise kernel")
        self.assertEqual(Changes["Transpose_Into"], "Keep original loop")
        self.assertEqual(Changes["Shared_Write"], "Keep original loop")
        for Parallel in (False, True):
            with self.subTest(OpenMP=Parallel):
                Output = self._Folder / str(Parallel)
                Binary = Compile(Source, Output, OpenMP=Parallel, Select=False)
                Program = (Source.parent / "Map_Probe.py").read_text(encoding="utf-8")
                self._Probe(Binary.parent, "Reference_Path = " + repr(str(Source)) + "\n" + Program)

    def test_Nested_For_And_While_Loops(self):
        Source = self._Root / "Test" / "Loop_Workloads.py"
        Findings = Analyze(Source, OpenMP=True)
        Changes = {Item.Function: Item.Change for Item in reversed(Findings)}
        for Name in ("Count_Pairs", "First_Fibonacci_At_Least", "Count_Triangle", "Range_Snapshot"):
            self.assertEqual(Changes[Name], "Guarded serial integer loop")
        self.assertEqual(Changes["Checked_Product"], "Guarded exact OpenMP integer reduction with serial fallback")
        self.assertEqual(Changes["Threshold_Volume"], "Guarded 3D OpenMP element-wise kernel")
        self.assertEqual(Changes["Fill_Batch"], "Guarded 4D OpenMP element-wise kernel")
        self.assertEqual(Changes["Skip_Elements"], "Keep original loop")
        self.assertEqual(Changes["With_Callback"], "Keep original loop")
        self.assertEqual(Changes["Return_Argument"], "Extract guarded serial numeric region")
        for Parallel in (False, True):
            with self.subTest(OpenMP=Parallel):
                Binary = Compile(Source, self._Folder / str(Parallel), OpenMP=Parallel, Select=False)
                Program = (Source.parent / "Loop_Probe.py").read_text(encoding="utf-8")
                self._Probe(Binary.parent, "Reference_Path = " + repr(str(Source)) + "\n" + Program)
