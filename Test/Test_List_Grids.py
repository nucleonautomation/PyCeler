import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Compile, Convert
from Test.Workspace import Temporary_Directory
# Regression checks for nested list updates and object identity.
class List_Grids(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Recognition_And_Native_Results(self):
        Fixture = self._Root / "Test/List_Grid_Loops.py"
        Findings = Analyze(Fixture)
        self.assertEqual(sum(Item.Classification == "Guarded_List_Grid" for Item in Findings), 22, Findings)
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Generated = Convert(Fixture, Folder / "Cython", Select=False, OpenMP=True)
            Status = '\ncdef extern from "fenv.h":\n    int _Nearest "FE_TONEAREST"\n    int _Downward "FE_DOWNWARD"\n    int _All "FE_ALL_EXCEPT"\n    int _Set "fesetround"(int)\n    int _Flags "fetestexcept"(int)\n    int _Clear "feclearexcept"(int)\n\ndef Test_Rounding(Down):\n    _Set(_Downward if Down else _Nearest)\n\ndef Test_Flags(Clear=False):\n    Result = _Flags(_All)\n    if Clear:\n        _Clear(_All)\n    return Result\n'
            Generated.write_text(Generated.read_text(encoding="utf-8") + Status, encoding="utf-8")
            Binary = Compile(Generated, Folder / "Native", Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/List_Grid_Probe.py"), str(Fixture), str(Binary), str(Folder / "Results.json")], capture_output=True, text=True, timeout=180)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
            Report = json.loads((Folder / "Results.json").read_text(encoding="utf-8"))
            self.assertEqual(Report["Positive_Native_Cases"], 33)
            print("List-grid probe: " + json.dumps(Report), flush=True)

    def test_Module_State_Aliases_And_Partial_Errors(self):
        Prelude = "H, W = 8, 9\nSource = [[(R * W + C + 1) * 0.01 for C in range(W)] for R in range(H)]\nOutput = [[0.0] * W for R in range(H)]\nConstant = 0.25\nRow = Column = -1\nA = B = C = D = None\n"
        Loop = "for Row in range(1, H - 1):\n    for Column in range(1, W - 1):\n        A = Source[Row - 1][Column]\n        B = 0.25\n        C = A / Source[Row][Column]\n        D = C\n        Output[Row][Column] = D\n"
        Fields = ["Source", "Output", "Constant", "Row", "Column", "A", "B", "C", "D", "Events"]
        Modifications = ("", "Source[3][4] = 0.0\n", "Source[6][7] = 0.0\n", "Source[3] = Source[3][:2]\n", "Output = Source\n", "Events = []\nclass Marker:\n    def __del__(self):\n        Events.append((Row, Column, Output[1][1]))\nOutput[2][2] = Marker()\n")
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            for Index, Modification in enumerate(Modifications):
                Source = Folder / f"Grid_Module_{Index}.py"
                Source.write_text(Prelude + Modification + Loop, encoding="utf-8")
                self.assertEqual(sum(Item.Classification == "Guarded_List_Grid" for Item in Analyze(Source)), 2)
                Binary = Compile(Source, Folder / f"Native_{Index}", Select=False)
                Reports = []
                for File in (Source, Binary):
                    Run = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Benchmark_List_Grids.py"), "--probe", str(File), json.dumps(Fields)], capture_output=True, text=True, timeout=90)
                    self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
                    Reports.append(json.loads(Run.stdout))
                self.assertEqual(Reports[0]["State"], Reports[1]["State"], Index)
                self.assertEqual(Reports[0]["Error"], Reports[1]["Error"], Index)
                Count = sum(Value["Native_Elements"] for Value in Reports[1]["Native"].values())
                self.assertGreater(Count, 0) if Index == 0 else self.assertEqual(Count, 0)

    def test_Aliased_Values_And_Dependent_Bounds_Remain_Original(self):
        Cases = ("Output[Row][Column] = Source[Row][Column]", "Output[Row][Column] = 1.5", "Output[Row][Column] = float(Source[Row][Column])")
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            File = Path(Directory) / "Retain.py"
            for Body in Cases:
                File.write_text("def Compute(Source, Output, N):\n    for Row in range(N):\n        for Column in range(N):\n            " + Body + "\n    return Output\n", encoding="utf-8")
                self.assertFalse(any(Item.Classification == "Guarded_List_Grid" for Item in Analyze(File)))
            File.write_text("def Compute(Source, Output, N):\n    for Row in range(N):\n        for Column in range(Row):\n            Output[Row][Column] = Source[Row][Column] * 0.5\n    return Output\n", encoding="utf-8")
            self.assertFalse(any(Item.Classification == "Guarded_List_Grid" for Item in Analyze(File)))
