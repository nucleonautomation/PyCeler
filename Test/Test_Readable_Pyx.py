import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Convert, Compile
from PyCeler.Direct_Bindings import _Direct_Builtin_Bindings
from Test.Workspace import Temporary_Directory
# Regression checks for editable single-file output without runtime source strings.
class Readable_Pyx(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Builtin_Shadow_Scopes(self):
        Cases = ["range = lambda Count: [Count + 1]\ndef Local(range):\n    return range(3)\nResult = ([range(Index) for Index in (1, 2)], Local(lambda Value: Value * 2))\n", "from math import sqrt as abs\ndef Read():\n    return abs(9)\nResult = Read()\n", "min = 7\ndef Change():\n    global min\n    min += 2\nChange()\nResult = min\n", "max = 0\nResult = (max := 9)\n"]
        Cases.extend(["range = lambda x: [x]\nResult = ([range for range in (1, 2)], range(3))", "range = lambda x: [x]\nResult = (list(range for range in (1, 2)), range(3))"])
        for Source in Cases:
            Expected, Actual = {}, {}
            Actual['_Pyceler_Direct_Globals'] = lambda: Actual
            Actual['_Pyceler_Direct_Value'] = lambda Namespace, Name: Namespace[Name] if Name in Namespace else Namespace['__builtins__'][Name]
            def Set(Name, Value):
                Actual[Name] = Value
                return Value
            Actual['_Pyceler_Direct_Set_Global'] = Set
            exec(Source, Expected)
            exec(_Direct_Builtin_Bindings(Source, '_Pyceler_'), Actual)
            self.assertEqual(Actual['Result'], Expected['Result'])

    def test_Single_Editable_Source_And_Native_Execution(self):
        Source = self._Root / 'Test/Readable_Pyx_Loops.py'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            Generated = Convert(Source, Folder / 'Cython', Select=False, OpenMP=True)
            Text = Generated.read_text(encoding='utf-8')
            self.assertIn('def Ordinary(Value):', Text)
            self.assertIn('def Process(Source, Output):', Text)
            self.assertIn('nogil', Text)
            self.assertNotIn('exec(', Text)
            self.assertNotIn('compile(', Text)
            self.assertEqual(list(Generated.parent.glob('*.py')), [])
            Generated.write_text(Text.replace("Message = 'editable source'", "Message = 'edited generated source'"), encoding='utf-8')
            Binary = Compile(Generated, Folder / 'Native', Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Readable_Pyx_Probe.py'), str(Source), str(Binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print('Readable single pyx: ' + Run.stdout.strip(), flush=True)
