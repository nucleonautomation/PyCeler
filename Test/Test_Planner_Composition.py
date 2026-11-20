import ast
import unittest
from PyCeler.Array_Regions import _Array_Region_Plans, _Compatible_Ordered_Map
from PyCeler.Math_Maps import _Math_Map_Plans
from PyCeler.Numeric_Regions import _Numeric_Region_Plans
# Regression checks for planner composition.
class Planner_Composition(unittest.TestCase):
    def test_Math_Maps_Have_Compatible_Storage_Alternatives(self):
        for Imports, Call, Supported in (('import math as M', 'M.sin(Source[Index])', True), ('from math import sin as Wave', 'Wave(Source[Index])', True), ('import numpy as N', 'N.sin(Source[Index])', False)):
            Text = Imports + '\ndef Calculate(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = ' + Call + '\n    return Output\n'
            Tree = ast.parse(Text)
            Edits = _Math_Map_Plans(Tree, Text)
            self.assertEqual(len(Edits), 1)
            self.assertEqual(_Array_Region_Plans(Tree, Edits), {})
            self.assertEqual(_Numeric_Region_Plans(Tree, Edits), {})
            Plan = next(iter(Edits.values()))[3]
            self.assertEqual('List_Alternative' in Plan, Supported)
            self.assertEqual('Array_Alternative' in Plan, Supported)
            if Supported:
                self.assertTrue(Plan['Array_Alternative']['Single_Only'])

    def test_Complete_Typed_Regions_Replace_Contained_Scalar_Regions(self):
        for Array in (False, True):
            Annotation = ': "numpy.ndarray"' if Array else ''
            Text = 'import math\ndef Calculate(Output' + Annotation + '):\n    for Index in range(len(Output)):\n        Value = Index * 0.01\n        for Repeat in range(24):\n            Value = math.sin(Value + 0.1)\n        Output[Index] = Value\n    return Output\n'
            for Supported in (False, True):
                Tree = ast.parse(Text if Supported else Text.replace('Output[Index] = Value', 'Output[Index] = str(Value)'))
                Function = Tree.body[1]
                Outer = Function.body[0]
                Inner = Outer.body[1]
                Edits = {Inner.lineno: ((), Inner, Function, dict(Kind='scalar_region'))}
                Plans = (_Array_Region_Plans if Array else _Numeric_Region_Plans)(Tree, Edits)
                self.assertEqual(Outer.lineno in Plans, Supported, (Array, Supported))
                self.assertEqual(Inner.lineno in Edits, not Supported, (Array, Supported))

    def test_Existing_Numpy_Math_Kernels_Keep_Their_Library_Contracts(self):
        for Imports, Call in (('import numpy as N', 'N.fabs(Source[Index])'), ('from numpy import fabs', 'fabs(Source[Index])'), ('import numpy as N\nimport math as M', 'N.fabs(Source[Index]) + M.fabs(Source[Index])')):
            with self.subTest(Imports=Imports):
                Text = Imports + '\ndef Calculate(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = ' + Call + '\n    return Output\n'
                Tree = ast.parse(Text)
                Edits = _Math_Map_Plans(Tree, Text)
                self.assertEqual(len(Edits), 1)
                self.assertEqual(_Array_Region_Plans(Tree, Edits), {})

    def test_Replacement_Matches_Each_Root_And_Imported_Symbol(self):
        Node = ast.parse('for Index in range(10):\n    Output[Index] = Index\n').body[0]
        Previous = ((), Node, None, dict(Math_Imports=('import math as M', 'from math import sqrt as Root', 'import numpy as N')))
        for Bindings, Expected in (((('M', 'sqrt', True),), True), ((('Root', 'sqrt', False),), True), ((('Root', 'fabs', False),), False), ((('N', 'sqrt', True),), False), ((('M', 'sqrt', True), ('N', 'sqrt', True)), False)):
            Plan = dict(Math=dict(Bindings=Bindings))
            self.assertEqual(_Compatible_Ordered_Map(Plan, Node, Previous), Expected, Bindings)

    def test_Inner_Replacement_Does_Not_Overlap_A_Preserved_Outer_Map(self):
        Outer = ast.parse('for Row in range(3):\n    for Column in range(4):\n        Output[Row][Column] = Source[Row][Column]\n').body[0]
        Previous = ((), Outer, None, dict(Math_Imports=()))
        self.assertFalse(_Compatible_Ordered_Map(dict(Math=dict(Bindings=())), Outer.body[0], Previous))

if __name__ == '__main__':
    unittest.main()
