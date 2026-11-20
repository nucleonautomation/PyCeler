import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Compile, Convert
from Test.Generalization_Cases import Source
from Test.Workspace import Temporary_Directory
# Regression checks for generalization.
class Generalization(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Default_Selection_Exercises_Nested_Parallel_Work(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Source_File = Folder / 'Nested_Selection.py'
            Source_File.write_text('import math\ndef Calculate(Source, Output, N):\n    for I in range(1, N - 1):\n        Value = 0.0\n        for J in range(256):\n            Value += math.sin(math.sqrt(abs(Source[I]) + J * 0.001))\n        Output[I] = Value\n    return Output\n', encoding='utf-8')
            Generated = Convert(Source_File, Folder / 'Cython', OpenMP=True)
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            Item = next(Item for Item in Report['Items'] if Item['Kind'] == 'numeric_region')
            Observed = [Case for Case in Item['Cases'] if Case['Observations'].get('OpenMP', {}).get('Native_Entry') and Case['Observations']['OpenMP'].get('Actual_Team', 0) > 1]
            self.assertTrue(any(Case['Size'] > 128 for Case in Observed), Item)
            self.assertEqual(Item['Status'], 'native_selected')
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Program = 'import importlib.util,sys\ndef Load(File, Name):\n    Spec=importlib.util.spec_from_file_location(Name,File)\n    Module=importlib.util.module_from_spec(Spec)\n    Spec.loader.exec_module(Module)\n    return Module\nR=Load(sys.argv[1],"Reference")\nM=Load(sys.argv[2],"Nested_Selection")\nN=4096\nA=[0.01+I*0.0001 for I in range(N)]\nassert R.Calculate(A,[0.0]*N,N)==M.Calculate(A,[0.0]*N,N)\nStats=[F() for K,F in vars(M).items() if K.startswith("_Pyceler_Fast_") and K.endswith("Stats")]\nassert sum(S["Native_Elements"] for S in Stats)>0,Stats\nassert sum(S["Parallel_Elements"] for S in Stats)>0,Stats\n'
            Run = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(Source_File), str(Binary)], capture_output=True, text=True, timeout=90)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)

    def test_Composed_Numeric_Regions(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            File = Folder / 'Generalization_Loops.py'
            File.write_text(Source(), encoding='utf-8')
            Findings = Analyze(File, OpenMP=True)
            Changed = {Item.Function for Item in Findings if Item.Classification in ('Guarded_Numeric_Region', 'Guarded_Array_Region', 'Potential_Independent_Write')}
            self.assertTrue({'Nested', 'Nested_While', 'Repeated_Index', 'Shared_Inner', 'Integer_Absolute', 'Interleaved', 'Columns', 'Dependent', 'Many_Slots_List', 'Many_Slots_Array', 'Many_Buffers'} <= Changed, Changed)
            Generated = Convert(File, Folder / 'Cython', Select=False, OpenMP=True)
            self.assertIn('Prange(', Generated.read_text(encoding='utf-8'))
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Generalization_Probe.py'), str(File), str(Binary), str(Folder / 'Results.json')], capture_output=True, text=True, timeout=180)
            if Run.returncode:
                print(Run.stdout + Run.stderr, flush=True)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            Report = json.loads((Folder / 'Results.json').read_text())
            self.assertGreater(Report['Comparisons'], 80)
            self.assertGreater(Report['Parallel'], 0)
            print('Generalization: ' + Run.stdout, flush=True)
