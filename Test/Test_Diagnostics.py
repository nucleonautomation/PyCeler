import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Convert, Loop_Finding
from Test.Workspace import Temporary_Directory

class Optimization_Diagnostics(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)

    def test_Finding_Construction_Remains_Compatible(self):
        Finding = Loop_Finding("Example", 1, 2, (), (), "Unknown", "Unproven")
        self.assertEqual(Finding.Diagnostics, ())

    def test_All_Blockers_Have_Exact_Source_Locations(self):
        Findings = Analyze(self._Root / "Test" / "Diagnostic_Loops.py")
        Function = Findings[0]
        By_Code = {Item["Code"]: Item for Item in Function.Diagnostics}
        self.assertIn("no_scalar_return_or_region", By_Code)
        self.assertIn("unsupported_scalar_operator", By_Code)
        self.assertIn("unproven_call_boundary", By_Code)
        self.assertEqual(By_Code["unsupported_scalar_operator"]["Line"], 6)
        self.assertEqual(By_Code["unproven_call_boundary"]["Line"], 7)
        self.assertIn("MatMult", Function.Reason)
        self.assertIn("Callback", Function.Reason)
        self.assertTrue(all(Item["Suggestion"] and Item["Column"] > 0 for Item in Function.Diagnostics))
        self.assertIsInstance(hash(Function), int)

    def test_Module_Diagnostic_Preserves_Additional_Blockers(self):
        Finding = Analyze(self._Root / "Test" / "Diagnostic_Loops.py")[1]
        self.assertIsNone(Finding.Function)
        Codes = {Item["Code"] for Item in Finding.Diagnostics}
        self.assertTrue({"unproven_module_region", "unsupported_scalar_operator", "unproven_call_boundary"} <= Codes)

    def test_Recognized_Modulo_Does_Not_Report_Unsupported(self):
        Source = self._Folder / "Modulo.py"
        Source.write_text("def Calculate(Count):\n    Total = 0\n    for Index in range(Count):\n        Total += (Index * Index + 7 * Index) % 999983\n    return Total\n", encoding="utf-8")
        Finding = Analyze(Source)[0]
        self.assertNotEqual(Finding.Change, "Keep original loop")
        self.assertFalse(any(Item["Severity"] == "unsupported" for Item in Finding.Diagnostics))

    def test_Overflow_Is_A_Conservative_Warning(self):
        Template = "def Calculate():\n    Total = 0\n    Iterations = 100_000_000\n    for Index in range(Iterations):\n        Total += (Index * Index + Index * 7) OP 999983\n    return Total\n"
        for Operator, Expected in (("*", True), ("%", False)):
            with self.subTest(Operator=Operator):
                Source = self._Folder / "Bounds.py"
                Source.write_text(Template.replace("OP", Operator), encoding="utf-8")
                Finding = Analyze(Source)[0]
                Warnings = [Item for Item in Finding.Diagnostics if Item["Code"] == "integer_range_may_overflow"]
                self.assertEqual(bool(Warnings), Expected)
                self.assertTrue(all(Item["Severity"] == "warning" for Item in Warnings))

    def test_No_Candidates_Report_Explains_Unchanged_Loops(self):
        with patch("PyCeler.Engine._Build", side_effect=AssertionError("No candidate should be built")):
            Output = Convert(self._Root / "Test" / "Diagnostic_Loops.py", self._Folder / "Converted")
        Report = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(Report["Status"], "no_candidates")
        self.assertEqual(Report["Summary"]["Candidate_Regions"], 0)
        self.assertEqual(Report["Summary"]["Native_Selected_Regions"], 0)
        self.assertEqual(Report["Summary"]["Skipped_Loops"], 2)
        self.assertEqual(Report["Builds"], {})
        self.assertTrue(all(Item["Diagnostics"] for Item in Report["Skipped"]))

    def test_Comprehensions_And_Generators_Are_Detected_Without_Execution(self):
        Source = self._Folder / "Comprehensions.py"
        Source.write_text("raise AssertionError('Analysis must not execute source')\ndef Calculate(Count):\n    Squares = [Index * Index for Index in range(10)]\n    Values = {Index for Index in range(Count)}\n    Mapping = {Index: Index + 1 for Index in range(Count) if Index}\n    return sum(A * B for A in range(3) for B in range(4))\n", encoding="utf-8")
        Findings = Analyze(Source)
        self.assertEqual(len(Findings), 4)
        self.assertEqual([Item.Classification for Item in Findings], ["Comprehension_Loop"] * 3 + ["Generator_Expression"])
        self.assertEqual([Item.Estimated_Iterations for Item in Findings], [10, None, None, 12])
        self.assertTrue(all(Item.Diagnostics[0].Code == "unproven_comprehension" for Item in Findings))
        with patch("PyCeler.Engine._Build", side_effect=AssertionError("Unsupported expressions must not build probes")):
            Output = Convert(Source, self._Folder / "Converted")
        Report = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(Report["Status"], "no_candidates")
        self.assertEqual(Report["Summary"]["Skipped_Loops"], 4)

    def test_Empty_Analysis_Still_Produces_A_Report(self):
        Source = self._Folder / "No_Loops.py"
        Source.write_text("Result = 42\n", encoding="utf-8")
        self.assertEqual(Analyze(Source), ())
        with patch("PyCeler.Engine._Build", side_effect=AssertionError("No candidate should be built")):
            Output = Convert(Source, self._Folder / "Converted")
        Report = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(Report["Status"], "no_candidates")
        self.assertEqual(Report["Summary"]["Candidate_Regions"], 0)
        self.assertEqual(Report["Summary"]["Skipped_Loops"], 0)
        self.assertEqual(Report["Builds"], {})

    def test_Disabled_Measurement_Still_Reports_Static_Findings(self):
        with patch("PyCeler.Engine._Build", side_effect=AssertionError("Disabled selection must not build probes")):
            Output = Convert(self._Root / "Test" / "Diagnostic_Loops.py", self._Folder / "Unmeasured", Select=False)
        Report = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(Report["Status"], "measurement_disabled")
        self.assertFalse(Report["Measurement"])
        self.assertEqual(len(Report["Findings"]), 2)
        self.assertEqual(Report["Builds"], {})

    def test_Failed_Candidate_Build_Is_Distinct_From_No_Candidates(self):
        with patch("PyCeler.Engine._Build", side_effect=RuntimeError("simulated compiler failure")):
            Output = Convert(self._Root / "Test" / "Numeric_Loops.py", self._Folder / "Converted")
        Report = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(Report["Summary"]["Candidate_Regions"], 1)
        self.assertEqual(Report["Summary"]["Native_Selected_Regions"], 0)
        self.assertEqual(Report["Items"][0]["Status"], "no_native_candidate_built")
        self.assertIn("separate operation", Report["Summary"]["Scope"])

    def test_Cli_Prints_Selection_Summary(self):
        Spec = importlib.util.spec_from_file_location("PyCeler_Diagnostic_Cli", self._Root / "Compile.py")
        Module = importlib.util.module_from_spec(Spec)
        Spec.loader.exec_module(Module)
        Binary = self._Folder / "Example.pyd"
        Report = dict(Status="no_candidates", Summary=dict(Candidate_Regions=0, Native_Selected_Regions=0, Skipped_Loops=1))
        Binary.with_suffix(".selection.json").write_text(json.dumps(Report), encoding="utf-8")
        Stream = io.StringIO()
        with contextlib.redirect_stdout(Stream):
            Module._Print_Selection_Summary(Binary)
        self.assertIn("0 candidate regions", Stream.getvalue())
        self.assertIn("original loops remain unchanged", Stream.getvalue())
        Report.update(Status="measurement_disabled", Measurement=False)
        Report["Summary"]["Candidate_Regions"] = 1
        Binary.with_suffix(".selection.json").write_text(json.dumps(Report), encoding="utf-8")
        Stream = io.StringIO()
        with contextlib.redirect_stdout(Stream):
            Module._Print_Selection_Summary(Binary)
        self.assertIn("Measurement disabled", Stream.getvalue())
        self.assertIn("1 eligible regions", Stream.getvalue())
        self.assertNotIn("retained Python", Stream.getvalue())
