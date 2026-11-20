import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from PyCeler import Analyze, Compile, Convert
from PyCeler.Common_Calls import _Call_Arguments, _Helper_Summaries
from PyCeler.Fast_Math import _Fast_Expression, _Fast_Emit, _Fast_Unsupported
from Test.Workspace import Temporary_Directory
# Regression checks for helper argument order, identity and guarded inlining.
def Plan(Source, Call, Types):
    Context = dict(Helpers=_Helper_Summaries(ast.parse(Source)), Helper_Counter=[0], Helper_Roots={}, Helper_Globals={}, Helper_Used=set(), Helper_Operations=set(), Numeric_Region=True, Builtins=(), Buffers={}, Local_Slots=list(Types), Local_Types=Types)
    return _Fast_Expression(ast.parse(Call, mode='eval').body, Context, {}, [], set())

class Helper_Calls(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Binding_Preserves_Keyword_Evaluation_Order(self):
        Call = ast.parse('Blend(First(), Third=Second(), Second=Third())', mode='eval').body
        Values, Slots = _Call_Arguments(Call, ('First', 'Second', 'Third'), 1)
        self.assertEqual(tuple(ast.unparse(Value) for Value in Values), ('First()', 'Second()', 'Third()'))
        self.assertEqual(Slots, (0, 2, 1))
        for Source in ('Scale(*Args)', 'Scale(**Args)', 'Scale(1)', 'Scale(1, 2, 3)', 'Scale(1, First=2)', 'Scale(First=1, Second=2)'):
            self.assertIsNone(_Call_Arguments(ast.parse(Source, mode='eval').body, ('First', 'Second'), 1), Source)

    def test_Argument_Is_Evaluated_Once_Even_When_Unused(self):
        Node, Kind = Plan('def Scale(Used, Unused):\n    return Used * Used\n', 'Scale(Left + Right, 1.0 / Other)', dict(Left='float', Right='float', Other='float'))
        Lines, Variables = [], []
        _Fast_Emit(Node, Lines, Variables, (), '_Test_')
        Text = '\n'.join(Lines)
        self.assertEqual(Kind, 'float')
        self.assertEqual(Text.count(' + '), 1)
        self.assertEqual(Text.count(' / '), 1)
        self.assertLess(Text.index(' / '), Text.index(' * '))

    def test_Nested_Arguments_And_Integer_Intermediates(self):
        Source = 'def Square(Value):\n    return Value * Value\ndef Scale(Value):\n    return Square(Value) * 0.5 + Value\n'
        Node, Kind = Plan(Source, 'Scale(Input)', dict(Input='integer'))
        self.assertEqual(Kind, 'float')
        Lines, Variables = [], []
        _Fast_Emit(Node, Lines, Variables, (), '_Test_')
        Text = '\n'.join(Lines)
        self.assertNotIn('helper_parameter', Text)
        self.assertLess(Text.index('1125899906842624'), Text.rindex(' * '))

    def test_Unsupported_Summaries_Do_Not_Execute_Source(self):
        Tree = ast.parse("raise RuntimeError('must never execute')\ndef Scale(Value):\n    return Value * 0.5\ndef Stateful(Value):\n    print(Value)\n    return Value\ndef Defaults(Value=1):\n    return Value * 0.5\n")
        self.assertEqual(set(_Helper_Summaries(Tree)), {'Scale'})
        for Source in ('def Recur(Value):\n    return Recur(Value)\n', 'def Recur(Value):\n    return Value\n', 'def Recur(Value):\n    return 3.5\n'):
            with self.assertRaises(_Fast_Unsupported):
                Plan(Source, 'Recur(Input)', dict(Input='float'))

    def test_Compiled_Helper_Boundaries_And_Precision(self):
        Source = self._Root / 'Test/Helper_Call_Cases.py'
        Findings = Analyze(Source, OpenMP=True)
        Changed = {Item.Function for Item in Findings if Item.Change != 'Keep original loop'}
        self.assertTrue({'Apply', 'Heavy', 'Array_Apply', 'Shadowed_Math', 'Captured_Callable.Apply_Captured'} <= Changed, Changed)
        Item = next(Item for Item in Findings if Item.Function == 'Apply')
        Call = next(Call for Call in Item.Plan.Calls if Call.Name == 'Nested')
        self.assertEqual(Call.Status, 'guarded_helper')
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Folder = Path(Directory)
            for Parallel in (False, True):
                Binary = Compile(Source, Folder / ('Parallel' if Parallel else 'Serial'), Select=False, OpenMP=Parallel)  # Build a real extension; a static finding alone does not prove native execution.
                Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Helper_Call_Probe.py'), str(Source), str(Binary), 'parallel' if Parallel else 'serial'], capture_output=True, text=True, timeout=120)
                self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
                Report = json.loads(Run.stdout)
                self.assertGreater(Report['Comparisons'], 90)
                self.assertGreater(Report['Native'], 40)
                self.assertEqual(Report['Parallel'] > 0, Parallel)
                print('Helper calls:', Run.stdout, flush=True)

    def test_Default_Selection_Retains_Helper_Definitions(self):
        Text = (self._Root / 'Test/Helper_Call_Cases.py').read_text()
        Names = {'Trig', 'Heavy'}
        Definitions = [ast.get_source_segment(Text, Node) for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef) and Node.name in Names]
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Folder = Path(Directory)
            Source = Folder / 'Helper_Selection.py'
            Source.write_text('import math\nfrom math import cos as Cosine\n' + '\n'.join(Definitions) + '\n')
            Generated = Convert(Source, Folder / 'Converted', OpenMP=True)
            Report = json.loads(Generated.with_suffix('.selection.json').read_text())
            self.assertEqual(Report['Items'][0]['Status'], 'native_selected')
            Selected = next((Mode for Size, Mode in Report['Items'][0]['Dispatch']['int'] if 4096 >= Size), 0)
            self.assertIn(Selected, (1, 2), Report)
            Binary = Compile(Generated, Folder / 'Native', OpenMP=True, Convert=False)
            Program = "import importlib.util,sys\ndef Load(File, Name):\n    Spec=importlib.util.spec_from_file_location(Name,File)\n    M=importlib.util.module_from_spec(Spec)\n    Spec.loader.exec_module(M)\n    return M\nR=Load(sys.argv[1],'Reference')\nM=Load(sys.argv[2],'Helper_Selection')\nA=[0.25]*4096\nassert M.Heavy(A,[0.0]*4096,4096)==R.Heavy(A,[0.0]*4096,4096)\nS=[F() for K,F in vars(M).items() if K.startswith('_Pyceler_Fast_') and K.endswith('Stats')]\nassert sum(V['Native_Elements'] for V in S)>0,S\nassert (sum(V['Parallel_Elements'] for V in S)>0)==(sys.argv[3]=='2'),S\nassert sys.argv[3]!='2' or max(V['Team'] for V in S)>1,S\n"
            Run = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(Source), str(Binary), str(Selected)], capture_output=True, text=True, timeout=60)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr + json.dumps(Report))

    def test_Monitoring_Preserves_Helper_And_Caller_Events(self):
        Source = self._Root / 'Test/Monitoring_Cases.py'
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Directory:
            Binary = Compile(Source, Path(Directory) / 'Native', Select=False, OpenMP=True)
            Run = subprocess.run([sys.executable, '-I', '-B', str(self._Root / 'Test/Monitoring_Probe.py'), str(Source), str(Binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(Run.returncode, 0, Run.stdout + Run.stderr)
            print('Monitoring:', Run.stdout, flush=True)
