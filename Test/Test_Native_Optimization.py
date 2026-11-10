import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from Test.Workspace import Temporary_Directory
from PyCeler import Analyze, Compile, Convert
from PyCeler.Native_Optimizer import _Plans

class Native_Optimization(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Source = _Root / "Test" / "Typed_Fills.pyx"

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, PYCELER_BUILD_DIR=str(self._Folder / "Build"))
        Environment.start()
        self.addCleanup(Environment.stop)

    def test_Native_Proof_Rejects_Shadowing_And_Context(self):
        Text = self._Source.read_text(encoding="utf-8")
        self.assertEqual(len(_Plans(Text)), 3)
        for Prefix in ("range = custom\n", "from external cimport range\n", "include 'External.pxi'\n", "@decorate\n"):
            self.assertEqual(_Plans(Prefix + Text), [])
        self.assertEqual(_Plans('Literal = """\n' + Text + '\n"""\n'), [])
        self.assertEqual(_Plans(Text.replace("Output.shape[0]", "Output.shape[0] + 1")), [])
        Source = self._Folder / "Augmented.pyx"
        Source.write_text(Text, encoding="utf-8")
        Source.with_suffix(".pxd").write_text("cdef int Hidden\n", encoding="utf-8")
        self.assertEqual(_Plans(Text, Source), [])

    def test_Typed_Fills_Optimize_Without_Changing_Native_Behavior(self):
        Findings = Analyze(self._Source)
        self.assertEqual(sum(Item.Classification == "Native_Contiguous_Fill" for Item in Findings), 3)
        Original = Compile(self._Source, self._Folder / "Original", Convert=False)
        Optimized = Compile(self._Source, self._Folder / "Optimized", Select=False)
        Program = "\n".join(("import importlib.util, sys, numpy as N", "from pathlib import Path",
            "def Load(Name, File):", "    Spec = importlib.util.spec_from_file_location(Name + '.Typed_Fills', File)",
            "    Module = importlib.util.module_from_spec(Spec); Spec.loader.exec_module(Module); return Module",
            "Original, Optimized = Load('Original', sys.argv[1]), Load('Optimized', sys.argv[2])",
            "for Name, Dtype, Values in [('Fill_Int', N.int32, [-2147483648, 0, 2147483647]), ('Fill_Float', N.float32, [-0.0, 1.25, float('nan'), float('inf')]), ('Clear_Double', N.float64, [None])]:",
            "    for Size in (0, 1, 17, 4097):",
            "        for Value in Values:", "            A = N.ones(Size, dtype=Dtype); B = A.copy()",
            "            Tail = () if Value is None else (Value,)",
            "            assert getattr(Original, Name)(A, *Tail) is None", "            assert getattr(Optimized, Name)(B, *Tail) is None",
            "            assert A.tobytes() == B.tobytes()",
            "Original.range = Optimized.range = lambda Stop: range(Stop - 1)", "A = N.ones(8, dtype=N.int32); B = A.copy()",
            "Original.Fill_Int(A, 5); Optimized.Fill_Int(B, 5)", "assert A.tobytes() == B.tobytes()",
            "def Observe(Function, Buffer, Value):", "    try:", "        Result = Function(Buffer, Value)",
            "        return ('return', Result)", "    except Exception as Error:", "        return ('raise', type(Error), str(Error))",
            "ReadOnly = N.arange(8,dtype=N.int32); ReadOnly.setflags(write=False)",
            "for Buffer, Value in [(None, 5), (ReadOnly, 5), (N.arange(8,dtype=N.int32)[::2], 5), (N.zeros(8,dtype=N.float32), 5), (N.zeros(8,dtype=N.int32), 2**40)]:",
            "    assert Observe(Original.Fill_Int,Buffer,Value) == Observe(Optimized.Fill_Int,Buffer,Value)"))
        Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Original), str(Optimized)], capture_output=True, text=True)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)

    def test_Standalone_Include_Uses_The_Proven_Native_Subset(self):
        Source = self._Folder / "Standalone.pxi"
        Source.write_bytes(self._Source.read_bytes())
        self.assertEqual(sum(Item.Classification == "Native_Contiguous_Fill" for Item in Analyze(Source)), 3)
        Converted = Convert(Source, self._Folder / "Converted", Select=False)
        self.assertIn("_Pyceler_Native_Optimized_Fill_Int", Converted.read_text(encoding="utf-8"))
        Binary = Compile(Source, self._Folder / "Native", Select=False)
        Program = "import sys, numpy as N; sys.path.insert(0,sys.argv[1]); import Standalone; A=N.ones(17,dtype=N.int32); assert Standalone.Fill_Int(A,7) is None; assert (A==7).all()"
        Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent)], capture_output=True, text=True)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)

    def test_Native_Selection_Uses_Unchanged_Cython_Baseline(self):
        Converted = Convert(self._Source, self._Folder / "Measured", Minimum_Speedup=1e12)
        Report = json.loads(Converted.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(Report["Status"], "Measured native candidates", Report)
        self.assertEqual(len(Report["Items"]), 3)
        for Item in Report["Items"]:
            self.assertTrue(all(Case["Validation"]["Serial"] == "valid" for Case in Item["Cases"]))
            self.assertTrue(all("Original_Cython" in Case["Timings"] for Case in Item["Cases"]))
        self.assertEqual(Converted.read_bytes(), self._Source.read_bytes())
