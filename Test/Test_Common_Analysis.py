import ast
import json
import unittest
from dataclasses import asdict
from pathlib import Path
from PyCeler import Analyze, Loop_Finding
from PyCeler.Common_Analysis import _Attach_Common_Plans, _Capability_Matrix, _Inventory, _Map_Adapter, _Map_Validate, _Plan_For

class Common_Analysis(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def _Plan(self, Source):
        Tree = ast.parse(Source)
        Entries, Parents = _Inventory(Tree)
        Node, Scope, Function = Entries[0]
        return _Plan_For(Node, Function, Parents)

    def test_New_Field_Preserves_Finding_Construction_And_Hashing(self):
        Finding = Loop_Finding("Example", 1, 2, (), (), "Unknown", "Unproven")
        self.assertIsNone(Finding.Plan)
        Findings = Analyze(self._Root / "Test" / "Coverage_Loops.py")
        self.assertTrue(all(Item.Plan is not None for Item in Findings))
        self.assertTrue(all(isinstance(hash(Item), int) for Item in Findings))

    def test_All_Loop_Forms_And_Comprehension_Clauses_Are_Accounted_For(self):
        Source = self._Root / "Test" / "Coverage_Loops.py"
        Tree = ast.parse(Source.read_text(encoding="utf-8"))
        Entries, _ = _Inventory(Tree)
        Findings = Analyze(Source)
        self.assertEqual(len(Entries), len(Findings))
        self.assertEqual(sorted(Node.lineno for Node, _, _ in Entries), sorted(Item.Line for Item in Findings))
        Kinds = {Item.Plan.Kind for Item in Findings}
        self.assertTrue({"For", "While", "AsyncFor", "ListComp", "SetComp", "DictComp", "GeneratorExp"} <= Kinds)
        Generator = next(Item for Item in Findings if Item.Plan.Kind == "GeneratorExp")
        self.assertEqual(Generator.Plan.Iteration_Clauses, 2)
        self.assertEqual(sum(Block.Kind == "Comprehension" for Block in Generator.Plan.Blocks), 2)

    def test_Name_Changes_Preserve_Normalized_Plan_Shape(self):
        Source = "def First(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = Source[Index] * 2\n    return Output\n"
        Left = self._Plan(Source)
        Right = self._Plan("def Second(Input, Result):\n    for Position in range(len(Result)):\n        Result[Position] = Input[Position] * 2\n    return Result\n")
        self.assertEqual(Left.Shape_Key, Right.Shape_Key)
        self.assertEqual(Left._Serialize(), self._Plan(Source)._Serialize())
        self.assertEqual(json.loads(Left._Serialize()), json.loads(json.dumps(asdict(Left))))
        self.assertEqual(len(Left._Fingerprint()), 64)

    def test_Dependencies_And_Aliasing_Are_Explicit(self):
        Independent = self._Plan("def Map(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = Source[Index] * 2\n    return Output\n")
        Dependent = self._Plan("def Prefix(Values):\n    for Index in range(1, len(Values)):\n        Values[Index] += Values[Index - 1]\n    return Values\n")
        Indirect = self._Plan("def Scatter(Values, Indices):\n    for Index in range(len(Values)):\n        Values[Indices[Index]] = Index\n    return Values\n")
        self.assertFalse(any("cross-iteration" in Item for Item in Independent.Blockers))
        self.assertTrue(any("overlapping" in Item for Item in Independent.Guards))
        self.assertEqual(Dependent.Parallel_Status, "rejected_dependency")
        self.assertTrue(any("cross-iteration" in Item for Item in Dependent.Blockers))
        self.assertTrue(any("unique, bounded" in Item for Item in Indirect.Blockers))

    def test_Liveness_Branch_Merges_And_Entry_Inputs(self):
        Plan = self._Plan("def Sum(Values, Flag):\n    Total = 0\n    for Index in range(len(Values)):\n        Temporary = Values[Index]\n        if Flag:\n            Updated = Temporary + 1\n        else:\n            Updated = Temporary + 2\n        Total += Updated\n    return Total, Index\n")
        self.assertIn("Total", Plan.Loop_Carried)
        self.assertNotIn("Temporary", Plan.Inputs)
        self.assertNotIn("Updated", Plan.Inputs)
        self.assertEqual(Plan.Live_Out, ("Index", "Total"))
        Branch = next(Block for Block in Plan.Blocks if Block.Kind == "If")
        self.assertEqual(len(Branch.Successors), 2)
        Partial = self._Plan("def Partial(Values, Flag):\n    for Index in range(len(Values)):\n        if Flag:\n            Previous = Values[Index]\n        Values[Index] = Previous\n    return Values\n")
        self.assertIn("Previous", Partial.Loop_Carried)

    def test_Annotations_Are_Hints_And_Unknown_Calls_Are_Boundaries(self):
        Plan = self._Plan("def Run(Count: int, Callback):\n    Total = 0\n    for Index in range(Count):\n        Total += Callback(Index)\n    return Total\n")
        Facts = {Fact.Name: Fact for Fact in Plan.Type_Facts}
        self.assertEqual(Facts["Count"].Evidence, "annotation_hint")
        self.assertEqual(Facts["Count"].Category, "unknown")
        self.assertEqual(Facts["Total"].Evidence, "static_assignment")
        Callback = next(Call for Call in Plan.Calls if Call.Name == "Callback")
        self.assertEqual(Callback.Effect, "unknown")
        self.assertEqual(Callback.Status, "python_boundary")

    def test_Suspension_Exception_And_Short_Circuit_Boundaries(self):
        Plan = self._Plan("async def Run(Values, Callback):\n    async for Value in Values:\n        try:\n            if Value and Callback(Value):\n                yield Value\n        finally:\n            await Callback(None)\n")
        self.assertIn("suspension", Plan.Effects)
        self.assertIn("python_control_boundary", Plan.Effects)
        self.assertIn("suspension", Plan.Exits)
        self.assertTrue(any(Expression.Evaluation == "short_circuit" for Expression in Plan.Expressions))

    def test_Map_Adapter_Is_Validated_And_Name_Independent(self):
        Plan = dict(Names=("Source", "Output"), Output="Output", Arrays={"Source", "Output"}, Scalars=set(), Reads={0},
                    Indices=("Index",), Lines=["V1[Index] = V0[Index] * 2"])
        Common = _Map_Adapter(Plan)
        self.assertEqual((Common.Dimensions, Common.Output, Common.Arrays), (1, 1, (0, 1)))
        self.assertEqual(_Map_Validate(Plan), Common)
        Plan["Common"] = Common
        Plan["Lines"] = ["V1[Index] = 3"]
        with self.assertRaisesRegex(ValueError, "disagree"):
            _Map_Validate(Plan)

    def test_Capabilities_Separate_Static_Candidates_From_Native_Entry(self):
        Findings = Analyze(self._Root / "Test" / "Numeric_Loops.py", OpenMP=True)
        Rows = _Capability_Matrix(Findings)
        self.assertEqual(Rows[0]["Serial"], "guarded_candidate")
        self.assertEqual(Rows[0]["Parallel"], "guarded_candidate")
        self.assertEqual(Rows[1]["Serial"], "python_retained")
        self.assertEqual(Rows[1]["Parallel"], "rejected_dependency")
        self.assertTrue(all(Row["Native_Entry"] == "not_observed_by_static_analysis" for Row in Rows))

    def test_Actual_Math_Calls_Expose_Registry_Contracts(self):
        Findings = Analyze(self._Root / "Test" / "Coverage_Loops.py")
        Math = next(Item for Item in Findings if Item.Function == "Math_Map")
        Calls = [Call for Call in Math.Plan.Calls if Call.Name.startswith("math.")]
        self.assertEqual([Call.Name for Call in Calls], ["math.sin", "math.sqrt"])
        self.assertTrue(all(Call.Contract and Call.Effect == "conditional_numeric" for Call in Calls))

    def test_Shadowed_And_Invalid_Math_Calls_Are_Unknown_Effects(self):
        Sources = (("import math\ndef Run(Values, math):\n    for Value in Values:\n        math.sin(Value)\n", "Shadowed"),
                   ("import math\ndef Run(Values):\n    for Value in Values:\n        math.sin()\n", "Invalid_Call_Form"))
        for Source, Status in Sources:
            with self.subTest(Status=Status):
                Tree = ast.parse(Source)
                Entries, _ = _Inventory(Tree)
                Findings = [Loop_Finding(Scope, Node.lineno, Node.end_lineno, (), (), "Unknown", "Unproven") for Node, Scope, Function in Entries]
                Finding = _Attach_Common_Plans(Tree, Findings)[0]
                Call = next(Call for Call in Finding.Plan.Calls if Call.Name == "math.sin")
                self.assertEqual(Call.Status, Status)
                self.assertEqual(Call.Effect, "unknown")
                self.assertTrue(any("Unknown calls" in Reason for Reason in Finding.Plan.Blockers))
