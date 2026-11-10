import unittest
from pathlib import Path
from PyCeler import Analyze, Loop_Finding
from Test.Benchmark_Large_Source import _Source
from Test.Workspace import Temporary_Directory

class Static_Ranking(unittest.TestCase):
    _Directory = Path(__file__).resolve().parent

    def test_Ranking_Preserves_Source_Order_And_Explains_Cost(self):
        Findings = Analyze(self._Directory / "Ranking_Loops.py")
        self.assertEqual([Item.Line for Item in Findings], sorted(Item.Line for Item in Findings))
        By_Name = {Item.Function: Item for Item in Findings}
        self.assertGreater(By_Name["Large"].Cost_Score, By_Name["Small"].Cost_Score)
        self.assertGreater(By_Name["Large"].Cost_Score, By_Name["Native_Calls"].Cost_Score)
        self.assertEqual(By_Name["Empty"].Cost_Score, 0)
        self.assertEqual(By_Name["Small"].Estimated_Iterations, 4)
        self.assertEqual(By_Name["Reverse"].Estimated_Iterations, 5)
        self.assertIn("possible native-library calls", By_Name["Native_Calls"].Cost_Reason)
        self.assertTrue(all(Item.Constraints for Item in Findings))
        self.assertTrue(all("not correctness eligibility or measured speedup" in Item.Cost_Reason for Item in Findings))

    def test_Dynamic_And_Shadowed_Ranges_Stay_Unknown(self):
        Findings = Analyze(self._Directory / "Ranking_Loops.py")
        By_Name = {Item.Function: Item for Item in Findings}
        for Name in ("Dynamic", "Early_Exit", "Shadowed"):
            with self.subTest(Name=Name):
                self.assertIsNone(By_Name[Name].Estimated_Iterations)
        Nested = [Item for Item in Findings if Item.Function == "Nested"]
        self.assertEqual([Item.Nesting_Depth for Item in Nested], [1, 2])

    def test_Native_Cost_Is_Explicitly_Unknown(self):
        Findings = Analyze(self._Directory / "Cython_Sources" / "Native_Loops.pyx")
        self.assertTrue(all(Item.Estimated_Iterations is None for Item in Findings))
        self.assertTrue(all("Native Cython cost" in Item.Cost_Reason for Item in Findings))

    def test_Original_Finding_Construction_Remains_Valid(self):
        Finding = Loop_Finding("Example", 1, 2, (), (), "Unknown", "Unproven")
        self.assertEqual(Finding.Cost_Score, 0.0)
        self.assertEqual(Finding.Transformations, ())
        self.assertIsNone(Finding.Estimated_Iterations)

    def test_Large_Source_Tracks_Each_Function_And_Loop(self):
        with Temporary_Directory(dir=self._Directory.parent / "Test_Run") as Folder:
            Source = Path(Folder) / "Many_Functions.py"
            Source.write_text(_Source(100), encoding="utf-8")
            Findings = Analyze(Source)
            self.assertEqual(len(Findings), 200)
            self.assertEqual([Item.Line for Item in Findings], sorted(Item.Line for Item in Findings))
            for Index in range(100):
                Group = Findings[Index * 2:Index * 2 + 2]
                self.assertTrue(all(Item.Function == f"Pipeline_{Index}" for Item in Group))
                self.assertTrue(all(Item.Classification == "Structural_Numeric_Map" for Item in Group))
                self.assertTrue(all("loop_fusion" in Item.Transformations for Item in Group))
