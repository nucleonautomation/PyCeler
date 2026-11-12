import ast
import builtins
import copy
import re
import unittest
from pathlib import Path

class Scalar_Bypass(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Source = """def Mixed(Begin, End, Stride, Initial, Events, Callback):
    Events.append(('prelude',))
    Total = Initial
    Index = -23
    for Index in range(Begin, End, Stride):
        Total += (Index * Index + Index * Stride) % 999983
        if Index % 6 == 0:
            Events.append((Index, Total, Stride))
            Total, Stride = Callback(Index, Total, Stride)
    else:
        Events.append(('else', Total, Index, Stride))
    Events.append(('done', Total, Index, Stride))
    return Total, Index, Stride
"""

    @classmethod
    def setUpClass(cls):
        Source = (cls._Root / 'PyCeler/Scalar_Region_Generator.pxi').read_text(encoding='utf-8')
        Source = re.sub(r'(?m)^cdef (?:str|object) (\w+)\((.*)\):$', lambda Match: 'def ' + Match[1] + '(' + re.sub(r'\b(?:dict|object|int|str) (?=\w)', '', Match[2]) + '):', Source)
        cls._Generator = dict(ast=ast, copy=copy)
        exec(compile(Source, 'Scalar_Region_Generator', 'exec'), cls._Generator)
        Runtime = (cls._Root / 'PyCeler/Scalar_Region_Runtime.pxi.in').read_text(encoding='utf-8')
        Runtime = Runtime[Runtime.index('def _Pyceler_Region_Divisor('):].replace('object ', '')
        cls._Runtime = {}
        exec(compile(Runtime, 'Scalar_Region_Runtime', 'exec'), cls._Runtime)

    def _Generate(self, Table, Source=None, Prefix='_Pyceler_'):
        Tree = ast.parse(self._Source if Source is None else Source)
        Function = Tree.body[0]
        Loop = next(Node for Node in Function.body if isinstance(Node, ast.For))
        Statements = Loop.body[:-1]
        Reporting = Loop.body[-1]
        Inputs = ('Total', 'Stride', 'Missing') if Source is not None and 'Missing' in Source else ('Total', 'Stride')
        Plan = dict(Inputs=Inputs, Outputs=('Total', 'Index'), Index='Index', Step=None, Period=6,
                    Statements=Statements, Reporting=Reporting)
        Generated = self._Generator['_Scalar_Region_Source'](Plan, Loop, 7, Prefix, Table)
        Location = Function.body.index(Loop)
        Function.body[Location:Location + 1] = ast.parse(Generated).body
        Tree = ast.fix_missing_locations(Tree)
        return Tree, Generated, Plan

    def _Call(self, Size, Step, Table, Generated, Begin=0, Failure=None, Header=False, Shadow=False, Prefix='_Pyceler_'):
        Events, Statistics = [], dict(Spans=0, Native=0, Declined=0, Choices=0, Counts=0)
        Namespace = dict(__builtins__=builtins.__dict__)
        def Binding():
            return Namespace.get('range', builtins.range)
        def Count(Values):
            Statistics['Counts'] += 1
            self.assertIs(type(Values), range)
            return self._Runtime['_Pyceler_Region_Count'](Values)
        def Spans(Values, Period):
            Statistics['Spans'] += 1
            yield from self._Runtime['_Pyceler_Region_Spans'](Values, Period)
        def Choose(Values, Scalar, Policy):
            Statistics['Choices'] += 1
            return next((Mode for Bound, Mode in Policy.get('int', ()) if Values[0] >= Bound), 0)
        def Candidate(End, Start, Total, Stride, Captured_Step):
            Statistics['Native'] += 1
            for Index in builtins.range(Start, End, Captured_Step):
                Total += (Index * Index + Index * Stride) % 999983
            return Total, Index
        def Declined():
            Statistics['Declined'] += 1
        def Callback(Index, Total, Stride):
            Events.append(('callback', Index, Total, Stride))
            Namespace['range'] = lambda *Arguments: (_ for _ in ()).throw(AssertionError('range was evaluated again'))
            if Failure == 'raise':
                raise RuntimeError('controlled callback failure')
            if Failure == 'unpack':
                return (Total,)
            if Failure in ('break', 'continue', 'return'):
                return {'break': -777, 'continue': -888, 'return': -999}[Failure], -Stride
            return Total + 1, 'bad' if Failure == 'stride' else -Stride
        class Header_Value:
            def __init__(self, Value, Name):
                self.Value, self.Name = Value, Name
            def __index__(self):
                Events.append(('index', self.Name, self.Value))
                return self.Value
        def Stable(Value):
            if isinstance(Value, Header_Value):
                return ('header value', Value.Name, Value.Value)
            if type(Value) is tuple:
                return tuple(Stable(Item) for Item in Value)
            if type(Value) is list:
                return [Stable(Item) for Item in Value]
            return Value
        if Shadow:
            def Custom_Range(*Arguments):
                Events.append(('custom range', Arguments))
                return [0, 3, 6]
            Namespace['range'] = Custom_Range
        if Generated:
            Tree, Text, Plan = self._Generate(Table, Prefix=Prefix)
            Namespace.update({Prefix + Name: Value for Name, Value in dict(Region_Binding=Binding, Region_Range=lambda Value, Expected: type(Value) is range,
                                                                         Region_Count=Count, Region_Spans=Spans, Region_Declined=Declined, Choose=Choose,
                                                                         Scalar_Region_7=Candidate, Table_7=Table).items()})
            exec(compile(Tree, 'Generated_Bypass', 'exec'), Namespace)
        else:
            exec(compile(self._Source, 'Original_Bypass', 'exec'), Namespace)
        Arguments = [Begin, Begin + Size * Step, Step]
        if Header:
            Arguments = [Header_Value(Value, Name) for Value, Name in zip(Arguments, ('begin', 'end', 'step'))]
        try:
            Result = ('return', Namespace['Mixed'](*Arguments, 17, Events, Callback))
        except Exception as Error:
            Result = ('raise', type(Error), Error.args)
        return Stable(Result), Stable(Events), Statistics

    def test_Minimum_Only_Uses_Validated_Serial_Bands(self):
        Minimum = self._Generator['_Scalar_Region_Minimum']
        for Table in (None, {}, {'int': []}, {'int': [(4, 0)]}, {'int': [(0, 1)]}, {'int': [(4, 2)]}, {'int': [(4, 101)]},
                      {'int': [(True, 1)]}, {'int': [(4, True)]}, {'int': [(-1, 1)]}, {'int': [(2.0, 1)]}):
            self.assertIsNone(Minimum(Table), Table)
        self.assertEqual(Minimum({'int': [(4096, 1), (256, 1), (4, 0)]}), 256)
        self.assertEqual(Minimum({'int': [(256, 1)], 'float': [(128, 1)]}), 128)

    def test_Exact_Count_Matches_Independent_Iteration_And_Huge_Ranges(self):
        Count = self._Runtime['_Pyceler_Region_Count']
        for Begin in range(-19, 20, 3):
            for End in range(-19, 20, 3):
                for Step in (-7, -3, -1, 1, 2, 7):
                    self.assertEqual(Count(range(Begin, End, Step)), sum(1 for Ignored in range(Begin, End, Step)))
        for Step in (-3, 2):
            for Begin in (-(2**100), 2**100):
                for Size in (0, 1, 64, 2**80):
                    self.assertEqual(Count(range(Begin, Begin + Size * Step, Step)), Size)

    def test_Generated_Bypass_Preserves_Values_Events_Headers_And_Callback_Rebinding(self):
        Table = {'int': [(4096, 1), (256, 1), (4, 0)]}
        for Step in (1, -1, 2, -3):
            for Size in (0, 1, 7, 63, 255, 256, 257):
                for Begin in (0, 2**100):
                    for Header in (False, True):
                        Reference = self._Call(Size, Step, Table, False, Begin=Begin, Header=Header)
                        Actual = self._Call(Size, Step, Table, True, Begin=Begin, Header=Header)
                        self.assertEqual(Actual[:2], Reference[:2], (Size, Step, Begin, Header))
                        if Header:
                            self.assertEqual(sum(Event[0] == 'index' for Event in Actual[1]), 3)
                        self.assertEqual(Actual[2]['Counts'], 1)
                        if Size < 256:
                            self.assertEqual(Actual[2], dict(Spans=0, Native=0, Declined=0, Choices=0, Counts=1))
                        else:
                            self.assertEqual(Actual[2]['Spans'], 1)

    def test_Callback_Exceptions_And_Custom_Range_Retain_Original_Order(self):
        Table = {'int': [(256, 1), (4, 0)]}
        for Failure in ('raise', 'unpack', 'stride'):
            Reference = self._Call(64, -3, Table, False, Failure=Failure)
            Actual = self._Call(64, -3, Table, True, Failure=Failure)
            self.assertEqual(Actual[:2], Reference[:2], Failure)
            self.assertEqual(Actual[2], dict(Spans=0, Native=0, Declined=0, Choices=0, Counts=1))
        Reference = self._Call(64, 1, Table, False, Shadow=True)
        Actual = self._Call(64, 1, Table, True, Shadow=True)
        self.assertEqual(Actual[:2], Reference[:2])
        self.assertEqual(Actual[2], dict(Spans=0, Native=0, Declined=1, Choices=0, Counts=0))

    def test_All_Python_And_Unmeasured_Sources_Preserve_Their_Existing_Paths(self):
        for Table in ({}, {'int': []}, {'int': [(256, 0), (4, 0)]}):
            Tree, Generated, Plan = self._Generate(Table)
            self.assertNotIn('Region_Count', Generated)
            self.assertNotIn('Region_Spans', Generated)
            Actual = self._Call(64, 1, Table, True)
            Reference = self._Call(64, 1, Table, False)
            self.assertEqual(Actual[:2], Reference[:2])
            self.assertEqual(Actual[2], dict(Spans=0, Native=0, Declined=0, Choices=0, Counts=0))
        Tree, Generated, Plan = self._Generate(None)
        self.assertNotIn('Region_Count', Generated)
        self.assertIn('Region_Spans', Generated)

    def test_Reporting_Break_Continue_Return_And_Index_Mutation(self):
        Original = self._Source
        self._Source = Original.replace("    else:\n        Events.append(('else', Total, Index, Stride))\n", '')
        self._Source = self._Source.replace('            Total, Stride = Callback(Index, Total, Stride)',
                                           '            Total, Stride = Callback(Index, Total, Stride)\n            if Total == -777:\n                break\n            if Total == -888:\n                continue\n            if Total == -999:\n                return Total, Index, Stride\n            Index = -99')
        try:
            for Failure in (None, 'break', 'continue', 'return'):
                Table = {'int': [(256, 1), (4, 0)]}
                Reference = self._Call(64, -3, Table, False, Failure=Failure)
                Actual = self._Call(64, -3, Table, True, Failure=Failure)
                self.assertEqual(Actual[:2], Reference[:2], Failure)
                self.assertEqual(Actual[2], dict(Spans=0, Native=0, Declined=0, Choices=0, Counts=1))
        finally:
            self._Source = Original

    def test_Private_Prefix_And_Empty_Unbound_Inputs(self):
        Table = {'int': [(256, 1), (4, 0)]}
        self.assertEqual(self._Call(63, -3, Table, True, Prefix='_Pyceler_XX')[:2], self._Call(63, -3, Table, False)[:2])
        Tree, Generated, Plan = self._Generate(Table)
        self.assertEqual(sum(isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id == '_Pyceler_Region_Binding' for Node in ast.walk(Tree)), 1)
        Source = self._Source.replace('Index * Index + Index * Stride', 'Missing')
        Tree, Generated, Plan = self._Generate(Table, Source=Source)
        Namespace = dict(_Pyceler_Region_Binding=lambda: range, _Pyceler_Region_Range=lambda Value, Step: type(Value) is range,
                         _Pyceler_Region_Count=self._Runtime['_Pyceler_Region_Count'])
        exec(compile(Tree, 'Empty_Unbound_Bypass', 'exec'), Namespace)
        Events = []
        self.assertEqual(Namespace['Mixed'](0, 0, 1, 17, Events, None), (17, -23, 1))
        self.assertEqual(Events, [('prelude',), ('else', 17, -23, 1), ('done', 17, -23, 1)])

if __name__ == '__main__':
    unittest.main()
