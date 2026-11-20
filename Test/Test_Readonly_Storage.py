import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile
from PyCeler.Fast_Math import _Fast_Expression, _Fast_Emit
from Test.Workspace import Temporary_Directory
# Regression checks for shared read-only storage and selection holdouts.
class Readonly_Storage(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Length_Coordinates_Check_Each_Axis_In_Order(self):
        Plan = dict(Numeric_Region=True, Buffers={'Source': (0, 3, 'float')}, Local_Types={'Row': 'integer', 'Column': 'integer'}, Local_Slots=['Row', 'Column'])
        Node, Kind = _Fast_Expression(ast.parse('len(Source[Row][Column + 1])', mode='eval').body, Plan, {}, [], set())
        Lines = []
        _Fast_Emit(Node, Lines, [], (), '_Test_')
        Text = '\n'.join(Lines)
        self.assertEqual(Kind, 'integer')
        self.assertLess(Text.index('>= Shapes[0][0]'), Text.index(' + 1.0'))
        self.assertLess(Text.index('>= Shapes[0][1]'), Text.index('= Shapes[0][2]'))

    def test_Aliases_Dynamic_Lengths_And_Competing_Backends(self):
        Source = self._Root / 'Test/Readonly_Storage_Loops.py'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            for Mode in ('serial', 'parallel'):
                Binary = Compile(Source, Path(Directory) / Mode, Select=False, OpenMP=Mode == 'parallel')  # Build a real extension; a static finding alone does not prove native execution.
                Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Readonly_Storage_Probe.py'), str(Source), str(Binary), Mode], capture_output=True, text=True, timeout=120)
                self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
                Report = json.loads(Run.stdout)
                self.assertGreater(Report['Comparisons'], 100)
                self.assertGreater(Report['Native'], 35)
                self.assertGreater(Report['Guarded'], 5)
                if Mode == 'parallel':
                    self.assertGreater(Report['Parallel'], 10)
                print('Readonly storage ' + Mode + ': ' + Run.stdout.strip(), flush=True)
