import ast
import copy
import json
import sys

_Registry_Version = 3
_Modules = ("math", "cmath", "numpy", "builtins")
_Guarded_Unboxed = frozenset("sqrt cbrt sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh exp exp2 expm1 log log10 log1p fabs isfinite isinf isnan erf erfc copysign fmod".split())
_Real_Groups = {
    "Roots_Powers": "sqrt cbrt pow",
    "Exponential": "exp exp2 expm1",
    "Logarithmic": "log log2 log10 log1p",
    "Trigonometric": "sin cos tan asin acos atan atan2",
    "Hyperbolic": "sinh cosh tanh asinh acosh atanh",
    "Angle": "degrees radians",
    "Rounding": "ceil floor trunc fabs",
    "Remainder_Decomposition": "fmod remainder modf frexp ldexp",
    "Float_Manipulation": "copysign nextafter ulp",
    "Classification": "isfinite isinf isnan isclose",
    "Fused": "fma",
    "Accurate_Aggregation": "fsum prod sumprod hypot dist",
    "Exact_Integer": "factorial comb perm gcd lcm isqrt",
    "Special": "erf erfc gamma lgamma",
}
_Numpy_Groups = {
    "Arithmetic": "add subtract multiply divide true_divide floor_divide power pow float_power square reciprocal positive negative absolute fabs sign",
    "Roots_Exponential_Logarithmic": "sqrt cbrt exp exp2 expm1 log log2 log10 log1p logaddexp logaddexp2",
    "Trigonometric": "sin cos tan arcsin asin arccos acos arctan atan arctan2 atan2 hypot degrees radians deg2rad rad2deg unwrap",
    "Hyperbolic_Special": "sinh cosh tanh arcsinh asinh arccosh acosh arctanh atanh sinc i0",
    "Rounding_Remainder": "round around rint fix floor ceil trunc fmod mod remainder modf divmod",
    "Float_Manipulation": "copysign signbit frexp ldexp nextafter spacing isfinite isinf isnan isclose allclose",
    "Limits_Integer": "minimum maximum fmin fmax clip gcd lcm",
    "Reduction_Statistics": "sum prod min amin max amax mean var std nansum nanprod nanmin nanmax nanmean nanvar nanstd",
    "Ordered": "cumsum cumprod nancumsum nancumprod cumulative_sum cumulative_prod diff gradient",
    "Complex": "real imag angle conj conjugate",
}
_Numpy_High_Level = frozenset("unwrap sinc i0 round around fix isclose allclose clip sum prod min amin max amax mean var std nansum nanprod nanmin nanmax nanmean nanvar nanstd cumsum cumprod nancumsum nancumprod cumulative_sum cumulative_prod diff gradient real imag angle".split())
_Binary = frozenset("atan2 copysign fmod remainder pow ldexp comb dist sumprod".split())
_Numpy_Binary = frozenset("add subtract multiply divide true_divide floor_divide power pow float_power logaddexp logaddexp2 arctan2 atan2 hypot fmod mod remainder divmod copysign ldexp nextafter minimum maximum fmin fmax gcd lcm".split())
_Libc = frozenset("sqrt cbrt pow exp exp2 expm1 log log2 log10 log1p sin cos tan asin acos atan atan2 sinh cosh tanh asinh acosh atanh fabs fmod remainder copysign ldexp erf erfc gamma lgamma ceil floor trunc modf frexp nextafter fma hypot isfinite isinf isnan".split())
_Domain = {
    "sqrt": "Finite x >= 0; preserve negative-zero sign, NaN and positive infinity; negative inputs raise ValueError.",
    "cbrt": "All real values including negative values; preserve signed zero and special values.",
    "pow": "Two operands convert to float; negative finite bases require integral exponents; zero-to-negative, infinity and NaN cases follow Python math.pow.",
    "exp": "Finite inputs may overflow; positive infinity and negative infinity have distinct results.",
    "exp2": "Finite inputs may overflow; match CPython special-value and underflow behavior.",
    "expm1": "Preserve cancellation-sensitive near-zero behavior; finite positive inputs may overflow.",
    "log": "Positive real input and optional positive base != 1; huge positive Python integers need Python's logarithm conversion path.",
    "log2": "Positive real input; huge Python integers and CPython's base-two algorithm require a dedicated equivalence check.",
    "log10": "Positive real input; huge Python integers use Python's logarithm conversion path.",
    "log1p": "Finite x > -1; preserve accuracy near zero and signed zero; x <= -1 raises ValueError.",
    "sin": "Finite arguments or NaN; infinite arguments raise ValueError; preserve signed zero.",
    "cos": "Finite arguments or NaN; infinite arguments raise ValueError.",
    "tan": "Finite arguments or NaN; infinite arguments raise ValueError; preserve signed zero.",
    "asin": "Real x in [-1, 1] or NaN; preserve signed zero; other inputs raise ValueError.",
    "acos": "Real x in [-1, 1] or NaN; other inputs raise ValueError.",
    "atan": "All real values; preserve signed zero, infinities and NaN.",
    "atan2": "Two real arguments; signs of zeros, infinities and NaNs affect quadrants.",
    "sinh": "Finite inputs may overflow; preserve signed zero, infinities and NaN.",
    "cosh": "Finite inputs may overflow; preserve infinities and NaN.",
    "tanh": "All real values; preserve signed zero, infinities and NaN.",
    "asinh": "All real values; preserve signed zero, infinities and NaN.",
    "acosh": "Real x >= 1 or NaN; smaller inputs raise ValueError.",
    "atanh": "Real -1 < x < 1 or NaN; preserve signed zero; endpoints and outside values raise ValueError.",
    "degrees": "Use CPython's conversion constant and multiplication order; preserve special values.",
    "radians": "Use CPython's conversion constant and multiplication order; preserve special values.",
    "ceil": "Delegates to __ceil__ for non-floats; float NaN/infinity cannot produce an integer.",
    "floor": "Delegates to __floor__ for non-floats; float NaN/infinity cannot produce an integer.",
    "trunc": "Delegates to __trunc__; float NaN/infinity cannot produce an integer.",
    "fabs": "Convert to float and remove the sign, including negative zero.",
    "fmod": "Finite numerator and nonzero divisor, plus Python's special-value rules; preserve dividend sign.",
    "remainder": "IEEE nearest-integer quotient with ties to even; preserve dividend zero sign; invalid infinities/zero divisors raise ValueError.",
    "modf": "Return fractional and integral float parts with input sign, including special values.",
    "frexp": "Return float mantissa and integer exponent, preserving zero and special values.",
    "ldexp": "First argument converts to float; exponent uses Python's accepted integer contract and range handling; finite results can overflow.",
    "copysign": "Return float magnitude of x with sign bit of y, including zeros and NaNs.",
    "nextafter": "Move toward y by nonnegative integer steps; steps=0 and x==y preserve Python's special cases.",
    "ulp": "Preserve NaN, infinity, magnitude, zero/subnormal and maximum-finite special cases.",
    "isfinite": "Convert real input and test both infinities and NaN; huge integer conversion can overflow.",
    "isinf": "Convert real input and recognize either infinity; huge integer conversion can overflow.",
    "isnan": "Convert real input and recognize NaN; huge integer conversion can overflow.",
    "isclose": "Nonnegative tolerances; NaN is never close and infinities only match themselves.",
    "fma": "Single correctly rounded multiply-add; preserve Python's invalid-operation and overflow rules.",
    "fsum": "Consume the iterable in order and preserve CPython's compensated summation, special values and intermediate-overflow errors.",
    "prod": "Consume numeric iterable in order, preserve start object, integer exactness and multiplication behavior.",
    "sumprod": "Consume equal-length iterables; preserve extended precision for float products/sums and exact integer behavior.",
    "hypot": "Arbitrary count of real coordinates; preserve CPython's scaled high-accuracy norm and NaN/infinity precedence.",
    "dist": "Equal-length coordinate iterables; preserve consumption order and CPython's high-accuracy norm.",
    "factorial": "Nonnegative integer protocol input; arbitrary-precision integer result.",
    "comb": "Nonnegative integer n,k; exact result is zero for k>n.",
    "perm": "Nonnegative integer n and optional integer k or None; exact result is zero for k>n.",
    "gcd": "Zero or more integer protocol inputs; exact nonnegative result and gcd() == 0.",
    "lcm": "Zero or more integer protocol inputs; exact nonnegative result and lcm() == 1.",
    "isqrt": "Nonnegative integer protocol input; exact integer square root without floating conversion.",
    "erf": "Preserve CPython's error-function implementation, signed zero, infinities and NaN.",
    "erfc": "Preserve CPython's complementary-error-function implementation and tail accuracy.",
    "gamma": "Reject nonpositive integer poles and negative infinity; preserve CPython implementation, sign and overflow behavior.",
    "lgamma": "Reject nonpositive integer poles; preserve CPython implementation, infinities and overflow behavior.",
}

