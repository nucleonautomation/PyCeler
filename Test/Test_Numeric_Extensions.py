import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from Test.Workspace import Temporary_Directory
from PyCeler import Analyze, Compile

class Numeric_Extensions(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Source = _Root / "Test" / "Numeric_Extensions.py"

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, PYCELER_BUILD_DIR=str(self._Folder / "Build"), OMP_NUM_THREADS="2")
        Environment.start()
        self.addCleanup(Environment.stop)

    def test_List_Allocation_Elision_Is_Explicit(self):
        Default = [Item for Item in Analyze(self._Source) if Item.Function == "Clipped_Median"]
        Enabled = [Item for Item in Analyze(self._Source, Elide_Temporaries=True) if Item.Function == "Clipped_Median"]
        self.assertTrue(Default)
        self.assertTrue(all(Item.Change == "Keep original loop" for Item in Default))
        self.assertTrue(all("row-local scratch" in Item.Change for Item in Enabled))

    def test_Clipped_Median_And_Channel_Distance_Match_Independent_Oracles(self):
        for Parallel in (False, True):
            Binary = Compile(self._Source, self._Folder / str(Parallel), Select=False, OpenMP=Parallel, Elide_Temporaries=True)
            Program = "\n".join(("import sys, numpy as N", "from pathlib import Path", "sys.path.insert(0,sys.argv[2])",
                "from PyCeler.Selection_Worker import _Load, _Observe", "sys.path.insert(0, sys.argv[1])", "import Numeric_Extensions as M",
                "Reference = _Load(Path(sys.argv[2])/'Test'/'Numeric_Extensions.py', 'Reference')",
                "Random = N.random.default_rng(2481)", "Fallbacks = []",
                "def Profile(Frame, Event, Arg):", "    if Event == 'call' and Frame.f_code.co_filename == 'Numeric_Extensions.py': Fallbacks.append(Frame.f_code.co_name)",
                "sys.setprofile(Profile)",
                "for Dtype in (N.int8, N.uint8, N.int16, N.uint16, N.int32, N.int64):",
                "    for Shape in ((0,0), (0,4), (4,0), (1,1), (1,9), (9,1), (2,2), (3,7), (19,23)):",
                "        Input = Random.integers(0, 24, size=Shape).astype(Dtype)", "        Output = N.zeros_like(Input); Expected = Output.copy()",
                "        for Y in range(Shape[0]):", "            for X in range(Shape[1]):",
                "                Values = Input[max(0,Y-1):Y+2, max(0,X-1):X+2].reshape(-1)",
                "                Expected[Y,X] = N.partition(Values, len(Values)//2)[len(Values)//2]",
                "        assert M.Clipped_Median(Input, Output) is Output", "        assert Output.tobytes() == Expected.tobytes()",
                "for Dtype in (N.int32, N.int64, N.float32, N.float64):",
                "    R, G, B = (Random.integers(0, 9, size=97).astype(Dtype) for Index in range(3))",
                "    Output = N.zeros_like(R)", "    assert M.Channel_Distance(R,G,B,Output,1,2,3) is Output",
                "    Expected = N.array([(int(R[I])-1)**2 + (int(G[I])-2)**2 + (int(B[I])-3)**2 for I in range(97)], dtype=Dtype)",
                "    assert Output.tobytes() == Expected.tobytes()", "sys.setprofile(None)", "assert not Fallbacks, Fallbacks",
                "A = N.arange(25,dtype=N.int64).reshape(5,5)", "ReadOnly = N.zeros_like(A); ReadOnly.setflags(write=False)",
                "for Args in [(A,A), (A[:4,:4],A[1:,1:]), (A,ReadOnly), (A,N.zeros((3,3),dtype=N.int64)), (A[:,::2],N.zeros_like(A[:,::2])), (A.astype(N.float64),N.zeros_like(A,dtype=N.float64))]:",
                "    assert _Observe(Reference.Clipped_Median,Args)[0] == _Observe(M.Clipped_Median,Args)[0]",
                "Extreme = N.array([N.iinfo(N.int64).min,0,N.iinfo(N.int64).max]*3,dtype=N.int64).reshape(3,3)",
                "Args = (Extreme,N.zeros_like(Extreme))", "assert _Observe(Reference.Clipped_Median,Args)[0] == _Observe(M.Clipped_Median,Args)[0]"))
            Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent), str(self._Root)], capture_output=True, text=True)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
