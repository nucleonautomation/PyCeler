import ast
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile
from PyCeler.Numeric_Regions import _Numeric_Region_Plan
from PyCeler.Array_Regions import _Array_Plan
from Test.Affine_Alias_Cases import Source
from Test.Workspace import Temporary_Directory
# Regression checks for affine offsets and overlapping storage.
class Affine_Aliases(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Common_Proof_Follows_Only_Stable_Preceding_Aliases(self):
        for Function in ast.parse(Source()).body:
            Available = {'Source', 'Output', 'N'}
            if Function.name.endswith('_List'):
                Plan = _Numeric_Region_Plan(Function, Function.body[0], Available, False)
            else:
                Plan = _Array_Plan(Function, Function.body[0], Available, False, {'Source', 'Output'})
            self.assertIsNotNone(Plan, Function.name)
            self.assertEqual(Plan['Parallel'], Function.name.startswith(('Direct_', 'Alias_', 'Chained_')), Function.name)

    def test_Equivalent_Indices_Preserve_Results_And_Enter_OpenMP(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            File = Folder / 'Affine_Loops.py'
            File.write_text(Source(), encoding='utf-8')
            Binary = Compile(File, Folder / 'Native', Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Program = 'import importlib.util,sys,numpy as N\nsys.path.insert(0,sys.argv[3])\nfrom Array_Region_Probe import Observe,_Copy\ndef Load(File,Name):\n    S=importlib.util.spec_from_file_location(Name,File)\n    M=importlib.util.module_from_spec(S)\n    S.loader.exec_module(M)\n    return M\nR=Load(sys.argv[1],"Reference")\nM=Load(sys.argv[2],"Affine_Loops")\nCount=0\nParallel=0\nfor Name in vars(R):\n    if Name.startswith("_"):\n        continue\n    for Size in (0,1,31,4096):\n        A=[I*0.125 for I in range(Size)]\n        O=[0.0]*(2*Size+2)\n        if Name.endswith("_Array"):\n            A,O=N.array(A),N.array(O)\n        Args=(A,O,Size)\n        M._Pyceler_Dispatch_Stats(True,True)\n        E=Observe(getattr(R,Name),_Copy(Args))\n        V=Observe(getattr(M,Name),_Copy(Args))\n        assert E==V,(Name,Size,E[1:],V[1:])\n        X=M._Pyceler_Dispatch_Stats().get("Execution",{})\n        Independent=Name.startswith(("Direct_","Alias_","Chained_"))\n        if Size==4096 and Independent:\n            assert X.get("Native_Entry") and X.get("Actual_Team",0)>1,(Name,X,M._Pyceler_Guard_Stats())\n            Parallel+=1\n        elif not Independent:\n            assert X.get("Actual_Team",0)<=1,(Name,X)\n        Count+=1\nprint("Affine aliases:",Count,"exact comparisons;",Parallel,"parallel cases")\n'
            Run = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(File), str(Binary), str(self._Root / 'Test')], capture_output=True, text=True, timeout=120)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout, flush=True)