def _Base_Record(Module, Name, Category):
    return {"Registry_Version": _Registry_Version, "Module": Module, "Name": Name, "Qualified_Name": Module + "." + Name,
            "Kind": "Function", "Category": Category, "Minimum_Python": (3, 11), "Minimum_Numpy": None,
            "Required_Arguments": 1, "Maximum_Arguments": 1, "Parameter_Names": ("x",), "Keyword_Arguments": (), "Positional_Only": True,
            "Inputs": "Real numbers accepted by Python float conversion; custom conversion hooks retain Python execution.",
            "Conversions": "Preserve argument evaluation and conversion order; exact builtin/array scalar types require separate guards.",
            "Return_Type": "float", "Domain": _Domain.get(Name, "Preserve the original library's type, domain and special-value behavior."),
            "Precision": "Exact Python behavior on the active platform; no fast-math, reassociation or implicit fusion.",
            "Exceptions": ("TypeError", "ValueError", "OverflowError", "Exceptions_From_Conversion"),
            "Native_Symbol": None, "Native_Availability": "No_Unboxed_Lowering", "Nogil_Eligible": False, "Native_Implemented": False,
            "Ordered_Loop_Implemented": True, "Implementation_Strategies": ("Ordered_Original_Library_Calls",),
            "Implementation_Scope": "Qualifying numeric-array maps only; arbitrary call sites, objects and unsupported control flow retain Python.",
            "Native_Requirements": (), "Qualification": "Platform-specific native execution, differential comparisons and measured selection remain required.",
            "Status": "Ordered_Loop_Support", "Fallback_Reason": "Eligible array maps compile ordered iteration while preserving original calls; unsupported regions retain Python.",
            "Binding_Contract": "Resolve the same callable at the original execution point; revalidate after callbacks and guard concurrent mutation.",
            "Documentation": "https://docs.python.org/3.14/library/" + Module + ".html#" + Module + "." + Name}

