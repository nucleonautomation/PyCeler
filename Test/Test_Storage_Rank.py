import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile, Convert
from Test.Workspace import Temporary_Directory
# Regression checks for storage rank.
class Storage_Rank(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Multidimensional_Alternatives_Use_Measured_Element_Count(self):
        Source = 'def Matrix(Source, Output):\n    for Row in range(Source.shape[0]):\n        for Column in range(Source.shape[1]):\n            Value = Source[Row, Column] * 2\n            Other = Value + 3\n            Output[Row, Column] = Other * 2\n    return Output\n'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            File = Folder / 'Matrix_Loops.py'
            File.write_text(Source, encoding='utf-8')
            Generated = Convert(File, Folder / 'Cython', OpenMP=True)
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            Item = Report['Items'][0]
            self.assertEqual(Item['Dimensions'], 2)
            Cases = [Case for Case in Item['Cases'] if Case['Key'] in ('<f4', '<f8') and Case['Size'] == 65536]
            self.assertEqual(len(Cases), 2)
            self.assertTrue(all(any(Observation.get('Native_Entry') for Observation in Case.get('Observations', {}).values()) for Case in Cases), Cases)
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Program = 'import importlib.util,sys,json,numpy as N\ndef Load(File, Name):\n    S=importlib.util.spec_from_file_location(Name,File)\n    M=importlib.util.module_from_spec(S)\n    S.loader.exec_module(M)\n    return M\nR=Load(sys.argv[1],"Reference")\nM=Load(sys.argv[2],"Matrix_Loops")\nReport=json.load(open(sys.argv[3]))\nfor D in (N.float32,N.float64,N.int32,N.int64):\n    A=(N.arange(65536)%9+1).astype(D).reshape(256,256)\n    M._Pyceler_Dispatch_Stats(True,True)\n    E=R.Matrix(A.copy(),N.zeros_like(A))\n    O=M.Matrix(A.copy(),N.zeros_like(A))\n    assert E.dtype==O.dtype and E.tobytes()==O.tobytes()\n    Stats=M._Pyceler_Dispatch_Stats()\n    Selection=Stats.get("Selection",{})\n    assert Selection.get("Size")==65536,Stats\nprint("Multidimensional storage selection: four exact outcomes and element-count observations")\n'
            Run = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(File), str(Binary), str(Generated.with_suffix('.selection.json'))], capture_output=True, text=True, timeout=60)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout, flush=True)
