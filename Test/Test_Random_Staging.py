import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile, Convert
from Test.Workspace import Temporary_Directory
# Regression checks for random staging.
class Random_Staging(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Missing_Or_Short_Private_Staging_Retains_Original_State(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Source = Folder / 'Random_Stage.py'
            Source.write_text('import random\ndef Run(Output: "numpy.ndarray"):\n    for Index in range(len(Output)):\n        Output[Index] = random.random()\n    return Output\n')
            Generated = Convert(Source, Folder / 'Cython', Select=False, OpenMP=True)
            Text = Generated.read_text()
            for Fault in ('missing', 'short'):
                if Fault == 'missing':
                    Before, After = 'Random_Values = &Random_View[0]', 'Random_Values = NULL'
                else:
                    Before = '        Random_Array = N.empty(Random_Total, dtype=N.float64)'
                    After = '        Random_Total = 1\n' + Before
                self.assertEqual(Text.count(Before), 1)
                File = Folder / ('Fault_' + Fault + '.pyx')
                File.write_text(Text.replace(Before, After))
                Binary = Compile(File, Folder / Fault, Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
                Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Random_Staging_Probe.py'), str(Source), str(Binary)], capture_output=True, text=True, timeout=90)
                self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
                print('Random staging ' + Fault + ': ' + Run.stdout.strip(), flush=True)
