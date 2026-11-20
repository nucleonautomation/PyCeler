import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile, Convert
from Test.Workspace import Temporary_Directory
# Regression checks for pure-helper local computations and unused arguments.
class Helper_Local_Selection(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Selected_Composed_Helper_Holdouts(self):
        Text = (self._Root / 'Test/Helper_Local_Loops.py').read_text()
        Definitions = [ast.get_source_segment(Text, Node) for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef) and Node.name in ('Polynomial', 'Nested', 'Heavy')]
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Source = Folder / 'Selected_Helper_Locals.py'
            Source.write_text('import math\n' + '\n'.join(Definitions) + '\n')
            Generated = Convert(Source, Folder / 'Cython', OpenMP=True, Workloads={'Heavy': dict(File=self._Root / 'Test/Iterator_Selection_Workloads.py', Factory='Helpers')})
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            Item = Report['Items'][0]
            self.assertEqual(tuple(Item['Names']), ('Source', 'Output'))
            for Key in ('int', 'list_float'):
                self.assertTrue(any(Case['Key'] == Key and any(Value.get('Native_Entry') for Value in Case.get('Observations', {}).values()) for Case in Item['Cases']), (Key, Item))
            self.assertEqual(sum(Case.get('Holdout', False) for Case in Item['Cases']), 3)
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Program = "import importlib.util,sys,numpy as N\ndef Load(Name,File):\n S=importlib.util.spec_from_file_location(Name,File); M=importlib.util.module_from_spec(S); S.loader.exec_module(M); return M\nR=Load('Reference',sys.argv[1]); M=Load('Selected_Helper_Locals',sys.argv[2])\nfor Kind in ('list','float32','float64'):\n A=N.full(8192,.125,dtype='float64' if Kind=='list' else Kind); B=N.zeros_like(A)\n if Kind=='list': A,B=A.tolist(),B.tolist()\n E=B.copy(); R.Heavy(A,E); M._Pyceler_Dispatch_Stats(True,True); V=M.Heavy(A,B); T=M._Pyceler_Dispatch_Stats().get('Totals',{}); assert T.get('Native_Entries',0)>0,(Kind,T); assert N.asarray(E).tobytes()==N.asarray(B).tobytes(),Kind; assert V is B\nprint('Exact composed-helper holdouts entered native code for all three storage variants')\n"
            Run = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(Source), str(Binary)], capture_output=True, text=True, timeout=90)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout.strip(), flush=True)
