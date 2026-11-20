import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile
from Test.Workspace import Temporary_Directory
# Regression checks for iterator construction, target bindings and strict mismatch.
class Iterator_Regions(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Ordered_Iterator_Transactions(self):
        Source = self._Root / 'Test/Iterator_Loops.py'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Binary = Compile(Source, Path(Directory) / 'Native', Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Iterator_Probe.py'), str(Source), str(Binary)], capture_output=True, text=True, timeout=90)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print('Iterator transactions: ' + Run.stdout.strip(), flush=True)
