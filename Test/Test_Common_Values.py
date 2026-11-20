import ast
import unittest
from PyCeler.Common_Analysis import _Affine_Outer
from PyCeler.Common_Values import _Stable_Values, _Real_Inputs, _Live_Region_Outputs
from PyCeler.Affine_Parameters import _Shifted_Forms
# Regression checks for live outputs and cross-region scalar state.
class Common_Values(unittest.TestCase):
    def test_Region_Outputs_Include_External_Uses_And_Module_Bindings(self):
        Tree = ast.parse('def Run(Source):\n    Total = 0.0\n    for Left in range(len(Source)):\n        for Right in range(Left + 1, len(Source)):\n            Value = Source[Right]\n            Total += Value\n    return Total\n')
        Function = Tree.body[0]
        Outer = Function.body[1]
        Written = ('Left', 'Right', 'Value', 'Total')
        self.assertEqual(_Live_Region_Outputs(Function, Outer, Written, False), ('Total',))
        self.assertEqual(_Live_Region_Outputs(Function, Outer, Written, True), Written)
        Function.body.append(ast.parse('dir()').body[0])
        self.assertEqual(_Live_Region_Outputs(Function, Outer, Written, False), Written)
        Function.body.pop()
        Function.body.append(ast.parse('Value += 1').body[0])
        self.assertEqual(_Live_Region_Outputs(Function, Outer, Written, False), ('Value', 'Total'))
        Tree = ast.parse('def Run(Source):\n    Value = 0.0\n    for Round in range(2):\n        print(Value)\n        for Index in range(len(Source)):\n            Value = Source[Index]\n    return Source\n')
        Function = Tree.body[0]
        self.assertEqual(_Live_Region_Outputs(Function, Function.body[1].body[1], ('Index', 'Value'), False), ('Value',))

    def test_Stable_Integer_Offset_Proof(self):
        Plan = dict(Index='I', Input_Types={'Start': 'integer', 'Other': 'integer'}, Written=('I',))
        Cases = (
            (('I - Start', 'I - Start'), ([(1, 0), (1, 0)], (('Start', -1),))),
            (('2 * I + Start', '2 * I + Start + 1'), ([(2, 0), (2, 1)], (('Start', 1),))),
            (('I + 2 * Start - Other',), ([(1, 0)], (('Other', -1), ('Start', 2)))),
            (('I * Start + I',), None),
            (('I + Start', 'I - Start'), None),
            (('I + Start * Other',), None),
        )
        for Sources, Expected in Cases:
            Nodes = [ast.parse(Source, mode='eval').body for Source in Sources]
            self.assertEqual(_Shifted_Forms(Nodes, Plan, {}), Expected, Sources)
        Plan['Written'] += ('Start',)
        self.assertIsNone(_Shifted_Forms([ast.parse('I + Start', mode='eval').body], Plan, {}))

    def test_Affine_Proof_Respects_Order_And_Rebinding(self):
        Cases = (
            ('J = 2 * I; K = J + 1; Output[K] = 1', (2, 1)),
            ('Output[J] = 1; J = 2 * I', None),
            ('J = K + 1; K = 2 * I; Output[J] = 1', None),
            ('J = 2 * I; J += 1; Output[J] = 1', None),
            ('J = 2 * I; del J; Output[J] = 1', None),
            ('if I:\n    J = 2 * I\nOutput[J] = 1', None),
        )
        for Source, Expected in Cases:
            Tree = ast.parse(Source)
            Index = next(Node.slice for Node in ast.walk(Tree) if isinstance(Node, ast.Subscript))
            self.assertEqual(_Affine_Outer(Index, 'I', _Stable_Values(Tree.body)), Expected, Source)

    def test_Floating_Use_Proof_Requires_Immediate_Promotion(self):
        Cases = (
            ('Output[I] = Source[I] * Factor', True),
            ('V = Source[I] * 0.5\nOutput[I] = Factor * V', True),
            ('Output[I] = Factor * 0.5', True),
            ('Output[I] = Factor * math.sin(Source[I])', True),
            ('Output[I] = math.sin(Factor) + Source[I]', True),
            ('Output[I] = Unknown(Factor) + Source[I]', False),
            ('Output[I] = Source[I] + Factor * Factor', False),
            ('V = Source[I]\nV = 2\nOutput[I] = V * Factor', False),
            ('Output[I] = Factor * V\nV = Source[I]', False),
            ('Output[I] = Source[Factor]', False),
            ('if Factor > 0:\n    Output[I] = Source[I] * Factor', False),
        )
        for Body, Expected in Cases:
            Outer = ast.parse('for I in range(N):\n' + '\n'.join('    ' + Line for Line in Body.splitlines())).body[0]
            self.assertEqual('Factor' in _Real_Inputs(Outer, ('Factor',), ('Source',), (), ('math.sin',)), Expected, Body)
