import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Compile, Convert
from Test.Storage_Composition_Cases import Source
from Test.Workspace import Temporary_Directory
# Regression checks for competing list/array backends and runtime storage kinds.
class Storage_Composition(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def _Probe(self, File, Binary, Native):
        Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Storage_Composition_Probe.py'), str(File), str(Binary), 'native' if Native else 'fallback'], capture_output=True, text=True, timeout=90)
        self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
        Report = json.loads(Run.stdout)
        self.assertEqual(Report['Comparisons'], 93)
        print('Storage composition: ' + json.dumps({Name: Value for Name, Value in Report.items() if Name != 'Cases'}), flush=True)
        return Report

    def test_List_And_Array_Backends_Compose(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            File = Folder / 'Storage_Loops.py'
            File.write_text(Source(), encoding='utf-8')
            Binary = Compile(File, Folder / 'Native', Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Report = self._Probe(File, Binary, True)
            self.assertGreater(Report['Parallel'], 0)

    def test_Default_Selection_Preserves_Storage_Identity(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            File = Folder / 'Storage_Loops.py'
            File.write_text(Source(), encoding='utf-8')
            Workloads = {Name: dict(File=self._Root / 'Test/Storage_Composition_Cases.py', Factory='Cases') for Name in ('Transform', 'Extracted')}
            Generated = Convert(File, Folder / 'Cython', OpenMP=True, Workloads=Workloads)
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            for Item in Report['Items']:
                self.assertIn('List_Alternative', Item)
                Cases = Item['Cases']
                self.assertTrue({'list_float', 'list_integer', '<f4', '<f8', '<i4', '<i8'} <= {Case['Key'] for Case in Cases}, Item)
                for Key in ('list_float', 'list_integer', '<f4', '<f8'):
                    Entered = [Case for Case in Cases if Case['Key'] == Key and any(Value.get('Native_Entry') for Value in Case.get('Observations', {}).values())]
                    self.assertTrue(Entered, (Item['Function'], Key, Cases))
                self.assertEqual(sum(Case.get('Holdout', False) for Case in Cases), 0 if Item['Function'] == 'Whole' else 6)
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)
            self._Probe(File, Binary, False)

    def test_All_Python_Selection_Preserves_Returns(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            File = Folder / 'Storage_Loops.py'
            File.write_text(Source(), encoding='utf-8')
            with patch('PyCeler.Engine._Build', side_effect=RuntimeError('unavailable optional candidate')):
                Generated = Convert(File, Folder / 'Cython', OpenMP=True)
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)
            Report = self._Probe(File, Binary, False)
            self.assertEqual(Report['Native'], 0)