def _Real_Record(Name, Category):
    Record = _Base_Record("math", Name, Category)
    if Name in _Binary:
        Record.update(Required_Arguments=2, Maximum_Arguments=2, Parameter_Names=("x", "y"))
    if Name == "atan2":
        Record["Parameter_Names"] = ("y", "x")
    if Name == "ldexp":
        Record["Parameter_Names"] = ("x", "i")
    if Name in {"log", "perm"}:
        Record.update(Maximum_Arguments=2, Parameter_Names=("x", "base") if Name == "log" else ("n", "k"))
    if Name in {"gcd", "lcm", "hypot"}:
        Record.update(Required_Arguments=0, Maximum_Arguments=None, Parameter_Names=())
    if Name == "fma":
        Record.update(Required_Arguments=3, Maximum_Arguments=3, Parameter_Names=("x", "y", "z"), Minimum_Python=(3, 13))
    if Name == "sumprod":
        Record["Minimum_Python"] = (3, 12)
    if Name in {"dist", "sumprod"}:
        Record["Parameter_Names"] = ("p", "q")
    if Name == "isclose":
        Record.update(Required_Arguments=2, Maximum_Arguments=2, Parameter_Names=("a", "b"), Keyword_Arguments=("a", "b", "rel_tol", "abs_tol"), Positional_Only=False)
    if Name == "nextafter":
        Record.update(Required_Arguments=2, Maximum_Arguments=2, Parameter_Names=("x", "y"), Keyword_Arguments=("steps",))
    if Name == "prod":
        Record.update(Parameter_Names=("iterable",), Keyword_Arguments=("start",), Return_Type="Numeric_Or_Start_Object")
    if Name == "fsum":
        Record["Parameter_Names"] = ("seq",)
    if Category == "Exact_Integer":
        Record.update(Inputs="Objects accepted by Python's integer index protocol; floats are not interchangeable.", Return_Type="Arbitrary_Precision_Int",
                      Fallback_Reason="Exact integer algorithms, argument validation and intermediate size must be preserved; fixed-width or floating substitutions are ineligible.")
        if Name in {"factorial", "isqrt"}:
            Record["Parameter_Names"] = ("n",)
        if Name == "comb":
            Record["Parameter_Names"] = ("n", "k")
    if Name in {"ceil", "floor", "trunc"}:
        Record.update(Return_Type="Int_Or_Protocol_Result", Fallback_Reason="Rounding protocols and arbitrary-size integer results require dedicated lowering.")
    if Name in {"isclose", "isfinite", "isinf", "isnan"}:
        Record["Return_Type"] = "bool"
    if Name == "modf":
        Record["Return_Type"] = "Tuple_Float_Float"
    if Name == "frexp":
        Record["Return_Type"] = "Tuple_Float_Int"
    if Category == "Accurate_Aggregation":
        Record["Fallback_Reason"] = "CPython's accuracy, arbitrary precision and iterable consumption need a dedicated algorithm; retain the existing native library call."
    if Name in _Libc:
        Record.update(Native_Symbol="tgamma" if Name == "gamma" else Name, Native_Availability="Platform_C_Library_Candidate_Requires_Qualification")
    if Name in {"log2", "erf", "erfc", "gamma", "lgamma", "hypot"}:
        Record["Native_Availability"] = "CPython_Algorithm_May_Differ_From_Libc"
    if Name in _Guarded_Unboxed:
        Record.update(Native_Availability="Guarded_Thin_Libm_Path", Native_Implemented=True, Nogil_Eligible=True, Status="Guarded_Unboxed_Region_Support",
                      Implementation_Strategies=("Ordered_Original_Library_Calls", "Guarded_Serial_Float64", "Guarded_OpenMP_Float64"),
                      Native_Requirements=("One-dimensional exact float64 arrays", "Contiguous aligned disjoint storage", "Validated finite inputs and every intermediate", "Original math callable identity", "Exclusive observer and floating-environment guards", "Ordered continuation before uncommitted effects"),
                      Fallback_Reason="Unproven values, changed bindings or observer conditions retain ordered original calls; unsupported whole regions retain Python.")
    if Name in {"erf", "erfc"}:
        Record.update(Native_Availability="Runtime_Guarded_CPython_Libm_Erf", Qualification="Staged implementation; native/platform qualification and representative measurements remain pending.",
                      Native_Requirements=Record["Native_Requirements"] + ("Runtime CPython 3.12-3.14 identified through stable-ABI Py_GetVersion",),
                      Fallback_Reason="CPython 3.11 and unknown runtime backends retain ordered original calls; mutable Python metadata and compiler headers do not establish runtime eligibility.")
    if Name in {"copysign", "fmod"}:
        Record.update(Native_Availability="Guarded_Binary_Libm_Path", Qualification="Staged binary-arity implementation; native/platform qualification and representative measurements remain pending.",
                      Native_Requirements=Record["Native_Requirements"] + ("Exactly two positional arguments evaluated left to right", "Finite binary operands without negative zero"))
    if Name == "fmod":
        Record.update(Native_Requirements=Record["Native_Requirements"] + ("Nonzero divisor and nonzero remainder",),
                      Fallback_Reason="Zero remainders retain original runtime-specific signed-zero repairs; invalid domains, nonfinite values and unproven inputs resume ordered original calls.")
    return Record

