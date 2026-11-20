import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Compile, Convert
from Test.Workspace import Temporary_Directory
# Regression checks for nested numeric control flow, list identities and partial errors.
class Numeric_Regions(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Compiled_Control_And_List_Families(self):
        Source = self._Root / "Test/Numeric_Region_Loops.py"
        Findings = Analyze(Source)
        Changed = {Item.Function for Item in Findings if Item.Classification in ("Guarded_Numeric_Region", "Guarded_Array_Region")}
        self.assertEqual(len(Changed), 11, [(Item.Function, Item.Classification) for Item in Findings])
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Generated = Convert(Source, Folder / "Cython", Select=False, OpenMP=True)
            Status = '\ncdef extern from "fenv.h":\n    int _Nearest "FE_TONEAREST"\n    int _Downward "FE_DOWNWARD"\n    int _All "FE_ALL_EXCEPT"\n    int _Set "fesetround"(int)\n    int _Flags "fetestexcept"(int)\n    int _Clear "feclearexcept"(int)\n\ndef Test_Rounding(Down):\n    _Set(_Downward if Down else _Nearest)\n\ndef Test_Flags(Clear=False):\n    Result = _Flags(_All)\n    if Clear:\n        _Clear(_All)\n    return Result\n'
            Generated.write_text(Generated.read_text(encoding="utf-8") + Status, encoding="utf-8")
            Binary = Compile(Generated, Folder / "Native", Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Run = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Numeric_Region_Probe.py"), str(Source), str(Binary), str(Folder / "Results.json")], capture_output=True, text=True, timeout=180)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            Report = json.loads((Folder / "Results.json").read_text())
            self.assertEqual(Report["Positive_Native_Cases"], 33)
            print("Numeric-region probe: " + json.dumps(Report), flush=True)

    def test_Module_Partial_State_And_Aliases(self):
        Prelude = "Size = 40\nSource = [0.1 + J * 0.01 for J in range(Size)]\nOutput = [0.0] * Size\nLiteral = 0.25\nPosition = -1\nValue = Shared = Part = None\n"
        Loop = "for Position in range(Size):\n    Part = 0.25\n    Value = Source[Position] ** 3 / (Source[Position] - 1.0)\n    Shared = Value\n    Output[Position] = Shared\n"
        Cases = ("", "Source[5] = 1.0\n", "Source[31] = 1.0\n", "Source[38] = 1.0\n", "Source[39] = 1.0\n", "Source = Source[:35]\n", "Output = Source\n", "Source[5] = 1.7e308\n")
        Fields = ["Source", "Output", "Literal", "Position", "Value", "Shared", "Part"]
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            for Index, Modification in enumerate(Cases):
                File = Folder / f"Numeric_Module_{Index}.py"
                File.write_text(Prelude + Modification + Loop)
                self.assertEqual(sum(Item.Classification == "Guarded_Numeric_Region" for Item in Analyze(File)), 1)
                Binary = Compile(File, Folder / f"Native_{Index}", Select=False)
                Reports = []
                for Pathname in (File, Binary):
                    Run = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Benchmark_List_Grids.py"), "--probe", str(Pathname), json.dumps(Fields)], capture_output=True, text=True, timeout=90)
                    self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
                    Reports.append(json.loads(Run.stdout))
                self.assertEqual(Reports[0]["State"], Reports[1]["State"], Index)
                self.assertEqual(Reports[0]["Error"], Reports[1]["Error"], Index)
                if Index == 0:
                    self.assertGreater(sum(Value["Native_Elements"] for Value in Reports[1]["Native"].values()), 0)

    def test_Unsafe_Identities_And_Outer_Break(self):
        Bodies = ("Output[I] = Source[I]", "Output[I] = 1.25", "if I == 3:\n    break\nOutput[I] = Source[I] * 2.0")
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            File = Path(Directory) / "Retain.py"
            for Body in Bodies:
                File.write_text("def Compute(Source, Output, N):\n    for I in range(N):\n" + "\n".join("        " + Line for Line in Body.splitlines()) + "\n    return Output\n")
                self.assertFalse(any(Item.Classification == "Guarded_Numeric_Region" for Item in Analyze(File)), Body)
