import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile, Convert
from Test.Workspace import Temporary_Directory

class Direct_Scopes(unittest.TestCase):
    def test_Deleted_Cells_Dead_Bindings_And_Late_Globals(self):
        Root = Path(__file__).resolve().parents[1]
        Source = Root / 'Test/Direct_Scope_Cases.py'
        with Temporary_Directory(dir=Root / 'Test_Run') as Directory:
            Generated = Convert(Source, Path(Directory) / 'Cython', Select=False, OpenMP=True)
            Text = Generated.read_text(encoding='utf-8')
            self.assertNotIn('_Pyceler_Baseline(', Text)
            self.assertNotIn('_Pyceler_Python_Builtins.exec(', Text)
            Binary = Compile(Generated, Path(Directory) / 'Native', Convert=False, OpenMP=True)
            Run = subprocess.run([sys.executable, '-I', '-B', str(Root / 'Test/Direct_Scope_Probe.py'), str(Source), str(Binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout.strip(), flush=True)
