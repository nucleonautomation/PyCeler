import unittest
from pathlib import Path
from PyCeler import Analyze

class Source_Analysis(unittest.TestCase):
    _Directory = Path(__file__).resolve().parent

    def test_Reference_Loop_Locations_And_Accesses(self):
        Clear, Prefix = Analyze(self._Directory / "Numeric_Loops.py")
        self.assertEqual((Clear.Function, Clear.Line, Clear.End_Line), ("Clear_Elements", 2, 3))
        self.assertEqual(Clear.Indexed_Reads, ())
        self.assertEqual(Clear.Indexed_Writes, ("Values[Index]",))
        self.assertEqual((Prefix.Function, Prefix.Line, Prefix.End_Line), ("Prefix_Sum", 7, 8))
        self.assertEqual(Prefix.Indexed_Reads, ("Values[Index]", "Values[Index - 1]"))
        self.assertEqual(Prefix.Indexed_Writes, ("Values[Index]",))

    def test_Independent_Write_Requires_Runtime_Checks(self):
        Clear, _ = Analyze(self._Directory / "Numeric_Loops.py")
        self.assertEqual(Clear.Classification, "Potential_Independent_Write")
        for Condition in ("Values[Index]", "built-in range and len", "writable", "dtype", "layout", "distinct element storage"):
            with self.subTest(Condition=Condition):
                self.assertIn(Condition, Clear.Reason)

    def test_Prefix_Sum_Explains_Parallel_Rejection(self):
        _, Prefix = Analyze(self._Directory / "Numeric_Loops.py")
        self.assertEqual(Prefix.Classification, "Loop_Carried_Dependency")
        self.assertIn("Values[Index - 1]", Prefix.Reason)
        self.assertIn("preceding iteration", Prefix.Reason)
        self.assertIn("ineligible", Prefix.Reason)

    def test_Analysis_Never_Executes_Target(self):
        Findings = Analyze(str(self._Directory / "Static_Only_Loops.py"))
        Method = Findings[0]
        self.assertEqual((Method.Function, Method.Line, Method.End_Line), ("Example.Clear", 5, 6))
        self.assertEqual(Method.Classification, "Potential_Independent_Write")
        self.assertEqual(Method.Indexed_Writes, ("Buffer[Position]",))

    def test_Unsupported_Patterns_Are_Unknown(self):
        Findings = Analyze(self._Directory / "Static_Only_Loops.py")
        Cases = [(Finding.Function, Finding.Classification) for Finding in Findings]
        self.assertEqual(Cases, [
            ("Example.Clear", "Potential_Independent_Write"),
            ("Indirect_Write", "Unknown"),
            ("With_Call", "Unknown"),
            ("Other_Source", "Unknown"),
            ("Other_Bounds", "Unknown"),
            ("Nested", "Unknown"),
            ("Nested", "Potential_Independent_Write"),
        ])
        self.assertIn("bounds", Findings[4].Reason)
        self.assertEqual(Findings[1].Indexed_Reads, ("Indices[Index]",))
        self.assertEqual(Findings[1].Indexed_Writes, ("Values[Indices[Index]]",))
        self.assertEqual(Findings[5].Indexed_Writes, ())
        self.assertEqual(Findings[6].Indexed_Writes, ("Values[Index]",))
