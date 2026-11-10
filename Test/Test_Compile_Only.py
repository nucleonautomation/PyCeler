import os
import shutil
import subprocess
import sys
from Test.Workspace import Temporary_Directory
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Compile, Convert
from PyCeler.Source_Inputs import _Source_Inputs, _Stage_Compile_Sources

class Compile_Only_Sources(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Runs = self._Root / "Test_Run"
        Runs.mkdir(exist_ok=True)
        Workspace = Temporary_Directory(dir=Runs)
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        self._Inputs = self._Folder / "Inputs"
        shutil.copytree(self._Root / "Test" / "Cython_Inputs", self._Inputs)
        Environment = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build")})
        Environment.start()
        self.addCleanup(Environment.stop)

    def _Probe(self, Output, Program):
        Result = subprocess.run([sys.executable, "-I", "-B", "-c", "import sys\nsys.path.insert(0, sys.argv[1])\n" + Program, str(Output)],
                                capture_output=True, text=True)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)

    def test_Discovery_And_Dependency_Staging(self):
        Source, Root, Files = _Source_Inputs(self._Inputs)
        self.assertEqual([File.name for File in Files], ["Native_Module.pyx", "Pure_Python.py"])
        Stage = self._Folder / "Stage"
        Paths, Supporting = _Stage_Compile_Sources(Root, Files, Stage)
        self.assertEqual(Paths, [Path("Native_Module.pyx"), Path("Pure_Python.py")])
        self.assertEqual(set(Supporting), {Path("Native_Types.pxd"), Path("Parts/Increment.pxi"), Path("Parts/Native_Value.h")})
        for File in Files:
            self.assertEqual(File.read_bytes(), (Stage / File.relative_to(Root)).read_bytes())
        (self._Inputs / "Native_Module.py").write_text("Value = 1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            _Source_Inputs(self._Inputs)

    def test_Compile_Only_Mixed_Sources(self):
        Before = {File.relative_to(self._Inputs): File.read_bytes() for File in self._Inputs.rglob("*") if File.is_file()}
        Output = self._Folder / "Native"
        Results = Compile(self._Inputs, Output, Convert=False)
        self.assertEqual(len(Results), 2)
        self.assertFalse(list(Output.rglob("*.selection.json")))
        self._Probe(Output, "from Native_Module import Transform\nfrom Pure_Python import Preserve\nassert Transform(3) == 18\nassert Preserve(5) == 7")
        self.assertEqual(Before, {File.relative_to(self._Inputs): File.read_bytes() for File in self._Inputs.rglob("*") if File.is_file()})

    def test_Standalone_Include_And_Native_Conversion(self):
        Source = self._Inputs / "Standalone.pxi"
        Converted = Convert(Source, self._Folder / "Converted")
        self.assertEqual(Converted.suffix, ".pxi")
        self.assertEqual(Converted.read_bytes(), Source.read_bytes())
        Binary = Compile(Source, self._Folder / "Standalone", Convert=False)
        self._Probe(Binary.parent, "from Standalone import Sum\nassert Sum(4, 5) == 9")
        Native_Source = self._Inputs / "Native_Module.pyx"
        Native_Converted = Convert(Native_Source, self._Folder / "Native_Converted")
        self.assertEqual(Native_Converted.read_bytes(), Native_Source.read_bytes())
        self.assertTrue((Native_Converted.parent / "Native_Types.pxd").is_file())
        self.assertTrue((Native_Converted.parent / "Parts" / "Increment.pxi").is_file())
        with self.assertRaisesRegex(ValueError, "preserve"):
            Convert(Source, Source.parent)

    def test_Compile_Only_Does_Not_Execute_Source(self):
        Source = self._Folder / "Not_Executed.py"
        Source.write_text("raise RuntimeError('Target source was executed')\n", encoding="utf-8")
        Binary = Compile(Source, self._Folder / "No_Execution", Convert=False)
        self.assertTrue(Binary.is_file())
        with self.assertRaisesRegex(ValueError, "require conversion"):
            Compile(Source, self._Folder / "Rejected", Convert=False, Workloads={})
        with self.assertRaisesRegex(ValueError, "require conversion"):
            Compile(Source, self._Folder / "Rejected", Convert=False, Elide_Temporaries=True)

    def test_Grouped_Raw_Package(self):
        Package = self._Folder / "Example"
        Package.mkdir()
        (Package / "__init__.pyx").write_text("from .Second import Read\n", encoding="utf-8")
        (Package / "Example.pyx").write_text("Value = 4\n", encoding="utf-8")
        (Package / "Second.py").write_text("from . import Example\ndef Read():\n    return Example.Value\n", encoding="utf-8")
        Output = self._Folder / "Linked"
        Results = Compile(Package, Output, Convert=False, Link=True)
        self.assertEqual(len(Results), 1)
        self._Probe(Output, "from Example import Read, Example\nassert Read() == 4\nExample.Value = 8\nassert Read() == 8")

    def test_Include_Text_Is_Not_A_Dependency(self):
        Source = self._Inputs / "Literal.pyx"
        Source.write_text('Text = """\ninclude "Missing.pxi"\n"""\ndef Read():\n    return Text\n', encoding="utf-8")
        Stage = self._Folder / "Literal_Stage"
        Paths, Supporting = _Stage_Compile_Sources(self._Inputs, [Source], Stage)
        self.assertEqual(Paths, [Path("Literal.pyx")])
        self.assertEqual(Supporting, [])

    def test_CPlus_Compile_Only(self):
        Source = self._Folder / "Native_Vector.pyx"
        Source.write_text("# distutils: language = c++\nfrom libcpp.vector cimport vector\ndef Read():\n    cdef vector[int] Values\n    Values.push_back(7)\n    return Values[0]\n", encoding="utf-8")
        Binary = Compile(Source, self._Folder / "CPlus", Convert=False, Mode="simple")
        self._Probe(Binary.parent, "from Native_Vector import Read\nassert Read() == 7")
