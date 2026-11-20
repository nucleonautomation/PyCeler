import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile, Convert
from Test.Readonly_Selection_Cases import Source
from Test.Workspace import Temporary_Directory
# Regression checks for shared read-only storage and selection holdouts.
class Readonly_Selection(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Math_Map_Selects_Each_Storage_Backend_With_Holdouts(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            File = Folder / 'Selected_Readonly.py'
            File.write_text(Source(), encoding='utf-8')
            Generated = Convert(File, Folder / 'Cython', OpenMP=True, Workloads={'Transform': dict(File=self._Root / 'Test/Readonly_Selection_Cases.py', Factory='Cases')})
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            self.assertEqual(len(Report['Items']), 1)
            Item = Report['Items'][0]
            self.assertIn('List_Alternative', Item)
            Cases = Item['Cases']
            for Key in ('list_float', '<f4', '<f8'):
                self.assertTrue(any(Case['Key'] == Key and any(Value.get('Native_Entry') for Value in Case.get('Observations', {}).values()) for Case in Cases), (Key, Item))
            self.assertEqual(sum(Case.get('Holdout', False) for Case in Cases), 3)
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Readonly_Selection_Probe.py'), str(File), str(Binary)], capture_output=True, text=True, timeout=120)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print('Readonly default selection: ' + Run.stdout.strip(), flush=True)
