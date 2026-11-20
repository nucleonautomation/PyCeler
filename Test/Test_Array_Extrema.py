import ast
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Convert, Compile
from Test.Workspace import Temporary_Directory
# Regression checks for dtype-preserving extrema, clamped indices and repeated reductions.
class Array_Extrema(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Extrema_Clamped_Indices_And_Integer_Division(self):
        Source = self._Root / 'Test/Array_Extrema_Loops.py'
        Function = next(Node for Node in ast.parse(Source.read_text()).body if isinstance(Node, ast.FunctionDef) and Node.name == 'Repeated_Scales')
        Outer = {Node.lineno for Node in Function.body if isinstance(Node, ast.For)}
        Findings = {Item.Line: Item.Classification for Item in Analyze(Source, OpenMP=True) if Item.Function == 'Repeated_Scales'}
        self.assertTrue(all(Findings[Line] == 'Guarded_Array_Region' for Line in Outer), Findings)
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Generated = Convert(Source, Path(Directory) / 'Cython', Select=False, OpenMP=True)
            Text = Generated.read_text(encoding='utf-8')
            self.assertNotIn('_Pyceler_Baseline(', Text)
            self.assertNotIn('exec(', Text)
            self.assertNotIn('compile(', Text)
            Binary = Compile(Generated, Path(Directory) / 'Native', Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Array_Extrema_Probe.py'), str(Source), str(Binary)], capture_output=True, text=True, timeout=90)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print('Array extrema: ' + Run.stdout.strip(), flush=True)
