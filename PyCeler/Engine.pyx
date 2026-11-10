import ast
import math
import re
import sys
import tokenize
from pathlib import Path
from .Loop_Detector import Loop_Finding
from .Native_Build import _Build, _Member_Alias, _Publish, _Temporary_Workspace, _Workspace
from .Runtime_Resources import _Resource

cdef bint _Name(object Node, str Name):
    return isinstance(Node, ast.Name) and Node.id == Name

cdef bint _Integer(object Node, int Value):
    return isinstance(Node, ast.Constant) and type(Node.value) is int and Node.value == Value

cdef object _Bounds(object Node):
    if not isinstance(Node, ast.Call) or not _Name(Node.func, "range") or Node.keywords:
        return None
    cdef list Args = Node.args
    if len(Args) != 1 and not (len(Args) == 2 and _Integer(Args[0], 1)):
        return None
    Length = Args[-1]
    if not isinstance(Length, ast.Call) or not _Name(Length.func, "len") or Length.keywords:
        return None
    if len(Length.args) == 1 and isinstance(Length.args[0], ast.Name):
        return Length.args[0].id, len(Args) - 1
    return None

cdef bint _Element(object Target, str Elements, str Index):
    return isinstance(Target, ast.Subscript) and _Name(Target.value, Elements) and _Name(Target.slice, Index)

cdef tuple _Classify(object Node, object Function):
    if isinstance(Node, ast.While):
        return "Unknown", "This while loop has no verified scalar-integer or counted-array conversion."
    if Function is None or not isinstance(Node, ast.For) or not isinstance(Node.target, ast.Name):
        return "Unknown", "Expected an indexed for loop inside a function."
    Bounds = _Bounds(Node.iter)
    if Bounds is None:
        return "Unknown", "The iteration bounds do not match a supported indexed range."
    Elements, Start = Bounds
    Index = Node.target.id
    if len({Elements, Index, "range", "len"}) != 4 or len(Node.body) != 1 or Node.orelse:
        return "Unknown", "Expected distinct names and a single statement without a loop else."
    Statement = Node.body[0]
    if Start == 0 and isinstance(Statement, ast.Assign) and len(Statement.targets) == 1:
        if _Element(Statement.targets[0], Elements, Index) and _Integer(Statement.value, 0):
            return "Potential_Independent_Write", (
                f"Each iteration writes only {Elements}[{Index}]. Requires built-in range and len and a supported "
                "writable numeric array with verified dtype, layout and distinct element storage."
            )
    if Start == 1 and isinstance(Statement, ast.AugAssign) and isinstance(Statement.op, ast.Add):
        Read = Statement.value
        if _Element(Statement.target, Elements, Index) and isinstance(Read, ast.Subscript) and _Name(Read.value, Elements):
            Offset = Read.slice
            if isinstance(Offset, ast.BinOp) and isinstance(Offset.op, ast.Sub) and _Name(Offset.left, Index) and _Integer(Offset.right, 1):
                return "Loop_Carried_Dependency", f"{Elements}[{Index} - 1] reads the preceding iteration's write. Independent parallel execution is ineligible."
    return "Unknown", "The loop body does not match a supported indexed write or prefix sum."

