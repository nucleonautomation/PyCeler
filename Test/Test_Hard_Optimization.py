import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Compile
from PyCeler.Math_Maps import _Math_Map_Plans
from Test.Workspace import Temporary_Directory
# Regression checks for hard optimization.
class Hard_Optimization(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Math_Workloads_Prioritize_Unboxed_Dtype_Without_Dropping_Cases(self):
        from PyCeler.Selection_Worker import _Cases
        Item = dict(Kind="array", Dimensions=3, Arrays=[0, 1], Arguments=2, Pixel_Dtypes=True)
        Reference = list(_Cases(Item))
        Actual = list(_Cases(dict(Item, Unboxed_Math=("sin", "cos"))))
        self.assertEqual([Case[0] for Case in Actual[:3]], ["<f8"] * 3)
        self.assertEqual([Case[1] for Case in Actual[:3]], [16, 2048, 65536])
        self.assertEqual(sorted((Key, Size, Shape) for Key, Size, Shape, Args in Reference), sorted((Key, Size, Shape) for Key, Size, Shape, Args in Actual))
        Expected = {(Key, Size): Args for Key, Size, Shape, Args in Reference}
        for Key, Size, Shape, Args in Actual:
            for Left, Right in zip(Expected[Key, Size], Args):
                self.assertEqual(Left.dtype, Right.dtype)
                self.assertEqual(Left.tobytes(), Right.tobytes())

    def test_Hard_Families_Have_Unboxed_Or_Array_Kernels(self):
        Source = self._Root / "Test/Hard_Optimization_Loops.py"
        Plans = _Math_Map_Plans(ast.parse(Source.read_text(encoding="utf-8")))
        self.assertEqual({Plan[2].name for Plan in Plans.values() if Plan[3].get("Fast_Math")}, {"Math_Chain", "Math_Ordered", "Math_Branch", "Math_Conditional", "Math_Nested", "Math_Nested_Branch", "Math_Branch_Output", "Math_Logical", "Math_Volume"})
        Findings = Analyze(Source, OpenMP=True)
        self.assertTrue(all(Item.Change != "Keep original loop" for Item in Findings), Findings)

    def test_Compiled_Hard_Cases_Preserve_Results_And_Enter_Native(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Result = subprocess.run([sys.executable, "-B", str(self._Root / "Test/Exercise_Hard_Optimization.py"), "--output", Directory], capture_output=True, text=True, timeout=300, cwd=self._Root)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
            for Variant in ("Serial", "Parallel"):
                Report = json.loads((Path(Directory) / (Variant + ".json")).read_text(encoding="utf-8"))
                self.assertEqual(len(Report["Functions"]), 11)
                self.assertGreaterEqual(Report["Comparisons"], 80)

    def test_Mutating_Shape_Bindings_Cannot_Flatten_Later_Rows(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Shape_Mutation.py"
            Source.write_text("def Compute(Source, Output):\n    Width = Source.shape[1]\n    for Row in range(Source.shape[0]):\n        for Column in range(Width):\n            Width = 2\n            Output[Row, Column] = Source[Row, Column] + 1\n    return Output\n", encoding="utf-8")
            self.assertTrue(all(Item.Classification == 'Guarded_Array_Region' for Item in Analyze(Source)))
            Binary = Compile(Source, Folder / "Native", Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Program = "import sys\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nfrom Test.Hard_Optimization_Probe import _Load\nimport numpy as N\nOriginal, Native = _Load(Path(sys.argv[2]),'Reference'), _Load(Path(sys.argv[3]),'Shape_Mutation')\nfor Dtype in (N.int64, N.float32, N.float64):\n    Expected, Actual = N.zeros((3,4),dtype=Dtype), N.zeros((3,4),dtype=Dtype)\n    Original.Compute(N.ones_like(Expected),Expected)\n    Native.Compute(N.ones_like(Actual),Actual)\n    assert Expected.dtype == Actual.dtype and Expected.tobytes() == Actual.tobytes(),(Expected,Actual)\n    assert Actual.tolist()==[[2,2,2,2],[2,2,0,0],[2,2,0,0]]\nStats = [Value() for Name, Value in vars(Native).items() if Name.startswith('_Pyceler_Fast_') and Name.endswith('Stats')]\nassert sum(Value['Native_Elements'] for Value in Stats) > 0\nassert sum(Value['Parallel_Elements'] for Value in Stats) == 0\n"
            Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(self._Root), str(Source), str(Binary)], capture_output=True, text=True, timeout=120)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
