import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile
from Test.Workspace import Temporary_Directory
# Regression checks for list storage and publication semantics.
class List_Runtime(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Large_Transactions_Preserve_Identities_Lifetimes_And_Errors(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            File = self._Root / 'Test/List_Runtime_Cases.py'
            Binary = Compile(File, Path(Directory) / 'Native', Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/List_Runtime_Probe.py'), str(File), str(Binary)], capture_output=True, text=True, timeout=120)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout, flush=True)
