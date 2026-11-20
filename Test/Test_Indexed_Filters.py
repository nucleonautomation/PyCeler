import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
import numpy as np
from PyCeler import Analyze, Compile
from Test.Workspace import Temporary_Directory

_Source = """def Nearby(Buckets, Samples, Pivot, Limit, Output):
    for Candidates in Buckets:
        for Index in Candidates:
            if Index == Pivot:
                continue
            Vertical = Samples[Pivot, 2] - Samples[Index, 2]
            Horizontal = Samples[Pivot, 0] - Samples[Index, 0]
            Distance = Horizontal * Horizontal + Vertical * Vertical
            if Distance <= Limit ** 2:
                Output.append(Index)
    return Output

def Screen(Rows, Readings, Base, Cutoff, Kept):
    for Row in Rows:
        Offset = Readings[Base, 1] - Readings[Row, 1]
        Score = Offset * Offset
        if Score < Cutoff:
            Kept.append(Row)
    return Kept
"""

# Compare the normal compiled entry point with Python for indexed gathers and guard failures.
class Indexed_Filters(unittest.TestCase):
    def test_Ordered_Filter_And_Fallback(self):
        with Temporary_Directory(dir=Path(__file__).resolve().parents[1] / 'Test_Run') as Folder:
            File = Path(Folder) / 'Renamed.py'
            File.write_text(_Source, encoding='utf-8')
            Binary = Compile(File, Path(Folder) / 'Native', OpenMP=False, Select=False)
            subprocess.run([sys.executable, '-B', '-m', 'Test.Test_Indexed_Filters', str(Binary)], cwd=Path(__file__).resolve().parents[1], check=True)
            File.write_text(_Source.replace('return Output', 'return Distance, Output'), encoding='utf-8')
            self.assertFalse(any(Item.Function == 'Nearby' and Item.Classification == 'Guarded_Indexed_Filter' for Item in Analyze(File)))

def _Probe(Binary):
    Reference = {}
    exec(_Source, Reference)
    Check = unittest.TestCase()
    Spec = importlib.util.spec_from_file_location('Renamed', Binary)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    Values = np.array([[3., 7., 0.], [0., 7., 4.], [0., 7., 0.]])
    Rows = [int('300'), int('300'), int('301')]
    Readings = np.zeros((302, 2))
    Readings[301, 1] = 2.
    Screened = Module.Screen(Rows, Readings, 0, 4., [])
    Check.assertEqual(Screened, Reference['Screen'](Rows, Readings, 0, 4., []))
    Check.assertTrue(all(Got is Want for Got, Want in zip(Screened, Rows)))
    for Table, Indices, Limit, Native in [(Values, [2, 1, 0, 1], 5., True), (Values[:, ::-1], [0, 1], 5., True), (Values.astype('f4'), [1], 2., False), (Values, [0, -1], 5., False), (Values, [0, 12], 5., False), (Values, [0, 1 << 80], 1., False), (Values * 1e-100, [1], 1., False), (Values, [1], np.float64(5), False)]:
        def Observe(Function):
            Output = [99]
            try:
                Result = Function([Indices], Table, 2, Limit, Output)
            except Exception as Error:
                return type(Error), Error.args, Output
            return Result is Output, Output
        Expected = Observe(Reference['Nearby'])
        Module._Pyceler_Dispatch_Stats(True, Reset=True)
        Check.assertEqual(Observe(Module.Nearby), Expected)
        Check.assertEqual(Module._Pyceler_Dispatch_Stats()['Execution']['Native_Entry'], Native)

if __name__ == "__main__":
    _Probe(Path(sys.argv[1]))
