import ast
import builtins
import importlib.util
import io
import sys
import sysconfig
import tokenize
import unittest
from pathlib import Path
from unittest.mock import patch

Root = Path(__file__).resolve().parents[1]
Spec = importlib.util.spec_from_file_location("_Fast_Erf_Staged", Root / "PyCeler/Fast_Math.py")
Fast = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Fast)

def _Backend(Version="3.14.8 (tags/v3.14.8) [MSC v.1944 64 bit (AMD64)]"):
    Namespace = {"__builtins__": dict(vars(builtins))}
    exec(compile(Fast._Fast_Erf_Backend_Source("_Test_"), "Erf_Backend.py", "exec"), Namespace)
    return Namespace["_Test_Erf_Backend"](Version)

def _Plan(Expression, Imports="import math"):
    Tree = ast.parse(Imports + "\ndef Compute(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = " + Expression + "\n    return Output\n")
    Function = Tree.body[-1]
    return Fast._Fast_Math_Plan(dict(Loops=[Function.body[0]], Indices=["Index"], Scalars=[], Locals=[], Output="Output", Names=["Source", "Output"], Math_Imports=Imports.splitlines()))

class Erf_Backend(unittest.TestCase):
    def test_CPython_Direct_Libm_Versions(self):
        for Version in ("3.12.0 (main) [GCC]", "3.13.9 (main) [Clang]", "3.14.8 (main) [MSC]"):
            with self.subTest(Version=Version):
                self.assertTrue(_Backend(Version))

    def test_CPython_311_Always_Retains_Original_Backend(self):
        with patch.object(sysconfig, "get_config_var", return_value=1):
            self.assertFalse(_Backend("3.11.9 (main) [MSC]"))

    def test_Unknown_Interpreters_Versions_And_Malformed_Values_Fail_Closed(self):
        for Version in ("3.10.0", "3.15.0", "4.0.0", "3.12.0 [PyPy]", "3.14.0 [GraalPy]", "unknown", "", None):
            with self.subTest(Version=Version):
                self.assertFalse(_Backend(Version))

    def test_Mutable_Python_Metadata_Cannot_Override_Runtime_C_Version(self):
        with patch.object(sys, "version_info", (3, 14)), patch.object(sysconfig, "get_config_var", return_value=1):
            self.assertFalse(_Backend("3.11.9 (main) [MSC]"))
        with patch.object(sys, "version_info", (3, 11)), patch.object(sysconfig, "get_config_var", return_value=None):
            self.assertTrue(_Backend("3.14.8 (main) [MSC]"))

    def test_Mutable_Builtin_Conversions_Cannot_Enable_Another_Runtime(self):
        with patch.object(builtins, "int", return_value=12), patch.object(builtins, "tuple", return_value=(3, 14)):
            self.assertFalse(_Backend("3.11.9 (main) [MSC]"))
            self.assertTrue(_Backend("3.14.8 (main) [MSC]"))

    def test_Module_Alias_Direct_Alias_And_Composition_Require_Backend(self):
        Cases = (("math.erf(Source[Index])", "import math"), ("M.erfc(Source[Index])", "import math as M"), ("Operation(Source[Index])", "from math import erf as Operation"), ("math.erfc(math.erf(Source[Index]))", "import math"))
        for Expression, Imports in Cases:
            with self.subTest(Expression=Expression):
                Plan = _Plan(Expression, Imports)
                self.assertEqual(Plan["Backend_Requirements"], ("Runtime_CPython_Libm_Erf",))
                self.assertEqual(Plan["Version"], 2)

    def test_Generated_Backend_Guard_Precedes_Array_Views_And_Allocation(self):
        Plan = _Plan("math.erf(Source[Index])")
        for Parallel in (False, True):
            Source = Fast._Fast_Math_Kernel(Plan, 7, Parallel)
            self.assertIn('const char* _Pyceler_Fast_7_Runtime_Version "Py_GetVersion"()', Source)
            self.assertIn('cdef bint _Pyceler_Fast_7_Erf_Backend_Eligible = _Pyceler_Fast_7_Erf_Backend((<bytes>_Pyceler_Fast_7_Runtime_Version()).decode("ascii"))', Source)
            Guard = Source.index("    if not _Pyceler_Fast_7_Erf_Backend_Eligible:")
            self.assertLess(Guard, Source.index("    Output = Args["))
            self.assertLess(Guard, Source.index("    Scratch = <double*>"))
            self.assertNotIn("sysconfig", Source)
            self.assertNotIn("version_info", Source)

    def test_Preexisting_Functions_Do_Not_Acquire_The_New_Gate(self):
        Plan = _Plan("math.sin(Source[Index])")
        self.assertEqual(Plan["Backend_Requirements"], ())
        self.assertNotIn("Erf_Backend", Fast._Fast_Math_Kernel(Plan, 7, True))

    def test_Erf_Plan_Retains_Existing_Finite_Scratch_Commit_Contract(self):
        Source = Fast._Fast_Math_Kernel(_Plan("math.erfc(Source[Index])"), 7, True)
        for Text in ("cdef volatile double", "not _Pyceler_Fast_7_isfinite(X0)", "_Pyceler_Fast_7_signbit(X0)", "Scratch[Position - Offset]", "if not Valid or not", "Prepare_Exceptions", "Set_Environment(&Previous)", "_Pyceler_Fast_7_Commit(Scratch"):
            self.assertIn(Text, Source)

    def test_Private_Prefix_Rename_Preserves_Runtime_C_Symbol_And_User_Literals(self):
        Location = Root / "PyCeler/Math_Maps.py"
        if not Location.is_file():
            Location = Root.parents[2] / "PyCeler/Math_Maps.py"
        Tree = ast.parse(Location.read_text(encoding="utf-8"))
        Function = next(Node for Node in Tree.body if isinstance(Node, ast.FunctionDef) and Node.name == "_Native_Prefix")
        Namespace = dict(io=io, tokenize=tokenize)
        exec(compile(ast.Module(body=[Function], type_ignores=[]), str(Location), "exec"), Namespace)
        Source = Fast._Fast_Math_Kernel(_Plan("math.erf(Source[Index])"), 7, True) + "\nUser_Text = '_Pyceler_keep_this_literal'\n"
        Rewritten = Namespace["_Native_Prefix"](Source, "_Private_")
        self.assertIn('const char* _Private_Fast_7_Runtime_Version "Py_GetVersion"()', Rewritten)
        self.assertIn("if not _Private_Fast_7_Erf_Backend_Eligible:", Rewritten)
        self.assertNotIn("_Pyceler_Fast_7_", Rewritten)
        self.assertIn("User_Text = '_Pyceler_keep_this_literal'", Rewritten)

if __name__ == "__main__":
    unittest.main()