cdef void _Accesses(object Node, list Reads, list Writes) except *:
    if isinstance(Node, (ast.For, ast.AsyncFor, ast.While, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
        return
    if isinstance(Node, ast.AugAssign) and isinstance(Node.target, ast.Subscript):
        Reads.append(ast.unparse(Node.target))
    if isinstance(Node, ast.Subscript):
        (Reads if isinstance(Node.ctx, ast.Load) else Writes).append(ast.unparse(Node))
    for Child in ast.iter_child_nodes(Node):
        _Accesses(Child, Reads, Writes)

cdef bint _Whole_Clear(object Function, object Node, str Elements):
    if not isinstance(Function, ast.FunctionDef) or Function.decorator_list:
        return False
    Body = Function.body
    if ast.get_docstring(Function, clean=False) is not None:
        Body = Body[1:]
    Args = Function.args
    Positions = Args.posonlyargs + Args.args
    return (len(Body) == 2 and Body[0] is Node and isinstance(Body[1], ast.Return)
            and _Name(Body[1].value, Elements) and len(Positions) == 1 and Positions[0].arg == Elements
            and not Args.kwonlyargs and Args.vararg is None and Args.kwarg is None)

include "Map_Planner.pxi"
include "Scalar_Loops.pxi"
include "Special_Regions.pxi"
include "Projection.pxi"
include "Row_Selection.pxi"
include "Stream_Loops.pxi"
include "Regions.pxi"
include "Structural_Planner.pxi"
include "Numeric_Planner.pxi"
include "Analysis_Ranking.pxi"
include "Cython_Frontend.pxi"

cdef void _Visit(object Node, tuple Scope, object Function, list Findings, dict Edits, str Source, bint Parallel, set Top_Level, object Covered=None) except *:
    if isinstance(Node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        Scope = (*Scope, Node.name)
        Function = None if isinstance(Node, ast.ClassDef) else Node
        Covered = {}
        if Node in Top_Level:
            Receive = _Exact_Read(Node)
            if Receive is not None:
                Loop = Receive["Loop"]
                Edits[Loop.lineno] = (Receive["Names"], Node, Node, Receive)
                Covered[Loop] = ("Ordered_IO_Loop", "Receive calls, short reads, EOF and the original exception handlers remain ordered. Selection uses an in-memory fragmented stream.", "Guarded serial exact-length receive")
            Scalar = _Scalar_Plan(Node)
            if Scalar is not None:
                Edits[Node.lineno] = (Scalar["Names"], Node, Node, Scalar)
                for Loop in Scalar["Loops"]:
                    Covered[Loop] = ("Scalar_Integer_Loop", "Exact integer locals and checked arithmetic preserve iteration order; overflow replays the side-effect-free function in Python.", "Guarded serial integer loop")
    if isinstance(Node, (ast.For, ast.AsyncFor, ast.While)):
        Classification, Reason = _Classify(Node, Function)
        Reads, Writes = [], []
        for Statement in Node.body:
            _Accesses(Statement, Reads, Writes)
        Change = "Keep original loop"
        if Classification == "Potential_Independent_Write" and Function in Top_Level:
            Elements = _Bounds(Node.iter)[0]
            if _Whole_Clear(Function, Node, Elements) and not getattr(Function, "type_params", ()):
                Edits[Node.lineno] = ((Elements,), Node, Function, None)
                Change = "Guarded OpenMP zero fill with serial fallback" if Parallel else "Guarded serial zero fill"
        if Node.lineno not in Edits and Function in Top_Level:
            Plan = _Map_Plan(Function, Node)
            if isinstance(Plan, str):
                Reason = Plan
            elif Plan is not None:
                Edits[Node.lineno] = (Plan["Names"], Node, Function, Plan)
                Dimensions = len(Plan["Indices"])
                Classification = "Potential_Independent_Write"
                Change = f"Guarded {Dimensions}D " + ("OpenMP" if Parallel else "serial") + " element-wise kernel"
                Reason = "Each iteration accesses its own position. The generated kernel checks shape, dtype, layout, writability and overlapping storage."
                if Plan["Arithmetic"]:
                    Reason += " Arithmetic requires proven integer ranges or a supported bounded floating-point operation."
                if Dimensions > 1:
                    _Accesses(Plan["Element"], Reads, Writes)
                    for Loop in Plan["Loops"][1:]:
                        Covered[Loop] = ("Potential_Independent_Write", "The enclosing kernel visits each guarded output position once.", f"Included in outer {Dimensions}D element-wise kernel")
        if Covered and Node in Covered:
            Classification, Reason, Change = Covered[Node]
        elif Change == "Keep original loop":
            Operations = sorted({Part.func.attr for Part in ast.walk(Node) if isinstance(Part, ast.Call) and isinstance(Part.func, ast.Attribute)
                                 and Part.func.attr in {"recv", "recv_into", "recvfrom", "recvfrom_into", "send", "sendto", "sendall", "accept", "select"}})
            if Operations:
                Classification = "Ordered_IO_Loop"
                Reason = "Keep the order and exception boundaries of " + ", ".join(Operations) + "; numeric subloops are analyzed separately."
        Findings.append(Loop_Finding(".".join(Scope) if Function is not None else None, Node.lineno, Node.end_lineno,
                                     tuple(Reads), tuple(Writes), Classification, Reason, Change, Source))
    for Child in ast.iter_child_nodes(Node):
        _Visit(Child, Scope, Function, Findings, Edits, Source, Parallel, Top_Level, Covered)

cdef tuple _Plan(object File, bint Parallel, bint Elide_Temporaries=False):
    with tokenize.open(str(File)) as Stream:
        Text = Stream.read()
    if File.suffix in (".pyx", ".pxi"):
        Native_Text, Native_Findings, Native_Edits, Native_Tree = _Cython_Plan(File, Text)
        return Native_Text, _Rank_Findings(Native_Findings, None), Native_Edits, Native_Tree
    Tree = ast.parse(Text, filename=str(File))
    Findings, Edits = [], {}
    _Visit(Tree, (), None, Findings, Edits, str(File), Parallel, set(Tree.body))
    _Find_Regions(Tree, Findings, Edits, Parallel)
    _Structural_Plans(Tree, Findings, Edits, Parallel, Elide_Temporaries)
    _Numeric_Plans(Tree, Findings, Edits, Parallel, Elide_Temporaries)
    Findings = _Rank_Findings(Findings, Tree, Edits)
    return Text, Findings, Edits, Tree

cdef tuple _Inputs(object Source_Path):
    from .Source_Inputs import _Source_Inputs
    return _Source_Inputs(Source_Path)

def Analyze(Source_Path, *, OpenMP=False, Elide_Temporaries=False):
    if type(Elide_Temporaries) is not bool:
        raise ValueError("Elide_Temporaries must be True or False")
    Source, Root, Files = _Inputs(Source_Path)
    Findings = []
    for File in Files:
        Findings.extend(_Plan(File, OpenMP, Elide_Temporaries)[1])
    return tuple(Findings)

include "Generator.pxi"
include "Selection.pxi"
