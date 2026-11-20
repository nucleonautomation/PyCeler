import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile, Convert
from Test.Workspace import Temporary_Directory
# Regression checks for iterator construction, target bindings and strict mismatch.
class Iterator_Selection(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Selected_Iterator_Storage_Holdouts(self):
        Text = (self._Root / 'Test/Iterator_Loops.py').read_text()
        Function = next(Node for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef) and Node.name == 'Array_Enumerated')
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Source = Folder / 'Selected_Iterator_Region.py'
            Source.write_text('import math\n' + ast.get_source_segment(Text, Function) + '\n')
            Generated = Convert(Source, Folder / 'Cython', OpenMP=True, Workloads={'Array_Enumerated': dict(File=self._Root / 'Test/Iterator_Selection_Workloads.py', Factory='Cases')})
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            Item = Report['Items'][0]
            self.assertEqual(tuple(Item['Names']), ('Source', 'Output', 'Start'))
            for Key in ('int', 'list_float'):
                self.assertTrue(any(Case['Key'] == Key and any(Value.get('Native_Entry') for Value in Case.get('Observations', {}).values()) for Case in Item['Cases']), (Key, Item))
            self.assertEqual(sum(Case.get('Holdout', False) for Case in Item['Cases']), 3)
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Program = "import importlib.util,sys,numpy as N\ndef Load(Name,File):\n S=importlib.util.spec_from_file_location(Name,File); M=importlib.util.module_from_spec(S); S.loader.exec_module(M); return M\nR=Load('Reference',sys.argv[1]); M=Load('Selected_Iterator_Region',sys.argv[2])\nfor Kind in ('list','float32','float64'):\n A=N.full(8192,.25,dtype='float64' if Kind=='list' else Kind); B=N.zeros_like(A)\n if Kind=='list': A,B=A.tolist(),B.tolist()\n E=B.copy(); Expected=R.Array_Enumerated(A,E,-7); M._Pyceler_Dispatch_Stats(True,True); Actual=M.Array_Enumerated(A,B,-7); T=M._Pyceler_Dispatch_Stats().get('Totals',{}); assert T.get('Native_Entries',0)>0,(Kind,T); assert N.asarray(E).tobytes()==N.asarray(B).tobytes(),Kind; assert Expected[1:]==Actual[1:],Kind; assert Actual[0] is B\nprint('Exact iterator holdouts entered native code for all three storage variants')\n"
            Run = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(Source), str(Binary)], capture_output=True, text=True, timeout=90)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout.strip(), flush=True)
