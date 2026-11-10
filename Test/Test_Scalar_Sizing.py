import ast
import unittest
from PyCeler.Engine import _Scalar_Size_Cases, _Scalar_Size_Plan, _Scalar_Workload_Size

class Scalar_Workload_Sizing(unittest.TestCase):
    def _Plan(self, Source):
        Function = ast.parse(Source).body[0]
        Loops = [Node for Node in ast.walk(Function) if isinstance(Node, (ast.For, ast.While))]
        return _Scalar_Size_Plan(dict(Names=tuple(Arg.arg for Arg in Function.args.args), Loops=Loops, Size_Function=Function))

    def test_Range_Counts_Match_Python(self):
        for Begin in (-11, -1, 0, 1, 15):
            for End in (-13, -1, 0, 1, 18):
                for Step in (-7, -2, -1, 1, 2, 7):
                    Sizing = dict(Ranges=[(True, 1, True, 2, Step)], Bounds=[])
                    self.assertEqual(_Scalar_Workload_Size(Sizing, (0, Begin, End)), len(range(Begin, End, Step)))

    def test_Sizing_Does_Not_Invoke_Unsupported_Operands(self):
        class Foreign:
            def __sub__(self, Other):
                raise AssertionError("Sizing invoked user arithmetic")
        Sizing = dict(Ranges=[(True, 0, True, 1, 1)], Bounds=[])
        self.assertEqual(_Scalar_Workload_Size(Sizing, (Foreign(), 10)), 0)
        self.assertEqual(_Scalar_Workload_Size(Sizing, (False, 10)), 0)

    def test_Reordered_Range_Arguments_Generate_Nonempty_Probes(self):
        for Step in (1, 3, -1, -3):
            Sizing = dict(Ranges=[(True, 2, True, 1, Step)], Bounds=[], Arguments=[2, 1], Vary=[1])
            Cases = list(_Scalar_Size_Cases(dict(Size_Plan=Sizing, Arguments=3)))
            self.assertEqual([Case[1] for Case in Cases], [4, 256, 32768])
            for Key, Size, Shape, Args in Cases:
                self.assertEqual(Args[0], 2)
                self.assertEqual(Size, len(range(Args[2], Args[1], Step)))

    def test_Literal_Stop_Varies_Start_For_Descending_Range(self):
        Sizing = dict(Ranges=[(True, 1, False, -10, -2)], Bounds=[], Arguments=[1], Vary=[1])
        Cases = list(_Scalar_Size_Cases(dict(Size_Plan=Sizing, Arguments=2)))
        self.assertEqual([Case[1] for Case in Cases], [4, 256, 32768])
        self.assertTrue(all(Size == len(range(Args[1], -10, -2)) for Key, Size, Shape, Args in Cases))

    def test_No_Dependency_Does_Not_Guess_First_Argument(self):
        Sizing = dict(Ranges=[(False, 0, False, 17, 1)], Bounds=[], Arguments=[], Vary=[])
        Cases = list(_Scalar_Size_Cases(dict(Size_Plan=Sizing, Arguments=2)))
        self.assertEqual(Cases, [("int", 17, (), (2, 2))])
        self.assertEqual(_Scalar_Workload_Size(Sizing, (0, -100)), 17)

    def test_Rectangular_Ranges_And_Arbitrary_Precision_Counts(self):
        Sizing = dict(Ranges=[(True, 0, True, 1, 3), (False, 0, True, 2, 1)], Bounds=[])
        self.assertEqual(_Scalar_Workload_Size(Sizing, (5, 20, 7)), 35)
        self.assertEqual(_Scalar_Workload_Size(dict(Ranges=[(False, -(2**63), False, 2**63, 1)], Bounds=[]), ()), 2**64)

    def test_Shared_Nested_Bound_Does_Not_Create_Excessive_Probes(self):
        Sizing = dict(Ranges=[(False, 0, True, 0, 1), (False, 0, True, 0, 1)], Bounds=[], Arguments=[0], Vary=[0])
        Cases = list(_Scalar_Size_Cases(dict(Size_Plan=Sizing, Arguments=1)))
        self.assertLessEqual(max(Case[1] for Case in Cases), 40000)
        self.assertTrue(all(Size == Args[0] ** 2 for Key, Size, Shape, Args in Cases))

    def test_Overwritten_Argument_Is_Not_Used_As_A_Size(self):
        Sizing = self._Plan("def Count(Amount):\n    Amount = 5\n    Total = 0\n    for Index in range(Amount):\n        Total += Index\n    return Total\n")
        self.assertEqual(Sizing["Arguments"], [])
        self.assertEqual(Sizing["Ranges"], [])
        self.assertEqual(Sizing["Overwritten_Arguments"], ["Amount"])
        self.assertFalse(Sizing["Exact"])

    def test_Outer_Loop_Mutation_Invalidates_Nested_Input_Bound(self):
        Sizing = self._Plan("def Count(Rows, Columns):\n    Total = 0\n    for Row in range(Rows):\n        for Column in range(Columns):\n            Total += Column\n        Columns = 0\n    return Total\n")
        self.assertEqual(Sizing["Arguments"], [0])
        self.assertEqual(Sizing["Overwritten_Arguments"], ["Columns"])
        self.assertEqual(_Scalar_Workload_Size(Sizing, (8, 9)), 8)

    def test_Snapshotted_Range_Bound_Can_Change_Inside_Its_Own_Body(self):
        Sizing = self._Plan("def Count(Amount):\n    Total = 0\n    for Index in range(Amount):\n        Amount = 0\n        Total += Index\n    return Total\n")
        self.assertEqual(Sizing["Arguments"], [0])
        self.assertEqual(Sizing["Overwritten_Arguments"], [])
        self.assertTrue(Sizing["Exact"])
        self.assertEqual(_Scalar_Workload_Size(Sizing, (19,)), 19)

    def test_While_Bound_Uses_Stop_Argument(self):
        Sizing = self._Plan("def Count(Start, Stop):\n    Total = 0\n    while Start < Stop:\n        Total += Start\n        Start += 1\n    return Total\n")
        self.assertEqual(Sizing["Bounds"], [1])
        self.assertEqual(Sizing["Arguments"], [1])
        self.assertFalse(Sizing["Exact"])
