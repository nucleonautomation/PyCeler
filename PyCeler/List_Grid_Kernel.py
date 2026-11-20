import ast
import copy
from .Fast_Math import _Fast_Emit_Program, _Fast_Math_Kernel
from .Math_Maps import _Module_Constant_Kernel, _Module_Constant_Anchor
# Generate buffered list-grid execution and preserve Python values at publication boundaries.
def _List_Grid_Kernel(Plan, Line, Filename, Measured):
    Prefix = f"_Pyceler_Fast_{Line}_"
    Grid = f"_Pyceler_Grid_{Line}_"
    Work, Variables = [], ["L" + str(Index) for Index in range(len(Plan["Slots"]))]
    _Fast_Emit_Program(Plan["Program"], Work, Variables, (), Prefix)
    Slots = Plan["Slots"]
    Sources = tuple(Name for Name in Plan["Grids"] if Name != Plan["Output"])
    Reads = Plan["Reads"]
    Args = ", ".join([*("double X" + str(Index) for Index in range(len(Reads))), "double Row", "double Column", "bint* Valid"])
    Lines = [_Module_Constant_Kernel(Line), _Fast_Math_Kernel(dict(Functions=(), Bindings=()), Line, Preamble=True),
             f"from cpython.float cimport PyFloat_CheckExact as {Grid}Float", f"from cpython.long cimport PyLong_CheckExact as {Grid}Integer",
             f"from cpython.bool cimport PyBool_Check as {Grid}Boolean", f"from cpython.list cimport PyList_CheckExact as {Grid}List",
             f"@{Prefix}Division(True)", f"cdef inline double {Grid}Value({Args}) noexcept nogil:"]
    for Start, Type in (("L", "double"), ("T", "volatile double")):
        Group = [Name for Name in Variables if Name.startswith(Start)]
        if Group:
            Lines.append("    cdef " + Type + " " + ", ".join(Group))
    for Index in range(len(Reads)):
        Lines.extend([f"    if not {Prefix}Finite(X{Index}):", "        Valid[0] = False", "        return 0.0", f"    L{Slots.index('_Pyceler_Grid_Read_' + str(Index))} = X{Index}"])
    Lines.extend([f"    L{Slots.index(Plan['Indices'][0])} = Row", f"    L{Slots.index(Plan['Indices'][1])} = Column", *Work, f"    return L{Slots.index('_Pyceler_Grid_Result')}"])
    Body = ast.unparse(ast.Module(body=Plan["Statements"], type_ignores=[]))
    Lines.extend([f"cdef object {Grid}Columns = compile({Plan['Ranges'][1]!r}, {Filename!r}, 'eval', dont_inherit=True)",
                  f"cdef object {Grid}Body = compile({Body!r}, {Filename!r}, 'exec', dont_inherit=True)",
                  f"cdef object _Pyceler_Grid_Try_{Line}(dict Namespace, object Rows, object Binding, object Length_Binding, object Policy, object Source_Code):",
                  "    import builtins as B", "    cdef Py_ssize_t Height, Width, Count, Size, Row, Column, Position, Index, Start_Row, Start_Column, End_Row, End_Column, Columns_Count",
                  "    cdef double* Inputs = NULL", "    cdef double* Scratch = NULL", "    cdef list Matrix, Row_List, Destination, Values, Matrices, Output_Rows",
                  "    cdef bint Valid = True", "    cdef int Flags", f"    cdef {Prefix}Environment Saved", f"    cdef {Prefix}Exception_State Prepared",
                  f"    global {Prefix}Native_Elements, {Prefix}Last_Team", "    _Pyceler_Dispatch_Event('Execution', 'python_fallback', 0)",
                  f"    if Binding is not B.range or Length_Binding is not B.len or B.type(Rows) is not B.range or Rows.step != 1:", "        return None",
                  f"    if B.type(Length_Binding) is not {Prefix}Types.BuiltinFunctionType or Length_Binding.__self__ is not B or Length_Binding.__name__ != 'len' or not {Prefix}Exclusive():", "        return None"])
    for Name in Plan["Names"]:
        Lines.extend([f"    if {Name!r} not in Namespace:", "        return None"])
    for Name in Plan["Controls"]:
        Lines.extend([f"    if not {Grid}Integer(Namespace[{Name!r}]):", "        return None"])
    for Name in (*Plan["Indices"], *Plan["Written"]):
        Lines.extend([f"    Previous = Namespace.get({Name!r})", f"    if not ({Grid}Float(Previous) or {Grid}Integer(Previous) or {Grid}Boolean(Previous) or Previous is None):", "        return None"])
    Lines.extend(["    Matrices = [" + ", ".join(f"Namespace[{Name!r}]" for Name in Sources) + "]", f"    Target = Namespace[{Plan['Output']!r}]",
                  f"    if not {Grid}List(Target) or not Target or not {Grid}List(Target[0]):", "        return None", "    Height, Width = B.len(Target), B.len(Target[0])",
                  "    if Width == 0 or Height > 1048576 or Width > 1048576 or Height * Width > 1048576:", "        return None", "    for Matrix_Object in Matrices:", "        if Matrix_Object is Target:", "            return None", "    Size = Height * Width", "    Output_Rows = list(Target)", "    Input_Identities = set()", "    Output_Identities = set()",
                  "    for Matrix_Object in [*Matrices, Target]:", f"        if not {Grid}List(Matrix_Object) or B.len(Matrix_Object) != Height:", "            return None", "        for Row_Object in Matrix_Object:", f"            if not {Grid}List(Row_Object) or B.len(Row_Object) != Width:", "                return None",
                  "            if Matrix_Object is Target:", "                if B.id(Row_Object) in Output_Identities:", "                    return None", "                Output_Identities.add(B.id(Row_Object))", "            else:", "                Input_Identities.add(B.id(Row_Object))",
                  "    if Input_Identities & Output_Identities:", "        return None", "    if not 0 <= Rows.start < Rows.stop <= Height:", "        return None",
                  f"    Columns = B.eval({Grid}Columns, Namespace)", "    if B.type(Columns) is not B.range or Columns.step != 1 or not 0 <= Columns.start < Columns.stop <= Width:", "        return None",
                  "    Start_Row, Start_Column, End_Row, End_Column = Rows.start, Columns.start, Rows.stop, Columns.stop", "    Columns_Count = End_Column - Start_Column", "    Count = (End_Row - Start_Row) * Columns_Count", "    if Count < 2:", "        return None"])
    if Measured:
        Lines.extend(["    if Policy is not None and not _Pyceler_Choose((Count,), True, Policy):", "        return None"])
    for Name, Row, Column in Reads:
        Lines.extend([f"    if Rows.start + ({Row}) < 0 or Rows.stop - 1 + ({Row}) >= Height or Columns.start + ({Column}) < 0 or Columns.stop - 1 + ({Column}) >= Width:", "        return None"])
    Lines.extend([f"    Inputs = <double*>{Prefix}Allocate(Size * {len(Sources)} * sizeof(double))", f"    Scratch = <double*>{Prefix}Allocate(Count * sizeof(double))", "    if Inputs == NULL or Scratch == NULL:", f"        {Prefix}Free(Inputs)", f"        {Prefix}Free(Scratch)", "        return None", "    try:", "        for Index in range(len(Matrices)):", "            Matrix = Matrices[Index]", "            for Row in range(Height):", "                Row_List = Matrix[Row]", "                for Column in range(Width):", "                    Previous = Row_List[Column]", f"                    if not {Grid}Float(Previous):", "                        return None", "                    Inputs[Index * Size + Row * Width + Column] = Previous",
                  "        for Row in range(Start_Row, End_Row):", "            Row_List = Output_Rows[Row]", "            for Column in range(Start_Column, End_Column):", "                Previous = Row_List[Column]", f"                if not ({Grid}Float(Previous) or {Grid}Integer(Previous) or {Grid}Boolean(Previous) or Previous is None):", "                    return None",
                  f"        if {Prefix}Get_Environment(&Saved) != 0:", "            return None", "        for Position in range(Count):", "            Row = Start_Row + Position // Columns_Count", "            Column = Start_Column + Position % Columns_Count"])
    Values = [f"Inputs[{Sources.index(Name)} * Size + (Row + ({Row})) * Width + Column + ({Column})]" for Name, Row, Column in Reads]
    Lines.extend([f"            Scratch[Position] = {Grid}Value({', '.join([*Values, 'Row', 'Column', '&Valid'])})", "            if not Valid:", "                break", f"        Flags = {Prefix}Test_Exceptions({Prefix}All_Exceptions)", f"        {Prefix}Set_Environment(&Saved)", "        if not Valid:", "            return None", f"        if Flags and {Prefix}Prepare_Exceptions(Flags, &Prepared) != 0:", "            return None",
                  "        Values = [None] * (Count - 1)", "        for Position in range(Count - 1):", "            Values[Position] = Scratch[Position]",
                  f"        Pool = _Pyceler_Module_Constants_{Line}_Pool(Source_Code)", f"        Body = _Pyceler_Module_Constants_{Line}_Code({Grid}Body, Pool)",
                  "        for Position in range(Count - 1):", "            Row = Start_Row + Position // Columns_Count", "            Column = Start_Column + Position % Columns_Count", "            Row_List = Output_Rows[Row]", "            Row_List[Column] = Values[Position]",
                  "        if Flags:", f"            {Prefix}Set_Exceptions(&Prepared, Flags)", f"        Namespace[{Plan['Indices'][0]!r}] = Rows.stop - 1", f"        Namespace[{Plan['Indices'][1]!r}] = Columns.stop - 1", "        B.exec(Body, Namespace)", f"        {Prefix}Native_Elements += Count - 1", f"        {Prefix}Last_Team = 1", "        _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)",
                  "        return (" + ", ".join(f"Namespace[{Name!r}]" for Name in (*Plan["Indices"], *Plan["Written"])) + ",)", "    finally:", f"        {Prefix}Free(Inputs)", f"        {Prefix}Free(Scratch)"])
    return "\n".join(Lines) + "\n"

def _List_Grid_Source(Plan, Node, Line, Prefix, Table):
    Range = f"{Prefix}Grid_Rows_{Line}"
    Result = f"{Prefix}Grid_Result_{Line}"
    Namespace = f"{Prefix}Module_Namespace()" if Plan["Module"] else "{" + ", ".join(repr(Name) + ": " + Name for Name in dict.fromkeys((*Plan["Names"], *Plan["Output_Guards"]))) + "}"
    Policy = f"{Prefix}Table_{Line}" if Table is not None else "None"
    Lines = [_Module_Constant_Anchor(Node, Line, Prefix), f"{Range} = {ast.unparse(Node.iter)}", f"{Result} = {Prefix}Grid_Try_{Line}({Namespace}, {Range}, range, len, {Policy}, {Prefix}Module_Constants_{Line}.__code__)", f"if {Result} is None:"]
    Fallback = copy.deepcopy(Node)
    Fallback.iter = ast.Name(id=Range, ctx=ast.Load())
    Lines.extend("    " + Text for Text in ast.unparse(Fallback).splitlines())
    if not Plan["Module"]:
        Lines.extend(["else:", "    " + ", ".join((*Plan["Indices"], *Plan["Written"])) + " = " + Result])
    return "\n".join(Lines)
