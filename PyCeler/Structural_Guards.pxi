cdef list _Structural_Interval_Code(dict Plan, str Name):
    Arrays = sorted(Plan["Names"].index(Value) for Value in Plan["Arrays"] if Value in Plan["Names"])
    Parameters = [*(f"object V{Index}" for Index in range(len(Plan["Names"]))), "object Minimum", "object Maximum"]
    Parameters.extend(f"object {Side}{Slot}" for Slot in Arrays for Side in ("Low", "High"))
    Parameters.append("bint Floating=False")
    Lines = [f"cdef bint {Name}_Ranges({', '.join(Parameters)}):", "    import builtins as B"]
    Bounds = {(Slot, 0): (f"Low{Slot}", f"High{Slot}") for Slot in Arrays}
    Integers = set()
    for Axes, Actions in Plan["Blocks"]:
        for Action in Actions:
            if Action[0] == "write":
                Bounds[(Action[1], Action[3])] = (f"L{Action[2]}", f"H{Action[2]}")
                continue
            Number = Action[1]
            Recipe = Plan["Nodes"][Number]
            Kind = Recipe[0]
            Integral = Kind in ("scalar", "literal") or Kind in ("+", "-", "*") and Recipe[1] in Integers and Recipe[2] in Integers
            if Integral:
                Integers.add(Number)
            if Kind == "array":
                Low, High = Bounds[(Recipe[1], Recipe[2])]
            elif Kind in ("scalar", "literal"):
                Low = High = f"V{Recipe[1]}" if Kind == "scalar" else str(Recipe[1])
            elif Kind == "abs":
                Left = Recipe[1]
                Low = f"(0 if L{Left} <= 0 <= H{Left} else B.min(B.abs(L{Left}), B.abs(H{Left})))"
                High = f"B.max(B.abs(L{Left}), B.abs(H{Left}))"
            else:
                Left, Right = Recipe[1:]
                if Kind == "+":
                    Low, High = f"L{Left} + L{Right}", f"H{Left} + H{Right}"
                elif Kind == "-":
                    Low, High = f"L{Left} - H{Right}", f"H{Left} - L{Right}"
                else:
                    Products = ", ".join(f"{A}{Left} * {B}{Right}" for A in ("L", "H") for B in ("L", "H"))
                    Low, High = f"B.min({Products})", f"B.max({Products})"
            Lines.extend([f"    L{Number} = {Low}", f"    H{Number} = {High}",
                          f"    if L{Number} < Minimum or H{Number} > Maximum:", "        return False"])
            if Integral and Kind in ("+", "-", "*"):
                Lines.extend([f"    if Floating and L{Number} == 0:", "        return False"])
    return [*Lines, "    return True", ""]

