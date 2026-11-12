import json
import ast
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Compile, Convert
from Test import Test_Fast_Math
from Test.Workspace import Temporary_Directory

class Unboxed_Erf(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test/Fast_Erf_Loops.py"

    def test_Empty_And_Ordered_Literal_Lookups_Preserve_Floating_Status_And_Identity(self):
        Text = "import math\nScalar = 2.0\nNested = (2.0, (-0.0, 2j))\ndef Float_Literal(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = math.erf(Source[Index]) + 2.0\n    return Output\ndef Signed_Literal(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = math.copysign(Source[Index], -0.0)\n    return Output\ndef Complex_Literal(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = math.erf(Source[Index]) + (2j).real\n    return Output\ndef Tuple_Literal(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = math.erf(Source[Index]) + math.fsum((2.0, -0.0))\n    return Output\ndef Scalar_Identity(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = math.copysign(Source[Index], 2.0)\n    return Output\ndef Tuple_Identity(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = math.fsum((2.0, (-0.0, 2j)))\n    return Output\n"
        Text = Text.replace("Nested = (2.0, (-0.0, 2j))", "Nested = (2.0, (-0.0, 5e-324, 5e-324j))").replace("math.fsum((2.0, (-0.0, 2j)))", "math.fsum((2.0, (-0.0, 5e-324, 5e-324j)))")
        for Name, Value in (("Tiny_Literal", "5e-324"), ("Tiny_Negative", "-5e-324"), ("Complex_Tiny", "(5e-324j).imag")):
            Text += f"def {Name}(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = math.erf(Source[Index]) + {Value}\n    return Output\n"
        Program = '''import importlib.util,json,sys,types
import numpy as N
def Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module
Original = Load('Reference', sys.argv[2])
Native = Load('Erf_Literals', sys.argv[1])
Comparisons = 0
for Disabled in (False, True):
    Native._Test_Force_Ordered(Disabled)
    for Down in (False, True):
        Previous = Native._Test_Rounding(Down)
        try:
            for Name in ('Float_Literal','Signed_Literal','Complex_Literal','Tuple_Literal','Tiny_Literal','Tiny_Negative','Complex_Tiny'):
                for Size in (0,1,9):
                    Source = N.zeros(Size)
                    Expected, Actual = N.full(Size,-12345.0), N.full(Size,-12345.0)
                    Native._Test_Floating_Status(True)
                    Python_Result = getattr(Original,Name)(Source,Expected)
                    Python_Status = Native._Test_Floating_Status(True)
                    Native_Result = getattr(Native,Name)(Source,Actual)
                    Native_Status = Native._Test_Floating_Status()
                    assert Python_Status == Native_Status, (Name,Size,Down,Disabled,Python_Status,Native_Status)
                    assert Python_Result is Expected and Native_Result is Actual
                    assert N.array_equal(Expected.view(N.uint64),Actual.view(N.uint64)), (Name,Size,Down,Disabled)
                    Comparisons += 1
        finally:
            Native._Test_Restore_Rounding(Previous)
for Module in (Original,Native):
    Module.math = types.SimpleNamespace(copysign=lambda Value,Sign,Module=Module: 1.0 if Sign is Module.Scalar else 0.0, fsum=lambda Value,Module=Module: 1.0 if Value is Module.Nested else 0.0)
    for Name in ('Scalar_Identity','Tuple_Identity'):
        Source,Output = N.zeros(3),N.zeros(3)
        Native._Test_Floating_Status(True)
        assert getattr(Module,Name)(Source,Output) is Output
        Flags = Native._Test_Floating_Status()
        assert Flags == 0, (Name,Flags)
        assert Output.tolist() == [1.0,1.0,1.0], (Name,Output)
        Comparisons += 1
print(json.dumps(dict(Comparisons=Comparisons, Exact_Bits=True, Caller_Flags=True, Original_Literal_Identity=True)))
'''
        with Temporary_Directory(dir=self._Root / "Test_Run") as Folder:
            Folder = Path(Folder)
            Source = Folder / "Erf_Literals.py"
            Source.write_text(Text, encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build")):
                Converted = Convert(Source, Folder / "Converted", Select=False, OpenMP=False)
                Generated = Converted.read_text(encoding="utf-8")
                Names = re.findall(r"(?m)^cdef bint (\w+Erf_Backend_Eligible) =", Generated)
                self.assertTrue(Names)
                Generated += Test_Fast_Math.Unboxed_Math._Rounding_Probe + "\n"
                Generated += "\n".join(f"cdef bint {Name}_Saved = {Name}" for Name in Names) + "\n"
                Generated += "def _Test_Force_Ordered(bint Disabled):\n    global " + ", ".join(Names) + "\n"
                Generated += "\n".join(f"    {Name} = False if Disabled else {Name}_Saved" for Name in Names) + "\n"
                Converted.write_text(Generated, encoding="utf-8")
                Binary = Compile(Converted, Folder / "Native", Convert=False, OpenMP=False)
            Probe = Folder / "Probe.py"
            Probe.write_text(Program, encoding="utf-8")
            Process = subprocess.run([sys.executable, "-I", "-B", str(Probe), str(Binary), str(Source)], capture_output=True, text=True, timeout=120)
            self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
            self.assertEqual(json.loads(Process.stdout)["Comparisons"], 88)

    def test_Backend_Gate_And_Bindings_Survive_Private_Prefix_Collisions(self):
        Text = "import math as Library\nfrom math import erfc as Complementary\n_Pyceler_Marker = '_Pyceler_Xliteral'\ndef Compute(_Pyceler_Source, Output):\n    for _Pyceler_Index in range(len(_Pyceler_Source)):\n        Output[_Pyceler_Index] = Library.erf(_Pyceler_Source[_Pyceler_Index]) + Complementary(_Pyceler_Source[_Pyceler_Index]) / 2.0\n    return Output\n"
        Prefix = "_Pyceler_"
        while Prefix in Text:
            Prefix += "X"
        Line = next(Node.body[0].lineno for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef))
        with Temporary_Directory(dir=self._Root / "Test_Run") as Folder:
            Folder = Path(Folder)
            Source = Folder / "Erf_Collision.py"
            Source.write_text(Text, encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                Converted = Convert(Source, Folder / "Converted", Select=False, OpenMP=True)
                Generated = Converted.read_text(encoding="utf-8")
                self.assertIn(f'const char* {Prefix}Fast_{Line}_Runtime_Version "Py_GetVersion"()', Generated)
                self.assertIn(f'if not {Prefix}Fast_{Line}_Erf_Backend_Eligible:', Generated)
                Generated += f"\ndef _Test_Backend():\n    return {Prefix}Fast_{Line}_Erf_Backend_Eligible\n"
                Converted.write_text(Generated, encoding="utf-8")
                Binary = Compile(Converted, Folder / "Native", Convert=False, OpenMP=True)
            Probe = Folder / "Probe.py"
            Probe.write_text("import importlib.util,json,sys\nfrom pathlib import Path\nimport numpy as N\ndef Load(Name, File):\n    Spec = importlib.util.spec_from_file_location(Name, File)\n    Module = importlib.util.module_from_spec(Spec)\n    Spec.loader.exec_module(Module)\n    return Module\nOriginal = Load('Reference', Path(sys.argv[2]))\nNative = Load('Erf_Collision', Path(sys.argv[1]))\nPrefix, Line = sys.argv[3], sys.argv[4]\nassert Native._Pyceler_Marker == Original._Pyceler_Marker == '_Pyceler_Xliteral'\nassert Native.Complementary is Original.Complementary\nassert Native.Library is Original.Library\nSource = N.linspace(-4.0, 4.0, 8195)\nExpected, Actual = N.empty_like(Source), N.empty_like(Source)\nOriginal.Compute(Source, Expected)\nStats = getattr(Native, Prefix + 'Fast_' + Line + '_Stats')\nDispatch = getattr(Native, Prefix + 'Dispatch_Stats')\nDispatch(True, True)\nBefore = Stats()\nassert Native.Compute(Source, Actual) is Actual\nAfter = Stats()\nExecution = Dispatch(False)['Execution']\nassert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64))\nEligible = Native._Test_Backend()\nassert Eligible == (sys.version_info[:2] in ((3,12),(3,13),(3,14)))\nassert After['Native_Elements'] - Before['Native_Elements'] == (len(Source) if Eligible else 0)\nassert After['Parallel_Elements'] - Before['Parallel_Elements'] == (len(Source) if Eligible else 0)\nassert Execution['Native_Entry'] and Execution['Actual_Team'] == (2 if Eligible else 1)\nprint(json.dumps(dict(Exact=True, Backend_Eligible=Eligible, Execution=Execution)))\n", encoding="utf-8")
            Process = subprocess.run([sys.executable, "-I", "-B", str(Probe), str(Binary), str(Source), Prefix, str(Line)], capture_output=True, text=True, timeout=120, env=dict(os.environ, OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"))
            self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
            self.assertTrue(json.loads(Process.stdout)["Exact"])

    def test_Erf_And_Erfc_Exact_Bits_Backend_Gates_And_Worker_State(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Folder:
            Folder = Path(Folder)
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                for Parallel, Disabled in ((False, False), (True, False), (True, True)):
                    with self.subTest(Parallel=Parallel, Disabled=Disabled):
                        Label = ("Parallel" if Parallel else "Serial") + ("_Disabled" if Disabled else "")
                        Converted = Convert(self._Fixture, Folder / (Label + "_Source"), Select=False, OpenMP=Parallel)
                        Text = Converted.read_text(encoding="utf-8").replace("    Scratch = <double*>", "    Scratch = NULL if _Test_Allocation_Failure else <double*>")
                        if Disabled:
                            Text = "\n".join(Line.split(" = ")[0] + " = False" if Line.startswith("cdef bint ") and "Erf_Backend_Eligible = " in Line else Line for Line in Text.splitlines()) + "\n"
                        Text += Test_Fast_Math.Unboxed_Math._Rounding_Probe + (Test_Fast_Math.Unboxed_Math._Worker_Probe if Parallel else "")
                        Line = next(Node.body[0].lineno for Node in ast.parse(self._Fixture.read_text()).body if isinstance(Node, ast.FunctionDef) and Node.name == "Map_erf")
                        Text += f"\ndef _Test_Erf_Backend():\n    return _Pyceler_Fast_{Line}_Erf_Backend_Eligible\n"
                        Converted.write_text(Text, encoding="utf-8")
                        Binary = Compile(Converted, Folder / Label, Convert=False, OpenMP=Parallel)
                        Process = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Fast_Erf_Probe.py"), str(Binary), str(self._Fixture), "parallel" if Parallel else "serial", "disabled" if Disabled else "automatic"], capture_output=True, text=True, timeout=180)
                        self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
                        Report = json.loads(Process.stdout)
                        self.assertGreaterEqual(Report["Comparisons"], 65)
                        self.assertEqual(Report["Native_Functions"], [] if not Report["Backend_Eligible"] else ["Aliased_erf", "Aliased_erfc", "Composed", "Domain_erf", "Domain_erfc", "Map_erf", "Map_erfc", "Nested", "Overflow_erfc"])
                        self.assertEqual(bool(Report["Parallel_Functions"]), Parallel and Report["Backend_Eligible"])
                        if Disabled:
                            self.assertFalse(Report["Backend_Eligible"])
                        else:
                            Poisoned = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Fast_Erf_Probe.py"), str(Binary), str(self._Fixture), "parallel" if Parallel else "serial", "poisoned"], capture_output=True, text=True, timeout=180)
                            self.assertEqual(Poisoned.returncode, 0, Poisoned.stdout + Poisoned.stderr)
                            self.assertEqual(json.loads(Poisoned.stdout)["Backend_Eligible"], Report["Backend_Eligible"])

if __name__ == "__main__":
    unittest.main()