def _Complex_Record(Name):
    Record = _Base_Record("cmath", Name, "Complex")
    Record.update(Inputs="Complex, real and integer objects accepted by __complex__ or __float__ conversion.",
                  Return_Type="complex", Domain="Preserve function-specific complex branch cuts and signed-zero side selection, exceptional points and special values.",
                  Fallback_Reason="Complex branch cuts, conversions, two-component precision and exceptions require a dedicated qualified implementation.")
    if Name == "log":
        Record.update(Maximum_Arguments=2, Parameter_Names=("z", "base"))
    elif Name == "rect":
        Record.update(Required_Arguments=2, Maximum_Arguments=2, Parameter_Names=("r", "phi"), Inputs="Two real float-convertible values.")
    elif Name == "isclose":
        Record.update(Required_Arguments=2, Maximum_Arguments=2, Parameter_Names=("a", "b"), Keyword_Arguments=("a", "b", "rel_tol", "abs_tol"), Positional_Only=False)
    else:
        Record["Parameter_Names"] = ("z",)
    if Name in {"isclose", "isfinite", "isinf", "isnan"}:
        Record["Return_Type"] = "bool"
    if Name == "phase":
        Record["Return_Type"] = "float"
    if Name == "polar":
        Record["Return_Type"] = "Tuple_Float_Float"
    return Record

def _Numpy_Record(Name, Category):
    Record = _Base_Record("numpy", Name, Category)
    Ufunc = Name not in _Numpy_High_Level
    Inputs = 2 if Name in _Numpy_Binary else 1
    Outputs = 2 if Name in {"modf", "frexp", "divmod"} else 1
    Record.update(Required_Arguments=Inputs, Maximum_Arguments=Inputs + Outputs if Ufunc else None,
                  Parameter_Names=tuple("x" + str(Index + 1) for Index in range(Inputs)),
                  Keyword_Arguments=("out", "where", "casting", "order", "dtype", "subok", "signature", "extobj") if Ufunc else None,
                  Inputs="NumPy arrays/scalars and array-like objects; preserve dtype, promotion, broadcasting and dispatch protocols.",
                  Conversions="Preserve array conversion, __array_ufunc__/__array_function__, output casting and conversion warnings.",
                  Return_Type="Tuple_Array_Or_Scalar" if Outputs == 2 else "Array_Or_Scalar",
                  Domain="Preserve this operation's dtype-specific domains, axes, shape, output overlap, where masks and NumPy error settings.",
                  Precision="Preserve dtype-specific computation and NumPy's operation/reduction order; scalar math substitution is not equivalent.",
                  Exceptions=("TypeError", "ValueError", "FloatingPointError", "RuntimeWarning", "Exceptions_From_Array_Protocols"),
                  Native_Availability="Existing_Numpy_Implementation", Ufunc=Ufunc,
                  Fallback_Reason="Retain NumPy's existing implementation until dtype, broadcasting, warning, output and overlap semantics are qualified for a specific region.",
                  Documentation="https://numpy.org/doc/stable/reference/generated/numpy." + Name + ".html")
    if Category in {"Reduction_Statistics", "Ordered"}:
        Record["Fallback_Reason"] = "Retain NumPy's reduction/cumulative algorithm, dtype promotion, axis order, empty behavior and numerical accuracy."
    if Name in {"asin", "acos", "atan", "atan2", "asinh", "acosh", "atanh", "pow"}:
        Record["Minimum_Numpy"] = (2, 0)
    if Name in {"cumulative_sum", "cumulative_prod"}:
        Record["Minimum_Numpy"] = (2, 1)
    if Name in {"isclose", "allclose"}:
        Record["Required_Arguments"] = 2
    if Name == "clip":
        Record["Domain"] += " Preserve version-specific a_min/a_max and min/max keyword alternatives."
    if Name == "gradient":
        Record["Return_Type"] = "Array_Or_Sequence_Of_Arrays"
    if Name in {"isfinite", "isinf", "isnan", "isclose", "allclose", "signbit"}:
        Record["Return_Type"] = "Bool_Array_Or_Scalar"
    return Record

