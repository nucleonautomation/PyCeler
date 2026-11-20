import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile, Convert
from Test.Workspace import Temporary_Directory
# Regression checks for iterator construction, target bindings and strict mismatch.
class Iterator_Scopes(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Default_Selection_Keeps_Array_And_List_Keys(self):
        Text = (self._Root / 'Test/Iterator_Scope_Loops.py').read_text()
        Function = next(Node for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef) and Node.name == 'Both')
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Source = Folder / 'Selected_Iterator.py'
            Source.write_text('import math\n' + ast.get_source_segment(Text, Function) + '\n')
            Generated = Convert(Source, Folder / 'Cython', OpenMP=True, Workloads={'Both': dict(File=self._Root / 'Test/Iterator_Selection_Cases.py', Factory='Cases')})
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            Item = Report['Items'][0]
            self.assertEqual(Item['Kind'], 'array_region')
            self.assertIn('List_Alternative', Item)
            for Key in ('int', 'list_float'):
                self.assertTrue(any(Case['Key'] == Key and any(Value.get('Native_Entry') for Value in Case.get('Observations', {}).values()) for Case in Item['Cases']), (Key, Item))
            self.assertEqual(sum(Case.get('Holdout', False) for Case in Item['Cases']), 3)
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Program = "import importlib.util,sys,numpy as N\nS=importlib.util.spec_from_file_location('Selected_Iterator',sys.argv[1]); M=importlib.util.module_from_spec(S); S.loader.exec_module(M)\nfor Kind in ('list','float32','float64'):\n A=N.full(8192,.25,dtype='float64' if Kind=='list' else Kind); B=N.zeros_like(A)\n if Kind=='list': A,B=A.tolist(),B.tolist()\n M._Pyceler_Dispatch_Stats(True,True); M.Both(A,B); T=M._Pyceler_Dispatch_Stats().get('Totals',{}); assert T.get('Native_Entries',0)>0,(Kind,T)\nprint('All three selected storage variants entered native code')\n"
            Run = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(Binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout.strip(), flush=True)

    def test_Tuple_Scopes_And_List_Array_Backends(self):
        Source = self._Root / 'Test/Iterator_Scope_Loops.py'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Binary = Compile(Source, Path(Directory) / 'Native', Select=False, OpenMP=True)
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Iterator_Scope_Probe.py'), str(Source), str(Binary)], capture_output=True, text=True, timeout=90)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print('Iterator scopes: ' + Run.stdout.strip(), flush=True)
