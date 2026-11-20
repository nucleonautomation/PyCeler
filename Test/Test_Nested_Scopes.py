import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Compile, Convert
from PyCeler.Common_Scopes import _Function_Scopes
from Test.Workspace import Temporary_Directory
# Regression checks for closures, class-private names and lexical scope.
class Nested_Scopes(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Qualified_Scopes_Keep_Lexical_Bindings_Separate(self):
        Tree = ast.parse('def Factory(abs):\n    Value=1\n    class Box:\n        Field=2\n        def Kernel(self):\n            return abs(Value)\n    def Global():\n        global Value\n        def Kernel():\n            return Value\n        return Kernel\n    return Box\n')
        Scopes = {Scope: Captures for Function, Scope, Captures, Locals, Globals in _Function_Scopes(Tree)}
        self.assertIn('abs', Scopes['Factory.Box.Kernel'])
        self.assertIn('Value', Scopes['Factory.Box.Kernel'])
        self.assertNotIn('Field', Scopes['Factory.Box.Kernel'])
        self.assertNotIn('Value', Scopes['Factory.Global.Kernel'])
        Tree = ast.parse('def Outer(Value):\n    def Kernel():\n        Result=Value\n        Value=2\n        return Result\n    return Kernel\n')
        Scopes = {Scope: Captures for Function, Scope, Captures, Locals, Globals in _Function_Scopes(Tree)}
        self.assertNotIn('Value', Scopes['Outer.Kernel'])
        Tree = ast.parse('def Factory():\n    Make = lambda Value=(sin := None): Value\n    def Kernel(X):\n        return sin(X)\n    return Kernel\n')
        Scopes = {Scope: Captures for Function, Scope, Captures, Locals, Globals in _Function_Scopes(Tree)}
        self.assertIn('sin', Scopes['Factory.Kernel'])
        Tree = ast.parse('class Box:\n    def Kernel(self, Source):\n        return __math.sin(Source)\n')
        Item = _Function_Scopes(Tree)[0]
        self.assertEqual(Item[4]['__math'], '_Box__math')

    def test_Nested_And_Captured_Loops_Enter_Native_Regions(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            File = self._Root / 'Test/Nested_Scope_Cases.py'
            Binary = Compile(File, Path(Directory) / 'Native', Select=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Nested_Scope_Probe.py'), str(File), str(Binary)], capture_output=True, text=True, timeout=120)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout, flush=True)

    def test_Default_Selection_Reports_Qualified_Regions(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            File = self._Root / 'Test/Nested_Scope_Cases.py'
            Generated = Convert(File, Path(Directory) / 'Cython', OpenMP=True)
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            Names = {Item['Function'] for Item in Report['Items']}
            self.assertTrue({'List_Factory.Kernel', 'Array_Factory.Kernel', 'Captured_List.Kernel', 'Captured_Array.Kernel'} <= Names)
            Item = next(Item for Item in Report['Items'] if Item['Function'] == 'List_Factory.Kernel')
            self.assertIn('list_float', Item['Probe_Dispatch_Keys'])
            for Name in ('List_Factory.Kernel', 'Array_Factory.Kernel'):
                Item = next(Item for Item in Report['Items'] if Item['Function'] == Name)
                self.assertTrue(any(Observation.get('Native_Entry') for Case in Item['Cases'] for Observation in Case.get('Observations', {}).values()), Name)
            Binary = Compile(Generated, Path(Directory) / 'Native', Convert=False, OpenMP=True)
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Nested_Scope_Probe.py'), str(File), str(Binary), str(Generated.with_suffix('.selection.json'))], capture_output=True, text=True, timeout=120)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print(Run.stdout, flush=True)
