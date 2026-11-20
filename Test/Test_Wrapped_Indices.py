import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Compile, Convert
from Test.Workspace import Temporary_Directory
# Regression checks for wrapped indices.
class Wrapped_Indices(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Wrapped_Addresses_And_Range_Identities(self):
        Source = self._Root / 'Test/Wrapped_Index_Cases.py'
        Changed = {Item.Function for Item in Analyze(Source, OpenMP=True) if Item.Change != 'Keep original loop'}
        self.assertTrue({'Reverse', 'Shared_Indices', 'Carried_Index', 'Index_And_Copy'} <= Changed, Changed)
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            for Parallel in (False, True):
                Binary = Compile(Source, Folder / ('Parallel' if Parallel else 'Serial'), Select=False, OpenMP=Parallel)  # Build a real extension; a static finding alone does not prove native execution.
                Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Wrapped_Index_Probe.py'), str(Source), str(Binary), 'parallel' if Parallel else 'serial'], capture_output=True, text=True, timeout=120)
                self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
                Report = json.loads(Run.stdout)
                self.assertGreater(Report['Comparisons'], 100)
                self.assertGreater(Report['Native'], 50)
                self.assertEqual(Report['Parallel'] > 0, Parallel)
                print('Wrapped indices:', Run.stdout, flush=True)

    def test_Default_Selection_Uses_Negative_Indexed_Math(self):
        Text = (self._Root / 'Test/Wrapped_Index_Cases.py').read_text()
        Function = next(Node for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef) and Node.name == 'Heavy')
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            Source = Folder / 'Wrapped_Selection.py'
            Source.write_text('import math\n' + ast.get_source_segment(Text, Function) + '\n')
            Generated = Convert(Source, Folder / 'Converted', OpenMP=True)
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            self.assertEqual(Report['Items'][0]['Status'], 'native_selected')
            Binary = Compile(Generated, Folder / 'Native', OpenMP=True, Convert=False)
            Program = "import importlib.util,sys\ndef Load(File, Name):\n    Spec=importlib.util.spec_from_file_location(Name,File)\n    M=importlib.util.module_from_spec(Spec)\n    Spec.loader.exec_module(M)\n    return M\nR=Load(sys.argv[1],'Reference')\nM=Load(sys.argv[2],'Wrapped_Selection')\nA=[0.25]*4096\nassert M.Heavy(A,[0.0]*4096,4096)==R.Heavy(A,[0.0]*4096,4096)\nS=[F() for K,F in vars(M).items() if K.startswith('_Pyceler_Fast_') and K.endswith('Stats')]\nassert sum(V['Parallel_Elements'] for V in S)>0,S\n"
            Run = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(Source), str(Binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
