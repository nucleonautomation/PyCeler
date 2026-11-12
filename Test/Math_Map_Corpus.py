import math
import numpy as Numpy

def _Math_Map_Corpus():
    Definitions = ["import math\nimport cmath\nimport numpy as np\nfrom math import sin as Wave\nLiteral_Finite = 1.25\nLiteral_Zero = -0.0\nLiteral_Infinite = 1e10000\nLiteral_Tuple = (1.25, -0.0)\n"]
    Recipes = []
    Real = "acos acosh asin asinh atan atan2 atanh cbrt ceil comb copysign cos cosh degrees dist erf erfc exp exp2 expm1 fabs factorial floor fmod frexp fsum gamma gcd hypot isclose isfinite isinf isnan isqrt lcm ldexp lgamma log log10 log1p log2 modf nextafter perm pow prod radians remainder sin sinh sqrt tan tanh trunc ulp".split()
    Real += [Name for Name in ("fma", "sumprod") if hasattr(math, Name)]
    Integer = set("comb factorial gcd isqrt lcm perm ldexp".split())
    Boolean = set("isclose isfinite isinf isnan".split())
    Unary_Tuple = {"frexp", "modf"}
    Binary = set("atan2 copysign fmod remainder pow comb".split())
    Arguments = {"dist": "(Source[Index], 1.0), (0.0, 2.0)", "fsum": "[Source[Index], 1.0, -1.0]",
                 "hypot": "Source[Index], 1.0, 2.0", "prod": "[Source[Index], 2]", "sumprod": "[Source[Index], 1.0], [2.0, 3.0]",
                 "gcd": "Source[Index], 6", "lcm": "Source[Index], 6", "perm": "Source[Index], 1", "comb": "Source[Index], 1",
                 "ldexp": "0.5, Source[Index]", "isclose": "Source[Index], Source[Index], abs_tol=0.0", "fma": "Source[Index], 2.0, 1.0",
                 "nextafter": "Source[Index], math.inf"}
    for Name in Real:
        Call = "math." + Name + "(" + Arguments.get(Name, "Source[Index], 2.0" if Name in Binary else "Source[Index]") + ")"
        if Name in Unary_Tuple:
            Call += "[0]"
        Function = "Real_" + Name
        Definitions.append(f"def {Function}(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = {Call}\n    return Output\n")
        Recipes.append(dict(Function=Function, Input="int64" if Name in Integer else "float64", Output="bool" if Name in Boolean else "float64", Domain="acosh" if Name == "acosh" else "integer" if Name in Integer else "real"))
    for Name in "acos acosh asin asinh atan atanh cos cosh exp isclose isfinite isinf isnan log log10 phase polar rect sin sinh sqrt tan tanh".split():
        Arguments = "Source[Index], 0.5" if Name == "rect" else "Source[Index], Source[Index]" if Name == "isclose" else "Source[Index]"
        Call = "cmath." + Name + "(" + Arguments + ")" + ("[0]" if Name == "polar" else "")
        Function = "Complex_" + Name
        Definitions.append(f"def {Function}(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = {Call}\n    return Output\n")
        Recipes.append(dict(Function=Function, Input="float64" if Name == "rect" else "complex128", Output="bool" if Name in Boolean else "float64" if Name in {"phase", "polar"} else "complex128", Domain="complex"))
    Numpy_Names = "add subtract multiply divide true_divide floor_divide power float_power square reciprocal positive negative absolute fabs sign sqrt cbrt exp exp2 expm1 log log2 log10 log1p logaddexp logaddexp2 sin cos tan arcsin arccos arctan arctan2 hypot degrees radians deg2rad rad2deg unwrap sinh cosh tanh arcsinh arccosh arctanh sinc i0 round around rint fix floor ceil trunc fmod mod remainder modf divmod copysign signbit frexp ldexp nextafter spacing isfinite isinf isnan isclose allclose minimum maximum fmin fmax clip gcd lcm sum prod min max mean var std nansum nanprod nanmin nanmax nanmean nanvar nanstd cumsum cumprod nancumsum nancumprod diff gradient real imag angle conj conjugate".split()
    Numpy_Names += [Name for Name in "asin acos atan atan2 asinh acosh atanh pow amin amax cumulative_sum cumulative_prod".split() if hasattr(Numpy, Name)]
    Binary = set("add subtract multiply divide true_divide floor_divide power pow float_power logaddexp logaddexp2 arctan2 atan2 hypot fmod mod remainder divmod copysign nextafter minimum maximum fmin fmax isclose allclose".split())
    Reduction = set("sum prod min amin max amax mean var std nansum nanprod nanmin nanmax nanmean nanvar nanstd".split())
    Cumulative = set("cumsum cumprod nancumsum nancumprod cumulative_sum cumulative_prod unwrap gradient diff".split())
    for Name in Numpy_Names:
        Arguments = "Source[Index], 2.0" if Name in Binary else "Source[Index]"
        if Name in Reduction | Cumulative:
            Arguments = "[Source[Index], 1.0, 2.0]"
        if Name == "clip":
            Arguments = "Source[Index], 0.0, 1.0"
        if Name == "ldexp":
            Arguments = "0.5, Source[Index]"
        if Name in {"gcd", "lcm"}:
            Arguments = "Source[Index], 6"
        Call = "np." + Name + "(" + Arguments + ")" + ("[0]" if Name in Cumulative | {"frexp", "modf", "divmod"} else "")
        Function = "Numpy_" + Name
        Definitions.append(f"def {Function}(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = {Call}\n    return Output\n")
        Recipes.append(dict(Function=Function, Input="int64" if Name in {"gcd", "lcm", "ldexp"} else "float64", Output="bool" if Name in Boolean | {"allclose", "signbit"} else "float64", Domain="integer" if Name in {"gcd", "lcm", "ldexp"} else "acosh" if Name in {"arccosh", "acosh"} else "real"))
    for Name in "abs round pow divmod sum min max int float complex bool".split():
        Arguments = "[Source[Index], 1.0]" if Name in {"sum", "min", "max"} else "Source[Index], 2" if Name in {"round", "pow", "divmod"} else "Source[Index]"
        Call = Name + "(" + Arguments + ")" + ("[0]" if Name == "divmod" else "")
        Function = "Builtin_" + Name
        Definitions.append(f"def {Function}(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = {Call}\n    return Output\n")
        Recipes.append(dict(Function=Function, Input="float64", Output="bool" if Name == "bool" else "complex128" if Name == "complex" else "float64", Domain="real"))
    Definitions.extend([
        "def Composite(Source, Output):\n    for Index in range(len(Output)):\n        Value = math.sqrt(Source[Index])\n        Value += Wave(Value)\n        Output[Index] = math.exp(Value) + math.log(Source[Index], 2) + math.cos(math.pi)\n    return Output\n",
        "def Nested(Source, Output):\n    for Row in range(Output.shape[0]):\n        for Column in range(Output.shape[1]):\n            if Source[Row, Column] < 0:\n                continue\n            Output[Row, Column] = math.sqrt(Source[Row, Column])\n    return Output\n",
        "def Float32_Intermediates(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.sin(Source[Index]) + math.cos(Source[Index])\n    return Output\n",
        "def Fraction(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.frexp(Source[Index])[1]\n    return Output\n",
        "def Literal_Identity(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.copysign(Source[Index], -0.0)\n    return Output\n",
        "def Infinite_Literal(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.copysign(Source[Index], 1e10000)\n    return Output\n",
        "def Collision(Baseline, Allow_Threads):\n    for _Pyceler_Math_B in range(len(Allow_Threads)):\n        Allow_Threads[_Pyceler_Math_B] = math.sqrt(Baseline[_Pyceler_Math_B])\n    return Allow_Threads\n",
        "def Identity_Finite(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.copysign(Source[Index], 1.25)\n    return Output\n",
        "def Identity_Zero(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.copysign(Source[Index], -0.0)\n    return Output\n",
        "def Identity_Infinite(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.copysign(Source[Index], 1e10000)\n    return Output\n",
        "def Identity_Tuple(Source, Output):\n    for Index in range(len(Output)):\n        Output[Index] = math.prod((1.25, -0.0), start=Source[Index])\n    return Output\n",
    ])
    return "\n".join(Definitions), Recipes