def _Builtin_Record(Name):
    Record = _Base_Record("builtins", Name, "Numeric_Builtin")
    Record.update(Maximum_Arguments=None, Parameter_Names=(), Keyword_Arguments=None, Positional_Only=False,
                  Inputs="Python objects subject to this builtin's numeric, ordering, iterator and conversion protocols.", Return_Type="Python_Protocol_Dependent",
                  Domain="Preserve overloaded operations, exact integers, iteration order, optional arguments and conversion hooks.",
                  Fallback_Reason="Numeric builtins have distinct contracts from math and NumPy and require type-specific guarded lowering.",
                  Documentation="https://docs.python.org/3.14/library/functions.html#" + Name)
    if Name in {"bool", "int", "float", "complex"}:
        Record["Required_Arguments"] = 0
    if Name in {"abs", "bool", "float"}:
        Record.update(Maximum_Arguments=1, Parameter_Names=("x",), Keyword_Arguments=(), Positional_Only=True)
    if Name == "divmod":
        Record.update(Required_Arguments=2, Maximum_Arguments=2, Parameter_Names=("x", "y"), Keyword_Arguments=(), Positional_Only=True)
    if Name == "round":
        Record.update(Maximum_Arguments=2, Parameter_Names=("number", "ndigits"), Keyword_Arguments=("number", "ndigits"))
    if Name == "pow":
        Record.update(Required_Arguments=2, Maximum_Arguments=3, Parameter_Names=("base", "exp", "mod"), Keyword_Arguments=("base", "exp", "mod"))
    if Name == "sum":
        Record.update(Maximum_Arguments=2, Parameter_Names=("iterable", "start"), Keyword_Arguments=("start",), Positional_Only=True)
    if Name in {"min", "max"}:
        Record["Keyword_Arguments"] = ("key", "default")
    return Record

def _Create_Registry():
    Records = {}
    for Category, Names in _Real_Groups.items():
        for Name in Names.split():
            Records[("math", Name)] = _Real_Record(Name, Category)
    for Name in "sqrt exp log log10 sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh phase polar rect isfinite isinf isnan isclose".split():
        Records[("cmath", Name)] = _Complex_Record(Name)
    for Category, Names in _Numpy_Groups.items():
        for Name in Names.split():
            Records[("numpy", Name)] = _Numpy_Record(Name, Category)
    for Name in "abs round pow divmod sum min max int float complex bool".split():
        Records[("builtins", Name)] = _Builtin_Record(Name)
    for Module, Names in (("math", "pi e tau inf nan"), ("cmath", "pi e tau inf infj nan nanj")):
        for Name in Names.split():
            Record = _Base_Record(Module, Name, "Constant")
            Record.update(Kind="Constant", Required_Arguments=0, Maximum_Arguments=0, Parameter_Names=(), Inputs="No arguments.",
                          Return_Type="complex" if Name.endswith("j") else "float", Domain="Preserve the current binding and observable object identity.",
                          Fallback_Reason="Constant propagation must preserve mutable bindings and observable identity.",
                          Ordered_Loop_Implemented=False, Implementation_Strategies=(), Status="Python_Retained")
            Records[(Module, Name)] = Record
    return Records

_Records = _Create_Registry()

def _Version(Value, Default):
    if Value is None:
        return Default
    Parts = Value.split(".") if isinstance(Value, str) else Value
    return tuple(int(Part) for Part in Parts[:2])

def _Math_Record(Module, Name, Python_Version=None, Numpy_Version=None):
    Original = _Records.get((Module, Name))
    if Original is None:
        return None
    Record = copy.deepcopy(Original)
    Version = _Version(Python_Version, tuple(sys.version_info[:2]))
    Numpy = _Version(Numpy_Version, None)
    Record["Available"] = Version >= Record["Minimum_Python"]
    if Module == "numpy":
        Record["Available"] = None if Numpy is None else Record["Minimum_Numpy"] is None or Numpy >= Record["Minimum_Numpy"]
    if Module == "math" and Name == "nextafter" and Version < (3, 12):
        Record["Keyword_Arguments"] = ()
        Record["Domain"] = "One representable step toward y; steps is unavailable before Python 3.12."
    if Record["Available"] is False:
        Record.update(Status="Unavailable", Fallback_Reason="This API is unavailable on the requested interpreter/library version; preserve Python's lookup failure.",
                      Ordered_Loop_Implemented=False, Native_Implemented=False, Nogil_Eligible=False, Implementation_Strategies=())
    return Record

def _Math_Registry(Python_Version=None, Numpy_Version=None):
    return tuple(_Math_Record(Module, Name, Python_Version, Numpy_Version) for Module, Name in sorted(_Records))

