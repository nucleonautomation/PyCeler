import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Compile, Convert
from Test.Survey_Source import _Stencil
from Test.Workspace import Temporary_Directory

class Dispatch_Observation(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Actual_Entry_Fallback_And_Teams_Across_Native_Families(self):
        Fixtures = {"Numeric_Loops.py": {"Clear_Elements"}, "Map_Loops.py": {"Clip_Negative"},
                    "Structural_Loops.py": {"Fused_Maps"}, "Numeric_Extensions.py": {"Clipped_Median"},
                    "Classic_Transport_Loops.py": {"Choose_Labels", "Count_Residuals", "Score_Stripes", "Load_Fragment", "Read_Exact"},
                    "Parallel_Reductions.py": {"Modulo_Total"}}
        Definitions = ["import numpy as np\nimport numpy as Numpy\nimport socket\n_Pyceler_Marker = 1\n"]
        for Filename, Names in Fixtures.items():
            Text = (self._Root / "Test" / Filename).read_text(encoding="utf-8")
            Definitions.extend(ast.get_source_segment(Text, Node) for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef) and Node.name in Names)
        Definitions.append(_Stencil("Dispatch_Filter", ((1, 1, 1), (1, 1, 1), (1, 1, 1)), 9))
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Dispatch_Kernels.py"
            Source.write_text("\n\n".join(Definitions) + "\n", encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                Converted = Convert(Source, Folder / "Converted", OpenMP=True, Select=False, Elide_Temporaries=True)
                Converted.write_text(Converted.read_text(encoding="utf-8") + "\nfrom openmp cimport omp_set_num_threads as _Test_Set\n\ndef _Test_Set_Threads(int Count):\n    _Test_Set(Count)\n", encoding="utf-8")
                Binary = Compile(Converted, Folder / "Native", OpenMP=True, Convert=False)
                Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test" / "Dispatch_Observation_Probe.py"), str(Binary)],
                                        capture_output=True, text=True, timeout=120)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
            Report = json.loads(Result.stdout)
            self.assertGreaterEqual(Report["Parallel_Families"], 8)
            self.assertGreaterEqual(Report["Serial_Families"], 3)
            self.assertGreaterEqual(Report["Fallbacks"], 3)
