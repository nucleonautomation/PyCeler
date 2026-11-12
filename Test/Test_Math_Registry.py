import ast
import cmath
import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path
from unittest import mock

_Path = Path(__file__).resolve().parents[1] / "PyCeler" / "Math_Registry.py"
_Spec = importlib.util.spec_from_file_location("_PyCeler_Math_Registry_Test", _Path)
_Registry = importlib.util.module_from_spec(_Spec)
_Spec.loader.exec_module(_Registry)

class Math_Registry(unittest.TestCase):
    def test_Standard_Library_Inventory_Is_Complete(self):
        for Module in (math, cmath):
            Expected = {Name for Name in dir(Module) if not Name.startswith("_")}
            Actual = {Record["Name"] for Record in _Registry._Math_Registry() if Record["Module"] == Module.__name__ and Record["Available"]}
            with self.subTest(Module=Module.__name__):
                self.assertEqual(Actual, Expected)

    def test_Numpy_And_Builtin_Inventory(self):
        Expected = "add subtract multiply divide true_divide floor_divide power float_power square reciprocal positive negative absolute fabs sign sqrt cbrt exp exp2 expm1 log log2 log10 log1p logaddexp logaddexp2 sin cos tan arcsin arccos arctan arctan2 hypot degrees radians deg2rad rad2deg unwrap sinh cosh tanh arcsinh arccosh arctanh sinc i0 round around rint fix floor ceil trunc fmod mod remainder modf divmod copysign signbit frexp ldexp nextafter spacing isfinite isinf isnan isclose allclose minimum maximum fmin fmax clip gcd lcm sum prod min max mean var std nansum nanprod nanmin nanmax nanmean nanvar nanstd cumsum cumprod nancumsum nancumprod diff gradient real imag angle conj conjugate".split()
        for Name in Expected:
            with self.subTest(Name=Name):
                Record = _Registry._Math_Record("numpy", Name)
                self.assertIsNotNone(Record)
                self.assertIsNone(Record["Available"])
                self.assertEqual(Record["Native_Availability"], "Existing_Numpy_Implementation")
        for Name in "abs round pow divmod sum min max int float complex bool".split():
            self.assertIsNotNone(_Registry._Math_Record("builtins", Name))

    def test_Every_Record_Has_An_Explicit_Contract(self):
        Fields = ("Qualified_Name", "Kind", "Category", "Inputs", "Conversions", "Return_Type", "Domain", "Precision", "Exceptions", "Native_Availability", "Fallback_Reason", "Binding_Contract", "Documentation")
        for Record in _Registry._Math_Registry():
            with self.subTest(Name=Record["Qualified_Name"]):
                for Field in Fields:
                    self.assertTrue(Record[Field], Field)
                self.assertEqual(Record["Registry_Version"], 3)
                Unboxed = Record["Module"] == "math" and Record["Name"] in _Registry._Guarded_Unboxed and Record["Available"] is not False
                self.assertEqual(Record["Native_Implemented"], Unboxed)
                self.assertEqual(Record["Nogil_Eligible"], Unboxed)
                self.assertEqual(Record["Ordered_Loop_Implemented"], Record["Kind"] == "Function" and Record["Available"] is not False)
                if Unboxed:
                    self.assertTrue(Record["Native_Requirements"])
                    self.assertEqual(Record["Status"], "Guarded_Unboxed_Region_Support")
                elif Record["Kind"] == "Constant":
                    self.assertEqual(Record["Status"], "Python_Retained")
                else:
                    self.assertEqual(Record["Status"], "Ordered_Loop_Support" if Record["Available"] is not False else "Unavailable")

    def test_Version_Gates_Are_Independent_Of_Host(self):
        for Version in ((3, 11), (3, 12), (3, 13), (3, 14)):
            with self.subTest(Version=Version):
                self.assertEqual(_Registry._Math_Record("math", "fma", Version)["Available"], Version >= (3, 13))
                self.assertEqual(_Registry._Math_Record("math", "sumprod", Version)["Available"], Version >= (3, 12))
                self.assertEqual(_Registry._Math_Record("math", "nextafter", Version)["Keyword_Arguments"], ("steps",) if Version >= (3, 12) else ())
        self.assertFalse(_Registry._Math_Record("numpy", "cumulative_sum", Numpy_Version="2.0.2")["Available"])
        self.assertTrue(_Registry._Math_Record("numpy", "cumulative_sum", Numpy_Version="2.1.0")["Available"])
        self.assertFalse(_Registry._Math_Record("numpy", "asin", Numpy_Version="1.26.4")["Available"])
        self.assertTrue(_Registry._Math_Record("numpy", "asin", Numpy_Version="2.0.0")["Available"])

    def test_Deterministic_Detached_Serializable_Records(self):
        First = _Registry._Math_Registry_Key((3, 14), (2, 1))
        Changed = _Registry._Math_Record("math", "sqrt")
        Changed["Domain"] = "Changed"
        self.assertNotEqual(Changed, _Registry._Math_Record("math", "sqrt"))
        self.assertEqual(First, _Registry._Math_Registry_Key((3, 14), (2, 1)))
        Records = json.loads(First)
        self.assertEqual([Item["Qualified_Name"] for Item in Records], sorted(Item["Qualified_Name"] for Item in Records))
        self.assertNotEqual(First, _Registry._Math_Registry_Key((3, 11), (2, 1)))

    def test_Algorithms_And_Return_Types_Are_Distinct(self):
        for Name in "gamma lgamma hypot log2".split():
            self.assertEqual(_Registry._Math_Record("math", Name)["Native_Availability"], "CPython_Algorithm_May_Differ_From_Libc")
        for Name in ("erf", "erfc"):
            Record = _Registry._Math_Record("math", Name)
            self.assertEqual(Record["Native_Availability"], "Runtime_Guarded_CPython_Libm_Erf")
            self.assertTrue(any("Py_GetVersion" in Requirement for Requirement in Record["Native_Requirements"]))
            self.assertIn("CPython 3.11", Record["Fallback_Reason"])
        for Name in "factorial comb perm gcd lcm isqrt".split():
            self.assertEqual(_Registry._Math_Record("math", Name)["Return_Type"], "Arbitrary_Precision_Int")
        self.assertEqual(_Registry._Math_Record("math", "gamma")["Native_Symbol"], "tgamma")
        self.assertEqual(_Registry._Math_Record("math", "frexp")["Return_Type"], "Tuple_Float_Int")
        self.assertEqual(_Registry._Math_Record("cmath", "polar")["Return_Type"], "Tuple_Float_Float")
        self.assertNotEqual(_Registry._Math_Record("math", "pow")["Inputs"], _Registry._Math_Record("builtins", "pow")["Inputs"])

    def test_Advertised_Unboxed_Registry_Matches_Generator(self):
        Spec = importlib.util.spec_from_file_location("_PyCeler_Fast_Math_Test", _Path.with_name("Fast_Math.py"))
        Fast = importlib.util.module_from_spec(Spec)
        Spec.loader.exec_module(Fast)
        self.assertEqual(_Registry._Guarded_Unboxed, frozenset(Fast._Fast_Call_Contracts))
        for Name in ("copysign", "fmod"):
            Record = _Registry._Math_Record("math", Name)
            self.assertEqual(Record["Required_Arguments"], 2)
            self.assertEqual(Record["Maximum_Arguments"], 2)
            self.assertEqual(Fast._Fast_Call_Contracts[Name]["Arity"], 2)
            self.assertEqual(Record["Native_Availability"], "Guarded_Binary_Libm_Path")
        self.assertIn("nonzero remainder", " ".join(_Registry._Math_Record("math", "fmod")["Native_Requirements"]))

    def test_All_Registered_Functions_Are_Recognized_From_Aliases(self):
        for Record in _Registry._Math_Registry((3, 14), (2, 5)):
            if Record["Kind"] != "Function":
                continue
            Module, Name = Record["Module"], Record["Name"]
            Arguments = ", ".join("Value" for _ in range(Record["Required_Arguments"]))
            Source = f"import {Module} as Library\nfrom {Module} import {Name} as Operation\ndef Compute(Value):\n    return Library.{Name}({Arguments}), Operation({Arguments})\n"
            Calls = _Registry._Math_Calls(Source, (3, 14), (2, 5))
            with self.subTest(Function=Record["Qualified_Name"]):
                self.assertEqual(len(Calls), 2)
                self.assertEqual([Call["Qualified_Name"] for Call in Calls], [Record["Qualified_Name"]] * 2)
                self.assertEqual([Call["Status"] for Call in Calls], ["Recognized"] * 2)
                self.assertEqual([Call["Binding"]["Path"] for Call in Calls], ["Library." + Name, "Operation"])

    def test_Argument_Binding_Matches_Math_Signatures(self):
        Valid = ("sqrt(4)", "log(4, 2)", "hypot()", "hypot(1, 2, 3)", "gcd()", "lcm()", "perm(3)", "perm(3, None)", "prod([1, 2], start=3)", "isclose(a=1, b=2, rel_tol=1)", "nextafter(1, 2, steps=3)")
        Invalid = ("sqrt()", "sqrt(1, 2)", "sqrt(x=1)", "log(x=4)", "log(4, base=2)", "perm(n=3)", "prod([1, 2], 3)", "isclose(1, 2, 0.1)", "isclose(1, a=2, b=3)", "nextafter(1, 2, 3)")
        for Form in Valid + Invalid:
            Calls = _Registry._Math_Calls("import math\nmath." + Form, (3, 14))
            with self.subTest(Form=Form):
                self.assertEqual(Calls[0]["Call_Form"], "Valid" if Form in Valid else "Invalid")
        self.assertEqual(_Registry._Math_Calls("import math\nmath.nextafter(1, 2, steps=3)", (3, 11))[0]["Status"], "Invalid_Call_Form")
        self.assertEqual(_Registry._Math_Calls("import math\nmath.fma(1, 2, 3)", (3, 11))[0]["Status"], "Unavailable")

    def test_Expanded_Arguments_And_Numpy_Forms_Are_Not_Proven(self):
        Source = "import math\nimport numpy as np\nmath.sin(*Values)\nmath.isclose(**Arguments)\nnp.sum(a=Values, axis=0)\nnp.add(Values, Values, out=Values, where=Mask)\n"
        Calls = _Registry._Math_Calls(Source)
        self.assertEqual([Call["Call_Form"] for Call in Calls], ["Dynamic", "Dynamic", "Runtime_Binding", "Runtime_Binding"])
        self.assertEqual(Calls[0]["Call_Form"], "Dynamic")
        self.assertTrue(Calls[0]["Contract"]["Native_Requirements"])
        self.assertTrue(all(not Call["Contract"]["Nogil_Eligible"] for Call in Calls[1:]))

    def test_Analysis_Never_Executes_Imports_Or_Target_Code(self):
        Source = "raise RuntimeError('executed')\nimport math\nimport definitely_missing_library\ndef Compute(Value):\n    return math.sqrt(Value)\n"
        Tree = ast.parse(Source)
        Before = ast.dump(Tree, include_attributes=True)
        Original_Import = __import__
        def Guarded_Import(Name, *Arguments, **Keywords):
            if Name in {"math", "definitely_missing_library"}:
                raise AssertionError("Target import attempted")
            return Original_Import(Name, *Arguments, **Keywords)
        with mock.patch("builtins.__import__", side_effect=Guarded_Import):
            Calls = _Registry._Math_Calls(Tree)
        self.assertEqual(Calls[0]["Qualified_Name"], "math.sqrt")
        self.assertEqual(Before, ast.dump(Tree, include_attributes=True))

    def test_Local_Imports_And_Simple_Aliases(self):
        Source = "import math\nRoot = math.sqrt\nLibrary = math\ndef Compute(Value):\n    from math import sin as Wave\n    Local = Wave\n    return Root(Value), Library.cos(Value), Local(Value)\n"
        Calls = _Registry._Math_Calls(Source)
        self.assertEqual([Call["Qualified_Name"] for Call in Calls], ["math.sqrt", "math.cos", "math.sin"])
        self.assertTrue(all(Call["Status"] == "Recognized" for Call in Calls))
        self.assertEqual(Calls[-1]["Binding"]["Scope"], "Compute")

    def test_Parameter_And_Late_Local_Assignment_Shadowing(self):
        Sources = (
            "import math\ndef Compute(math, Value):\n    return math.sqrt(Value)\n",
            "from math import sqrt\ndef Compute(Value):\n    Result = sqrt(Value)\n    sqrt = Value\n    return Result\n",
            "import math\ndef Compute(Value):\n    for math in Value:\n        math.sqrt(1)\n",
            "from math import sqrt\ndef Compute(Value):\n    try:\n        return sqrt(Value)\n    except Exception as sqrt:\n        return 1\n",
            "from math import sqrt\ndef Compute(Value):\n    match Value:\n        case {'op': sqrt}:\n            return sqrt(1)\n",
        )
        for Source in Sources:
            with self.subTest(Source=Source):
                Calls = _Registry._Math_Calls(Source)
                self.assertTrue(Calls)
                self.assertTrue(all(Call["Status"] == "Shadowed" for Call in Calls))

    def test_Module_Rebinding_And_Attribute_Changes_Are_Conservative(self):
        Sources = (
            "import math\ndef Compute(Value):\n    return math.sqrt(Value)\nmath = Replacement\n",
            "from math import sqrt\ndef Compute(Value):\n    return sqrt(Value)\ndef sqrt(Value):\n    return Value\n",
            "import math\nmath.sqrt = Replacement\ndef Compute(Value):\n    return math.sqrt(Value)\n",
            "import math\nif Flag:\n    math = Replacement\ndef Compute(Value):\n    return math.sqrt(Value)\n",
            "import math\ndef Change():\n    global math\n    math = Replacement\ndef Compute(Value):\n    return math.sqrt(Value)\n",
        )
        for Source in Sources:
            with self.subTest(Source=Source):
                self.assertEqual(_Registry._Math_Calls(Source)[0]["Status"], "Shadowed")

    def test_Comprehension_And_Lambda_Scopes(self):
        Source = "from math import sqrt\nA = [sqrt(1) for sqrt in Values]\nB = sqrt(4)\nC = lambda sqrt: sqrt(9)\nD = lambda Value=sqrt(16): sqrt(Value)\n"
        Calls = _Registry._Math_Calls(Source)
        self.assertEqual([Call["Status"] for Call in Calls], ["Shadowed", "Recognized", "Shadowed", "Recognized", "Recognized"])

    def test_Class_Bindings_Do_Not_Leak_Into_Methods(self):
        Source = "import math\nclass Example:\n    math = Replacement\n    A = math.sqrt(4)\n    def Compute(self, Value):\n        return math.sqrt(Value)\n"
        Calls = _Registry._Math_Calls(Source)
        self.assertEqual([Call["Status"] for Call in Calls], ["Shadowed", "Recognized"])
        self.assertEqual(Calls[-1]["Scope"], "Example.Compute")

    def test_Named_Expression_Updates_Subsequent_Lookups(self):
        Source = "import math\n(math := Replacement, math.sqrt(4))\n"
        self.assertEqual(_Registry._Math_Calls(Source)[0]["Status"], "Shadowed")

    def test_Unknown_Members_Constants_And_Unimported_Names(self):
        Source = "import math\nmath.future_api(1)\nmath.pi()\nMissing.sqrt(1)\n"
        Calls = _Registry._Math_Calls(Source)
        self.assertEqual([Call["Status"] for Call in Calls], ["Unknown_API", "Invalid_Call_Form"])
        self.assertEqual(_Registry._Math_Calls("math.sqrt(4)"), ())
        self.assertIsNone(_Registry._Math_Record("math", "future_api"))

    def test_Locations_Order_And_Binding_Guards(self):
        Source = "import math as M\ndef Compute(Value):\n    return M.sin(M.sqrt(Value)) + M.cos(Value)\n"
        Calls = _Registry._Math_Calls(Source)
        self.assertEqual([(Call["Line"], Call["Column"]) for Call in Calls], [(3, 11), (3, 17), (3, 34)])
        self.assertTrue(all("Concurrent_Binding_Mutation" in Call["Binding"]["Guards"] for Call in Calls))
        self.assertEqual(Calls, _Registry._Math_Calls(ast.parse(Source)))
        json.dumps(Calls, sort_keys=True)

    def test_Builtin_Zero_Argument_Conversions_And_Pow_Are_Distinct(self):
        Calls = _Registry._Math_Calls("import math\nint()\nfloat()\nbool()\ncomplex()\npow(base=2, exp=3, mod=5)\nmath.pow(2, 3)\n")
        self.assertEqual([Call["Status"] for Call in Calls], ["Recognized"] * 6)
        self.assertNotEqual(Calls[-1]["Qualified_Name"], Calls[-2]["Qualified_Name"])

    def test_Unsupported_Input_Is_Explicit(self):
        with self.assertRaises(TypeError):
            _Registry._Math_Calls(ast.parse("1").body[0])
        with self.assertRaises(SyntaxError):
            _Registry._Math_Calls("def broken(")

if __name__ == "__main__":
    unittest.main()
