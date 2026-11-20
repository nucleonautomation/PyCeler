import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile
from Test.Scalar_Promotion_Cases import Source
from Test.Workspace import Temporary_Directory
# Regression checks for mixed scalar types and NumPy promotion.
class Scalar_Promotion(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Integer_Parameters_Promote_Only_At_Floating_Operations(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            File = Folder / 'Promotion_Loops.py'
            File.write_text(Source(), encoding='utf-8')
            Binary = Compile(File, Folder / 'Native', Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Program = '''import importlib.util,sys,numpy as N
sys.path.insert(0,sys.argv[3])
from Array_Region_Probe import Observe,_Copy
def Load(File,Name):
    S=importlib.util.spec_from_file_location(Name,File)
    M=importlib.util.module_from_spec(S)
    S.loader.exec_module(M)
    return M
R=Load(sys.argv[1],"Reference")
M=Load(sys.argv[2],"Promotion_Loops")
class Integer(int):
    pass
Count=0
Positive=0
for Name in vars(R):
    if Name.startswith("_") or Name == "math":
        continue
    for Kind in ((float,) if Name.endswith("_List") else (N.float32,N.float64)):
        for Factor in (2,2.0,-3,2**50,2**60+1,Integer(2)):
            Size=4096
            A=[I*0.125 for I in range(Size)]
            O=[0.0]*Size
            if Kind is not float:
                A,O=N.array(A,dtype=Kind),N.array(O,dtype=Kind)
            Args=(A,O,Factor,Size)
            M._Pyceler_Dispatch_Stats(True,True)
            E=Observe(getattr(R,Name),(*_Copy((A,O)),Factor,Size))
            V=Observe(getattr(M,Name),(*_Copy((A,O)),Factor,Size))
            assert E==V,(Name,Kind,Factor,E[1:],V[1:])
            X=M._Pyceler_Dispatch_Stats().get("Execution",{})
            Required=type(Factor) is int and abs(Factor)<=2**50 and not Name.startswith("Integer_First")
            if Required:
                assert X.get("Native_Entry"),(Name,Kind,Factor,X,M._Pyceler_Guard_Stats())
                Positive+=1
            if type(Factor) is int and Name.startswith("Integer_First"):
                assert not X.get("Native_Entry"),(Name,Kind,Factor,X)
            Count+=1
print("Scalar promotion:",Count,"exact comparisons;",Positive,"required native cases")
'''
            Run = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(File), str(Binary), str(self._Root / 'Test')], capture_output=True, text=True, timeout=120)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout, flush=True)
