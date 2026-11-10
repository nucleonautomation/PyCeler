from Test.Workspace import Temporary_Directory
import unittest
from pathlib import Path
from PyCeler import Analyze, Convert

class Cython_Source_Analysis(unittest.TestCase):
    _Directory = Path(__file__).resolve().parent / "Cython_Sources"
    _Run_Root = Path(__file__).resolve().parent.parent / "Test_Run"

    def test_Native_Loops_Keep_Types_And_Report_Included_Source(self):
        Source = self._Directory / "Native_Loops.pyx"
        Original = Source.read_bytes()
        Findings = Analyze(Source)
        self.assertEqual([Item.Function for Item in Findings], ["Fill_Helper", "Fill", "Prefix", "Parallel_Fill", "Example.Count"])
        self.assertEqual(Path(Findings[0].Source), self._Directory / "Native_Helper.pxi")
        self.assertEqual((Findings[0].Line, Findings[0].End_Line), (3, 4))
        self.assertEqual((Findings[1].Line, Findings[1].End_Line), (8, 9))
        self.assertEqual(Findings[1].Indexed_Writes, ("Values[Index]",))
        self.assertEqual(Findings[2].Classification, "Loop_Carried_Dependency")
        self.assertEqual(Findings[2].Indexed_Reads, ("Values[Index]", "Values[Index - 1]"))
        self.assertEqual(Findings[3].Classification, "Existing_OpenMP_Loop")
        self.assertEqual(Findings[4].Classification, "Cython_Loop")
        self.assertEqual(Source.read_bytes(), Original)

    def test_Convert_Preserves_Native_Source_And_Include_Bytes(self):
        self._Run_Root.mkdir(exist_ok=True)
        Source = self._Directory / "Native_Loops.pyx"
        Include = self._Directory / "Native_Helper.pxi"
        with Temporary_Directory(prefix="Cython_Convert_", dir=self._Run_Root) as Folder:
            Output = Convert(Source, Path(Folder) / "Output", Select=False)
            self.assertEqual(Output.read_bytes(), Source.read_bytes())
            self.assertEqual((Output.parent / Include.name).read_bytes(), Include.read_bytes())

    def test_Direct_Include_And_Context_Diagnostic(self):
        Findings = Analyze(self._Directory / "Native_Helper.pxi")
        self.assertEqual(len(Findings), 1)
        self.assertEqual(Findings[0].Function, "Fill_Helper")
        self._Run_Root.mkdir(exist_ok=True)
        with Temporary_Directory(prefix="Cython_Context_", dir=self._Run_Root) as Folder:
            Include = Path(Folder) / "Context.pxi"
            Include.write_text("    cdef int Value\n", encoding="utf-8")
            Context = Analyze(Include)
            self.assertEqual(Context[0].Classification, "Cython_Context_Required")
            self.assertIn("owning .pyx", Context[0].Reason)

    def test_Compile_Time_Expressions_Are_Not_Evaluated(self):
        self._Run_Root.mkdir(exist_ok=True)
        with Temporary_Directory(prefix="Cython_Static_", dir=self._Run_Root) as Folder:
            Source = Path(Folder) / "Compile_Time.pyx"
            Source.write_text('DEF Value = int("must not evaluate")\n', encoding="utf-8")
            Findings = Analyze(Source)
            self.assertEqual(Findings[0].Classification, "Cython_Static_Unsupported")
            self.assertIn("without evaluation", Findings[0].Reason)
            Include = Path(Folder) / "Compile_Time.pxi"
            Include.write_bytes(Source.read_bytes())
            Source.write_text('include "Compile_Time.pxi"\n', encoding="utf-8")
            Findings = Analyze(Source)
            self.assertEqual(Findings[0].Classification, "Cython_Static_Unsupported")
            self.assertEqual(Path(Findings[0].Source), Include)

    def test_Native_Syntax_Error_Is_Actionable(self):
        self._Run_Root.mkdir(exist_ok=True)
        with Temporary_Directory(prefix="Cython_Invalid_", dir=self._Run_Root) as Folder:
            Source = Path(Folder) / "Invalid.pyx"
            Source.write_text("cdef int =\n", encoding="utf-8")
            with self.assertRaisesRegex(SyntaxError, "Unable to parse Cython source"):
                Analyze(Source)