def _Math_Registry_Key(Python_Version=None, Numpy_Version=None):
    return json.dumps(_Math_Registry(Python_Version, Numpy_Version), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def _Call_Form(Node, Record):
    if Record["Kind"] != "Function":
        return "Invalid", "The resolved library member is a constant, not a callable."
    if any(isinstance(Argument, ast.Starred) for Argument in Node.args) or any(Keyword.arg is None for Keyword in Node.keywords):
        return "Dynamic", "Expanded arguments require runtime binding and ordered iterator consumption."
    if Record["Module"] == "numpy" and not Record["Ufunc"]:
        return "Runtime_Binding", "Preserve version-specific high-level NumPy argument binding and array protocols."
    Count = len(Node.args)
    Maximum = Record["Maximum_Arguments"]
    Keywords = [Keyword.arg for Keyword in Node.keywords]
    Allowed = Record["Keyword_Arguments"]
    Parameters = Record["Parameter_Names"]
    if Maximum is not None and Count > Maximum:
        return "Invalid", "The call supplies too many positional arguments for the resolved API."
    if Allowed is not None and any(Name not in Allowed for Name in Keywords):
        return "Invalid", "The call uses a keyword unavailable in this API/version or for a positional-only parameter."
    if len(Keywords) != len(set(Keywords)) or any(Name in Parameters[:Count] for Name in Keywords):
        return "Invalid", "The call supplies an argument more than once."
    Bound = Count + sum(Name in Parameters[:Record["Required_Arguments"]] for Name in Keywords)
    if Bound < Record["Required_Arguments"]:
        return "Invalid", "The call omits a required argument."
    if Record["Module"] in {"numpy", "builtins"}:
        return "Runtime_Binding", "Preserve library-specific optional argument binding and protocols."
    return "Valid", "The static argument form matches this API/version; values and conversions still require validation."

def _Binding(Module, Name, Path, Scope, Status="Imported", Reason=""):
    return {"Module": Module, "Name": Name, "Path": Path, "Scope": Scope, "Status": Status, "Reason": Reason,
            "Kind": "Module" if Name is None else "Member", "Guards": ("Callable_Identity_At_Original_Point", "Revalidate_After_Effects", "Concurrent_Binding_Mutation")}

def _Resolve(Node, Bindings):
    if isinstance(Node, ast.Name):
        return Bindings.get(Node.id)
    if isinstance(Node, ast.Attribute) and isinstance(Node.value, ast.Name):
        Base = Bindings.get(Node.value.id)
        if Base is not None and Base["Kind"] == "Module":
            return _Binding(Base["Module"], Node.attr, Node.value.id + "." + Node.attr, Base["Scope"], Base["Status"], Base["Reason"])
    return None

def _Target_Names(Node):
    if isinstance(Node, ast.Name):
        return {Node.id}
    if isinstance(Node, (ast.Tuple, ast.List)):
        return set().union(*(_Target_Names(Item) for Item in Node.elts))
    if isinstance(Node, ast.Starred):
        return _Target_Names(Node.value)
    return set()

def _Local_Changes(Node):
    Changes = set()
    Globals = set()
    Stack = list(ast.iter_child_nodes(Node))
    while Stack:
        Current = Stack.pop()
        if isinstance(Current, (ast.Global, ast.Nonlocal)):
            Globals.update(Current.names)
        elif isinstance(Current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            Changes.add(Current.name)
        elif isinstance(Current, ast.Lambda):
            continue
        elif isinstance(Current, ast.Name) and isinstance(Current.ctx, (ast.Store, ast.Del)):
            Changes.add(Current.id)
        elif isinstance(Current, ast.Import):
            Changes.update(Alias.asname or Alias.name.split(".")[0] for Alias in Current.names)
        elif isinstance(Current, ast.ImportFrom):
            Changes.update(Alias.asname or Alias.name for Alias in Current.names if Alias.name != "*")
        elif isinstance(Current, ast.ExceptHandler) and Current.name:
            Changes.add(Current.name)
            Stack.extend(ast.iter_child_nodes(Current))
        elif isinstance(Current, (ast.MatchAs, ast.MatchStar)):
            if Current.name:
                Changes.add(Current.name)
            Stack.extend(ast.iter_child_nodes(Current))
        elif isinstance(Current, ast.MatchMapping):
            if Current.rest:
                Changes.add(Current.rest)
            Stack.extend(ast.iter_child_nodes(Current))
        elif isinstance(Current, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            Stack.extend(Part for Part in ast.walk(Current) if isinstance(Part, ast.NamedExpr))
        else:
            Stack.extend(ast.iter_child_nodes(Current))
    return Changes - Globals, Globals

def _Invalidate(Bindings, Names, Reason):
    for Name in Names:
        Previous = Bindings.get(Name)
        if Previous is not None:
            Bindings[Name] = dict(Previous, Status="Shadowed", Reason=Reason)
        else:
            Bindings[Name] = None

def _Import_Bindings(Node, Bindings, Scope):
    if isinstance(Node, ast.Import):
        for Alias in Node.names:
            Name = Alias.asname or Alias.name.split(".")[0]
            if Alias.name in _Modules:
                Bindings[Name] = _Binding(Alias.name, None, Name, Scope)
            else:
                _Invalidate(Bindings, (Name,), "A different import replaces the name.")
    elif Node.level == 0 and Node.module in _Modules:
        for Alias in Node.names:
            if Alias.name == "*":
                _Invalidate(Bindings, tuple(Bindings), "Wildcard imports do not establish stable explicit bindings.")
            else:
                Name = Alias.asname or Alias.name
                Bindings[Name] = _Binding(Node.module, Alias.name, Name, Scope)
    else:
        _Invalidate(Bindings, tuple(Bindings) if any(Alias.name == "*" for Alias in Node.names) else (Alias.asname or Alias.name for Alias in Node.names), "An unrelated or relative import may replace the binding.")

class _Math_Inspector:
    def __init__(self, Tree, Python_Version, Numpy_Version):
        self._Tree = Tree
        self._Python_Version = Python_Version
        self._Numpy_Version = Numpy_Version
        self._Calls = []
        self._Globals = {Name: _Binding("builtins", Name, Name, "Builtins") for Module, Name in _Records if Module == "builtins"}
        self._Global_Mutations = set()

    def _Prepare(self):
        for Node in self._Tree.body:
            self._Update(Node, self._Globals, "Module", False)
        for Node in ast.walk(self._Tree):
            if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _, Globals = _Local_Changes(Node)
                self._Global_Mutations.update(Globals)
        _Invalidate(self._Globals, self._Global_Mutations, "A global/nonlocal declaration can expose mutation of this binding.")

    def _Update(self, Node, Bindings, Scope, Conditional):
        if isinstance(Node, (ast.Import, ast.ImportFrom)):
            _Import_Bindings(Node, Bindings, Scope)
        elif isinstance(Node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            Targets = Node.targets if isinstance(Node, ast.Assign) else (Node.target,)
            Resolved = _Resolve(Node.value, Bindings) if Node.value is not None else None
            for Target in Targets:
                Names = _Target_Names(Target)
                if isinstance(Target, ast.Name) and Resolved is not None and not Conditional:
                    Bindings[Target.id] = dict(Resolved, Path=Target.id, Scope=Scope)
                else:
                    _Invalidate(Bindings, Names, "Assignment replaces or conditionally defines the imported binding.")
                if isinstance(Target, ast.Attribute) and isinstance(Target.value, ast.Name):
                    Base = Bindings.get(Target.value.id)
                    if Base is not None:
                        _Invalidate(Bindings, (Name for Name, Value in Bindings.items() if Value and Value["Module"] == Base["Module"]), "An attribute write can replace a mathematical callable.")
        elif isinstance(Node, (ast.AugAssign, ast.Delete)):
            Targets = Node.targets if isinstance(Node, ast.Delete) else (Node.target,)
            for Target in Targets:
                _Invalidate(Bindings, _Target_Names(Target), "Assignment or deletion changes this name.")
                if isinstance(Target, ast.Attribute) and isinstance(Target.value, ast.Name):
                    _Invalidate(Bindings, (Target.value.id,), "Attribute mutation changes the library binding.")
        elif isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _Invalidate(Bindings, (Node.name,), "A function or class definition replaces this name.")
        elif isinstance(Node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, getattr(ast, "TryStar", ast.Try), ast.With, ast.AsyncWith, ast.Match)):
            Changes, _ = _Local_Changes(Node)
            _Invalidate(Bindings, Changes, "Control flow may replace or conditionally define this binding.")

    def _Record(self, Node, Bindings, Scope):
        Resolved = _Resolve(Node.func, Bindings)
        if Resolved is None or Resolved["Name"] is None:
            return
        Contract = _Math_Record(Resolved["Module"], Resolved["Name"], self._Python_Version, self._Numpy_Version)
        if Contract is None:
            Contract = _Base_Record(Resolved["Module"], Resolved["Name"], "Unknown_API")
            Contract.update(Kind="Unknown", Available=None, Ordered_Loop_Implemented=False, Implementation_Strategies=(), Status="Python_Retained",
                            Fallback_Reason="This library member has no registered contract; preserve dynamic lookup and Python execution.")
            Form, Explanation = "Unknown", "No registered signature is available for this library member."
        else:
            Form, Explanation = _Call_Form(Node, Contract)
        Status = "Recognized" if Resolved["Status"] == "Imported" else "Shadowed"
        if Contract["Kind"] == "Unknown" and Status == "Recognized":
            Status = "Unknown_API"
        elif Contract["Available"] is False:
            Status = "Unavailable"
        elif Form == "Invalid":
            Status = "Invalid_Call_Form" if Status == "Recognized" else Status
        Reason = Resolved["Reason"] or (Contract["Fallback_Reason"] if Status in {"Recognized", "Unavailable"} else Explanation)
        self._Calls.append({"Registry_Version": _Registry_Version, "Module": Contract["Module"], "Name": Contract["Name"],
                            "Qualified_Name": Contract["Qualified_Name"], "Line": Node.lineno, "Column": Node.col_offset,
                            "End_Line": Node.end_lineno, "End_Column": Node.end_col_offset, "Scope": Scope,
                            "Binding": dict(Resolved), "Status": Status, "Reason": Reason,
                            "Call_Form": Form, "Call_Form_Reason": Explanation, "Contract": Contract})

    def _Function(self, Node, Bindings, Scope):
        for Value in Node.decorator_list + Node.args.defaults + [Value for Value in Node.args.kw_defaults if Value is not None]:
            self._Walk(Value, Bindings, Scope)
        Inner = dict(Bindings)
        Changes, Globals = _Local_Changes(Node)
        _Invalidate(Inner, Changes, "A function-local binding shadows the outer name, including before its assignment.")
        Arguments = Node.args.posonlyargs + Node.args.args + Node.args.kwonlyargs
        Arguments += ([Node.args.vararg] if Node.args.vararg else []) + ([Node.args.kwarg] if Node.args.kwarg else [])
        _Invalidate(Inner, (Argument.arg for Argument in Arguments), "A parameter shadows the imported name.")
        _Invalidate(Inner, Globals, "Global/nonlocal state is a mutable boundary.")
        Name = Node.name if Scope == "Module" else Scope + "." + Node.name
        for Statement in Node.body:
            self._Walk(Statement, Inner, Name)
            self._Update(Statement, Inner, Name, False)

    def _Walk(self, Node, Bindings, Scope):
        if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._Function(Node, Bindings, Scope)
            return
        if isinstance(Node, ast.ClassDef):
            for Value in Node.bases + Node.decorator_list + [Keyword.value for Keyword in Node.keywords]:
                self._Walk(Value, Bindings, Scope)
            Inner = dict(Bindings)
            Name = Node.name if Scope == "Module" else Scope + "." + Node.name
            for Statement in Node.body:
                self._Walk(Statement, Bindings if isinstance(Statement, (ast.FunctionDef, ast.AsyncFunctionDef)) else Inner, Name)
                self._Update(Statement, Inner, Name, False)
            return
        if isinstance(Node, ast.Lambda):
            for Value in Node.args.defaults + [Value for Value in Node.args.kw_defaults if Value is not None]:
                self._Walk(Value, Bindings, Scope)
            Inner = dict(Bindings)
            Arguments = Node.args.posonlyargs + Node.args.args + Node.args.kwonlyargs
            Arguments += ([Node.args.vararg] if Node.args.vararg else []) + ([Node.args.kwarg] if Node.args.kwarg else [])
            _Invalidate(Inner, (Argument.arg for Argument in Arguments), "A lambda parameter shadows this name.")
            self._Walk(Node.body, Inner, Scope + ".<lambda>")
            return
        if isinstance(Node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            Inner = dict(Bindings)
            for Generator in Node.generators:
                self._Walk(Generator.iter, Inner, Scope)
                _Invalidate(Inner, _Target_Names(Generator.target), "A comprehension target shadows this name.")
                for Condition in Generator.ifs:
                    self._Walk(Condition, Inner, Scope)
            for Value in (Node.key, Node.value) if isinstance(Node, ast.DictComp) else (Node.elt,):
                self._Walk(Value, Inner, Scope)
            return
        if isinstance(Node, ast.Call):
            self._Record(Node, Bindings, Scope)
        if isinstance(Node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, getattr(ast, "TryStar", ast.Try), ast.With, ast.AsyncWith, ast.Match)):
            Inner = dict(Bindings)
            Changes, _ = _Local_Changes(Node)
            _Invalidate(Inner, Changes, "A conditional, loop, handler or context can replace this binding.")
            for Child in ast.iter_child_nodes(Node):
                self._Walk(Child, Inner, Scope)
            return
        for Child in ast.iter_child_nodes(Node):
            self._Walk(Child, Bindings, Scope)
        if isinstance(Node, ast.NamedExpr):
            self._Update(Node, Bindings, Scope, False)

    def _Inspect(self):
        self._Prepare()
        Module = {Name: _Binding("builtins", Name, Name, "Builtins") for Package, Name in _Records if Package == "builtins"}
        for Node in self._Tree.body:
            self._Walk(Node, self._Globals if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else Module, "Module")
            self._Update(Node, Module, "Module", False)
        return tuple(sorted(self._Calls, key=lambda Record: (Record["Line"], Record["Column"], Record["Qualified_Name"])))

def _Math_Calls(Source, Python_Version=None, Numpy_Version=None):
    Tree = ast.parse(Source) if isinstance(Source, (str, bytes)) else Source
    if not isinstance(Tree, ast.Module):
        raise TypeError("Math analysis requires Python source text or an ast.Module.")
    return _Math_Inspector(Tree, Python_Version, Numpy_Version)._Inspect()
