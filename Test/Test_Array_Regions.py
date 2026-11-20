import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Compile, Convert
from Test.Workspace import Temporary_Directory
from Test.Random_Boundary_Cases import Sources
# Regression checks for ndarray ranks, scalar promotion and ordered region execution.
class Array_Regions(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Random_Bounds_Keep_Original_Order_And_Native_Inner_Work(self):
        Source = self._Root / 'Test/Random_Bound_Loops.py'
        Findings = Analyze(Source, OpenMP=True)
        self.assertEqual({Item.Function for Item in Findings if Item.Classification == 'Guarded_Array_Region'}, {'Pure_Body', 'Random_Body', 'Heavy', 'Ordered_Math'})
        self.assertTrue(any(Item.Function == 'List_Math' and Item.Classification == 'Guarded_Numeric_Region' for Item in Findings))
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            for Parallel in (False, True):
                Mode = 'parallel' if Parallel else 'serial'
                Binary = Compile(Source, Folder / Mode, Select=False, OpenMP=Parallel)  # Build a real extension; a static finding alone does not prove native execution.
                Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Random_Bound_Probe.py'), str(Source), str(Binary), Mode], capture_output=True, text=True, timeout=120)
                self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
                print('Random bounds: ' + Run.stdout.strip(), flush=True)

    def test_Random_Bound_Selection_Preserves_State_And_Native_Work(self):
        Source = self._Root / 'Test/Random_Bound_Loops.py'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            Workloads = {'Heavy': dict(File=self._Root / 'Test/Random_Bound_Cases.py', Factory='Cases')}
            Generated = Convert(Source, Folder / 'Cython', OpenMP=True, Workloads=Workloads)
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            Item = next(Item for Item in Report['Items'] if Item['Function'] == 'Heavy')
            self.assertEqual(Item['Status'], 'native_selected', Item)
            self.assertTrue(any(Case.get('Holdout') for Case in Item['Cases']), Item)
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Random_Bound_Probe.py'), str(Source), str(Binary), 'selected'], capture_output=True, text=True, timeout=120)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print('Selected random bounds: ' + Run.stdout.strip(), flush=True)

    def test_Random_Range_Errors_And_Lazy_Branches(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            for Parallel in (False, True):
                for Name, Text in Sources().items():
                    Source = Folder / (Name + '.py')
                    Source.write_text(Text)
                    Binary = Compile(Source, Folder / str(Parallel), Select=False, OpenMP=Parallel)
                    Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Random_Boundary_Probe.py'), str(Source), str(Binary), Name], capture_output=True, text=True, timeout=120)
                    self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
                    print('Random range boundaries: ' + Run.stdout.strip(), flush=True)

    def test_Selection_Retains_Inferred_Array_Inputs(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            Source = Folder / 'Inferred_Array.py'
            Source.write_text('import math\nimport numpy as np\nValues = np.linspace(0.01, 0.6, 2048)\nTotal = 0.0\nfor Index in range(len(Values)):\n    Value = Values[Index]\n    if Value < 0.07:\n        Total += Value * 1.5\n    else:\n        Total += math.sqrt(Value)\n')
            Generated = Convert(Source, Folder / 'Converted', OpenMP=True)
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            Item = Report['Items'][0]
            self.assertEqual(Item['Kind'], 'array_region')
            self.assertEqual(Item['Status'], 'native_selected')
            self.assertTrue(any(Case['Observations'].get('Serial', {}).get('Native_Entry') for Case in Item['Cases']))

    def test_Typed_Ranks_Strides_Reductions_And_Parallel_Writes(self):
        Source = self._Root / 'Test/Array_Region_Loops.py'
        Findings = Analyze(Source, OpenMP=True)
        self.assertEqual({Item.Function for Item in Findings if Item.Change != 'Keep original loop'}, {'Stencil', 'Volume_Four', 'Volume_Six', 'Row_Sum', 'Strided', 'Neighbor_Recurrence', 'Cast_Outputs', 'Piecewise_Sum'})
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            Binary = Compile(Source, Folder / 'Native', Select=False, OpenMP=True)
            Result = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Array_Region_Probe.py'), str(Source), str(Binary), str(Folder / 'Result.json')], capture_output=True, text=True, timeout=180)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
            Report = json.loads((Folder / 'Result.json').read_text())
            self.assertGreater(Report['Counters']['Parallel_Elements'], 0)
            print('Array regions: ' + json.dumps(Report), flush=True)

    def test_Ordered_Random_State_And_Transactional_Errors(self):
        Source = self._Root / 'Test/Array_Random_Loops.py'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            for Parallel in (False, True):
                Mode = 'parallel' if Parallel else 'serial'
                Binary = Compile(Source, Folder / Mode, Select=False, OpenMP=Parallel)
                Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Array_Random_Probe.py'), str(Source), str(Binary), str(Folder / 'Result.json'), Mode], capture_output=True, text=True, timeout=180)
                self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
                Report = json.loads((Folder / 'Result.json').read_text())
                self.assertEqual(Report['Counters']['Parallel_Elements'] > 0, Parallel)
                print('Array random regions: ' + json.dumps(Report), flush=True)
