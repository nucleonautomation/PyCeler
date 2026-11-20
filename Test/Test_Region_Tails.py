import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile
from Test.Workspace import Temporary_Directory
# Regression checks for conditional tails and bounded prefix recovery.
class Region_Tails(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Triangular_And_Conditional_Final_Bindings(self):
        Source = self._Root / 'Test/Region_Tail_Loops.py'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Binary = Compile(Source, Path(Directory) / 'Native', Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Region_Tail_Probe.py'), str(Source), str(Binary)], capture_output=True, text=True, timeout=90)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print('Region tails: ' + Run.stdout.strip(), flush=True)
