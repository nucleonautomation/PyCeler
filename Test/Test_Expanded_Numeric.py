import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Compile
from Test.Workspace import Temporary_Directory
# Regression checks for expanded numeric.
class Expanded_Numeric(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Volumes_Integer_Buffers_Strides_And_Carries(self):
        Source = self._Root / "Test/Expanded_Numeric_Loops.py"
        Findings = Analyze(Source)
        self.assertEqual(len({Item.Function for Item in Findings if Item.Classification == "Guarded_Numeric_Region"}), 8)
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Binary = Compile(Source, Folder / "Native", Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Expanded_Numeric_Probe.py"), str(Source), str(Binary), str(Folder / "Results.json")], capture_output=True, text=True, timeout=180)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
            Report = json.loads((Folder / "Results.json").read_text())
            self.assertEqual(Report["Comparisons"], 68)
            self.assertEqual(Report["Positive_Native_Cases"], 24)
            print("Expanded numeric probe: " + json.dumps(Report), flush=True)

    def test_Module_Carries_And_Fill_Error_Boundaries(self):
        Cases = (
            "Size = 65540\nFlags = [True] * Size\nCount = 0\nTotal = 0\nfor Position in range(Size + 2):\n    if Flags[Position]:\n        Count += 1\n        Total += Position\n",
            "Size = 65540\nFlags = [True] * Size\nfor Position in range(Size + 2):\n    Flags[Position] = False\n",
            "Size = 40\nFlags = [False] * Size\nCount = Seed = 1000\nTotal = 0\nfor Position in range(Size):\n    if Flags[Position]:\n        Count += 1\n        Total += Position\n",
            "Size = 40\nEvents = []\nclass Previous:\n    def __del__(self):\n        Events.append(Position)\nFlags = [Previous() for Item in range(Size)]\nfor Position in range(Size):\n    Flags[Position] = False\n"
        )
        Fields = ["Size", "Flags", "Count", "Seed", "Total", "Position", "Events"]
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            for Index, Text in enumerate(Cases):
                Source = Folder / f"Expanded_Module_{Index}.py"
                Source.write_text(Text)
                Binary = Compile(Source, Folder / f"Native_{Index}", Select=False)
                Reports = []
                for File in (Source, Binary):
                    Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Benchmark_Programs.py"), "--probe", str(File), json.dumps(Fields)], capture_output=True, text=True, timeout=90)
                    self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
                    Reports.append(json.loads(Result.stdout))
                self.assertEqual(Reports[0]["State"], Reports[1]["State"], Index)
                self.assertEqual(Reports[0]["Error"], Reports[1]["Error"], Index)
                if Index < 3:
                    self.assertGreater(sum(Value["Native_Elements"] for Value in Reports[1]["Native"].values()), 0, Index)

    def test_Integer_Annotations_Still_Require_Runtime_Guards(self):
        Text = "def Accumulate(Flags, Total: int):\n    for Position in range(len(Flags)):\n        if Flags[Position]:\n            Total += Position + 1\n    return Total\n"
        Program = "import copy, sys\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[3])\nfrom Expanded_Numeric_Probe import Load, Observe, Count\nReference = Load(sys.argv[1], 'Reference')\nNative = Load(sys.argv[2], 'Annotated_Carry')\nfor Value in (0, 0.5, 2**80, None):\n    Args = ([True] * 40, Value)\n    Before = Count(Native)\n    assert Observe(Reference.Accumulate, copy.deepcopy(Args)) == Observe(Native.Accumulate, copy.deepcopy(Args))\n    assert (Count(Native) > Before) == (type(Value) is int and Value == 0)\n"
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Annotated_Carry.py"
            Source.write_text(Text)
            Binary = Compile(Source, Folder / "Native", Select=False)
            Run = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Source), str(Binary), str(self._Root / "Test")], capture_output=True, text=True, timeout=90)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
