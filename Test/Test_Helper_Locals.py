import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile
from PyCeler.Fast_Math import _Fast_Emit, _Fast_Unsupported
from Test.Test_Helper_Calls import Plan
from Test.Workspace import Temporary_Directory
# Regression checks for pure-helper local computations and unused arguments.
class Helper_Locals(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Assignments_Evaluate_Once_In_Order(self):
        Source = 'def Helper(Value, Divisor):\n    First = Value * 0.75\n    Ignored = Value / Divisor\n    Result = First * First\n    Result += First\n    return Result\n'
        Node, Kind = Plan(Source, 'Helper(Input, Other)', dict(Input='float', Other='float'))
        Lines, Variables = [], []
        _Fast_Emit(Node, Lines, Variables, (), '_Test_')
        Text = '\n'.join(Lines)
        self.assertEqual(Kind, 'float')
        self.assertEqual(Text.count(' * '), 2)
        self.assertEqual(Text.count(' / '), 1)
        self.assertLess(Text.index(' / '), Text.rindex(' * '))
        self.assertNotIn('helper_parameter', Text)

    def test_Borrowed_Constant_And_Unbound_Locals_Stay_Unsupported(self):
        Bodies = ('Result = 1.0 + 2.0\nreturn Result', 'Result = Value\nreturn Result', 'First = Result + Value\nResult = Value * 0.5\nreturn First')
        for Body in Bodies:
            Source = 'def Helper(Value):\n' + '\n'.join('    ' + Line for Line in Body.splitlines())
            with self.assertRaises(_Fast_Unsupported):
                Plan(Source, 'Helper(Input)', dict(Input='float'))

    def test_Native_Local_Helper_Composition(self):
        Source = self._Root / 'Test/Helper_Local_Loops.py'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Binary = Compile(Source, Path(Directory) / 'Native', Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Helper_Local_Probe.py'), str(Source), str(Binary)], capture_output=True, text=True, timeout=90)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print('Helper locals: ' + Run.stdout.strip(), flush=True)
