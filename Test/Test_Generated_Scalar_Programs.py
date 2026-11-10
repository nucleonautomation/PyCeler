import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile
from Test.Generated_Scalar_Programs import _Programs
from Test.Workspace import Temporary_Directory

class Generated_Scalar_Programs(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Generated_AST_Combinations_Preserve_Observable_Behavior(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Generated_Programs.py"
            Text = _Programs()
            Tree = ast.parse(Text)
            self.assertEqual(len(Tree.body), 54)
            Expressions = {ast.dump(Node) for Node in ast.walk(Tree) if isinstance(Node, ast.BinOp)}
            self.assertGreater(len(Expressions), 70)
            Source.write_text(Text, encoding="utf-8")
            Findings = Analyze(Source, OpenMP=True)
            self.assertGreaterEqual(sum(Item.Change != "Keep original loop" for Item in Findings), 24)
            with patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(Folder / "Build"), "OMP_NUM_THREADS": "2", "OMP_DYNAMIC": "FALSE"}):
                for Parallel in (False, True):
                    with self.subTest(OpenMP=Parallel):
                        Binary = Compile(Source, Folder / ("Parallel" if Parallel else "Serial"), Select=False, OpenMP=Parallel)
                        Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test" / "Generated_Scalar_Probe.py"), str(Source), str(Binary)],
                                                capture_output=True, text=True, timeout=180)
                        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
                        Report = json.loads(Result.stdout)
                        self.assertEqual(Report["Generated_Programs"], 54)
                        self.assertGreater(Report["Differential_Cases"], 10000)