cdef list _Structural_Guard_Code(dict Plan, str Name):
    Names = Plan["Names"]
    Arrays = sorted(Names.index(Value) for Value in Plan["Arrays"] if Value in Names)
    Scalars = sorted(Names.index(Value) for Value in Plan["Scalars"])
    Outputs = sorted(Names.index(Value) for Value in Plan["Outputs"] if Value in Names)
    Destination = Names.index(Plan["Output"])
    Arguments = ", ".join(f"V{Index}" for Index in range(len(Names)))
    Parameters = ", ".join(f"object V{Index}" for Index in range(len(Names)))
    Lines = _Structural_Interval_Code(Plan, Name)
    Lines.extend([f"cdef bint {Name}_Allowed({Parameters}, object Baseline):", "    import builtins as B", "    import sys as S",
                  "    N = S.modules.get('numpy')", f"    Output = V{Destination}",
                  f"    if not _Pyceler_Bindings(Baseline) or not _Pyceler_Array(Output, N, {Plan['Dimensions']}, True):", "        return False"])
    if Plan["Abs"]:
        Lines.extend(["    Absolute = Baseline.__globals__.get('abs', Baseline.__builtins__.get('abs'))",
                      "    if not _Pyceler_Is_C_Function(Absolute) or Absolute.__self__ is not B or Absolute.__name__ != 'abs':", "        return False"])
    for Slot in Arrays:
        if Slot != Destination:
            Lines.extend([f"    if not _Pyceler_Array(V{Slot}, N, {Plan['Dimensions']}, True) or V{Slot}.dtype != Output.dtype or V{Slot}.shape != Output.shape:", "        return False"])
        if Slot in Outputs:
            Lines.extend([f"    if not V{Slot}.flags.writeable:", "        return False"])
    Pairs = set()
    for Slot in Outputs:
        for Other in Arrays:
            Pair = tuple(sorted((Slot, Other)))
            if Slot != Other and Pair not in Pairs:
                Pairs.add(Pair)
                Lines.extend([f"    if N.may_share_memory(V{Slot}, V{Other}):", "        return False"])
    for Value, Axis in Plan["Dimension_Args"].items():
        Slot = Names.index(Value)
        Lines.extend([f"    if B.type(V{Slot}) is not B.int or V{Slot} != Output.shape[{Axis}]:", "        return False"])
    if Plan["Allocation"] is not None:
        Alias = Plan["Allocation"][0]
        Lines.extend([f"    Module = Baseline.__globals__.get({Alias!r})",
                      "    Core = S.modules.get('numpy._core.multiarray') or S.modules.get('numpy.core.multiarray')",
                      "    if Module is not N or Core is None or N.empty_like is not Core.empty_like:", "        return False",
                      "    Native_Module = S.modules.get('numpy._core._multiarray_umath') or S.modules.get('numpy.core._multiarray_umath')",
                      "    Dispatcher = B.getattr(Native_Module, '_ArrayFunctionDispatcher', None)",
                      "    if Dispatcher is None or B.type(N.empty_like) is not Dispatcher:", "        return False",
                      "    Implementation = B.getattr(N.empty_like, '_implementation', None)",
                      "    if not _Pyceler_Is_C_Function(Implementation) or Implementation is not B.getattr(Native_Module, 'empty_like', None):", "        return False",
                      "    if Implementation.__name__ != 'empty_like' or Implementation.__self__ is not Native_Module:", "        return False"])
    Lines.append("    if Output.dtype.kind == 'f':")
    if not Plan["Arithmetic"] or Plan["Abs"]:
        Float_Check = "False" if Plan["Abs"] else " and ".join(f"B.type(V{Slot}) is B.int and -16777216 <= V{Slot} <= 16777216" for Slot in Scalars) or "True"
        Lines.append("        return " + Float_Check)
    else:
        Lines.extend(["        if _Pyceler_Rounding() != _Pyceler_Nearest:", "            return False"])
        Lines.append("        Limit = 16777216 if Output.itemsize == 4 else 9007199254740992")
        for Slot in Scalars:
            Lines.extend([f"        if B.type(V{Slot}) is not B.int or not -Limit <= V{Slot} <= Limit:", "            return False"])
        Lines.extend(["        if Output.size == 0:", "            return True"])
        Initial = {Recipe[1] for Recipe in Plan["Nodes"] if Recipe[0] == "array" and Recipe[2] == 0}
        for Slot in Arrays:
            if Slot not in Initial:
                Lines.append(f"        Low{Slot}, High{Slot} = -Limit, Limit")
            else:
                Lines.extend(["        if Output.itemsize == 4:", f"            Bounds = _Pyceler_Integral_Bounds[float](V{Slot}.reshape(-1), Limit)",
                              "        else:", f"            Bounds = _Pyceler_Integral_Bounds[double](V{Slot}.reshape(-1), Limit)",
                              "        if Bounds is None:", "            return False", f"        Low{Slot}, High{Slot} = Bounds"])
        Limits = ", ".join(f"Low{Slot}, High{Slot}" for Slot in Arrays)
        Lines.append(f"        return {Name}_Ranges({Arguments}, -Limit, Limit, {Limits}, True)")
    Lines.extend(["    Bits = Output.itemsize * 8",
                  "    Minimum = 0 if Output.dtype.kind == 'u' else -(1 << (Bits - 1))", "    Maximum = Minimum + (1 << Bits) - 1"])
    for Slot in Scalars:
        Lines.extend([f"    if B.type(V{Slot}) is not B.int or not Minimum <= V{Slot} <= Maximum:", "        return False"])
    Lines.extend(["    if Output.size == 0:", "        return True"])
    Limits = ", ".join("Minimum, Maximum" for Slot in Arrays)
    Lines.extend([f"    if {Name}_Ranges({Arguments}, Minimum, Maximum, {Limits}):", "        return True"])
    Initial = {Recipe[1] for Recipe in Plan["Nodes"] if Recipe[0] == "array" and Recipe[2] == 0}
    for Slot in Arrays:
        Expression = f"_Pyceler_Integer_Bounds(V{Slot})" if Slot in Initial else "(Minimum, Maximum)"
        Lines.append(f"    Low{Slot}, High{Slot} = {Expression}")
    Limits = ", ".join(f"Low{Slot}, High{Slot}" for Slot in Arrays)
    return [*Lines, f"    return {Name}_Ranges({Arguments}, Minimum, Maximum, {Limits})", ""]
