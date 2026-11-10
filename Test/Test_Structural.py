import os
import subprocess
import sys
from Test.Workspace import Temporary_Directory
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert

class Structural_Optimization(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Source = _Root / "Test" / "Structural_Loops.py"

    def setUp(self):
        Runs = self._Root / "Test_Run"
        Runs.mkdir(exist_ok=True)
        Temporary = Temporary_Directory(dir=Runs)
        self.addCleanup(Temporary.cleanup)
        self._Folder = Path(Temporary.name)
        Environment = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build"), "OMP_NUM_THREADS": "2"})
        Environment.start()
        self.addCleanup(Environment.stop)

    def test_Shared_Structural_Plans(self):
        Findings = Analyze(self._Source, Elide_Temporaries=True)
        Groups = {Item.Function: Item for Item in Findings}
        self.assertIn("loop_fusion", Groups["Fused_Maps"].Transformations)
        self.assertIn("loop_invariants", Groups["Invariant_Scale"].Transformations)
        self.assertIn("common_subexpressions", Groups["Repeated_Scores"].Transformations)
        self.assertIn("loop_interchange", Groups["Column_First"].Transformations)
        self.assertIn("temporary_elimination", Groups["Temporary_Pipeline"].Transformations)
        self.assertIn("loop_fusion", Groups["Implicit_Fusion"].Transformations)
        self.assertIn("loop_invariants", Groups["Explicit_None"].Transformations)
        self.assertNotEqual(Groups["Unsafe_Neighbor"].Classification, "Structural_Numeric_Map")

    def test_Allocation_Elision_Is_Explicit(self):
        Findings = Analyze(self._Source)
        self.assertFalse(any("temporary_elimination" in Item.Transformations for Item in Findings))
        Original = self._Source.read_bytes()
        Output = Convert(self._Source, self._Folder / "Converted", Select=False, Elide_Temporaries=True)
        Text = Output.read_text(encoding="utf-8")
        self.assertIn("_Allowed", Text)
        self.assertNotIn("_Pyceler_Structural_Intervals", Text)
        self.assertNotIn('Spec["Blocks"]', Text)
        self.assertIn("_Original_0", Text)
        self.assertIn("_Optimized", Text)
        self.assertEqual(self._Source.read_bytes(), Original)

    def test_Native_Structures_And_Fallbacks(self):
        for Parallel in (False, True):
            Binary = Compile(self._Source, self._Folder / str(Parallel), Select=False, OpenMP=Parallel, Elide_Temporaries=True)
            Program = (self._Root / "Test" / "Structural_Probe.py").read_text(encoding="utf-8")
            Command = "import sys\nsys.path.insert(0, sys.argv[1])\nReference_Path = " + repr(str(self._Source)) + "\n" + Program
            Process = subprocess.run([sys.executable, "-I", "-B", "-c", Command, str(Binary.parent)], text=True, capture_output=True)
            self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
            Randomized = subprocess.run([sys.executable, "-B", str(self._Root / "Test" / "Randomized_Probe.py"), "--binary", str(Binary), "--seed", "73129"], text=True, capture_output=True)
            self.assertEqual(Randomized.returncode, 0, Randomized.stdout + Randomized.stderr)

    def test_Selection_Contains_Untransformed_Control(self):
        import json
        Output = Convert(self._Source, self._Folder / "Measured", OpenMP=False, Elide_Temporaries=True, Minimum_Speedup=1e12)
        Report = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        Items = [Item for Item in Report["Items"] if Item["Kind"] == "structural"]
        self.assertTrue(Items)
        self.assertTrue(all("Serial" in Item["Eligible"] and "Optimized" in Item["Eligible"] for Item in Items))
        for Item in Items:
            self.assertTrue(Item["Cases"], Item)
            for Candidate in ("Serial", "Optimized"):
                self.assertTrue(any(Candidate in Case["Timings"] for Case in Item["Cases"]), (Item["Function"], Candidate, Item))
            self.assertFalse(any(Status.startswith("invalid") for Case in Item["Cases"] for Status in Case["Validation"].values()), Item)
        self.assertTrue(all(Case["Winner"] == "Python" for Item in Items for Case in Item["Cases"]))
        self.assertNotIn("cdef void _Pyceler_Structure_Run_", Output.read_text(encoding="utf-8"))

    def test_Shadowed_Temporary_And_Shared_Docstring_Are_Preserved(self):
        Allocation = "    Temporary = np.empty_like(Input)\n"
        Shape = "    Temporary = len(Input)\n"
        Loops = "    for Index in range(len(Input)):\n        Temporary[Index] = Input[Index]\n    for Index in range(len(Input)):\n        Output[Index] = Temporary[Index]\n    return Output\n"
        for Index, Prelude in enumerate((Allocation + Shape, Shape + Allocation)):
            Source = self._Folder / f"Shadow_{Index}.py"
            Source.write_text("import numpy as np\ndef Process(Input, Output):\n" + Prelude + Loops, encoding="utf-8")
            self.assertFalse(any(Item.Classification == "Structural_Numeric_Map" for Item in Analyze(Source, Elide_Temporaries=True)))
        Source = self._Folder / "Shared_Doc.py"
        Source.write_text('def Process(Input, Output):\n    "Preserved documentation"; Height, Width = Output.shape\n    for X in range(Width):\n        for Y in range(Height):\n            Output[Y, X] = Input[Y, X] * 2\n    return Output\n', encoding="utf-8")
        Text = Convert(Source, self._Folder / "Docs", Select=False).read_text(encoding="utf-8")
        self.assertIn('"Preserved documentation"; Height, Width', Text)
