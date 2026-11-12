import ast
import hashlib
import json
from dataclasses import asdict, dataclass, replace

_Plan_Version = 1
_Loop_Types = (ast.For, ast.AsyncFor, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_Scopes = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)

@dataclass(frozen=True)
class _Flow_Block:
    Id: int
    Parent: int | None
    Kind: str
    Location: tuple[int, int, int, int]
    Defines: tuple[str, ...]
    Uses: tuple[str, ...]
    Successors: tuple[int, ...]
    Exit: str

@dataclass(frozen=True)
class _Call_Plan:
    Name: str
    Location: tuple[int, int, int, int]
    Effect: str
    Binding: str
    Status: str
    Reason: str
    Contract: str = ""

@dataclass(frozen=True)
class _Type_Fact:
    Name: str
    Category: str
    Evidence: str
    Detail: str

@dataclass(frozen=True)
class _Expression_Plan:
    Kind: str
    Location: tuple[int, int, int, int]
    Text: str
    Evaluation: str

@dataclass(frozen=True)
class _Analysis_Plan:
    Version: int
    Kind: str
    Location: tuple[int, int, int, int]
    Shape_Key: str
    Blocks: tuple[_Flow_Block, ...]
    Inputs: tuple[str, ...]
    Definitions: tuple[str, ...]
    Live_Out: tuple[str, ...]
    Loop_Carried: tuple[str, ...]
    Indexed_Reads: tuple[str, ...]
    Indexed_Writes: tuple[str, ...]
    Calls: tuple[_Call_Plan, ...]
    Expressions: tuple[_Expression_Plan, ...]
    Type_Facts: tuple[_Type_Fact, ...]
    Effects: tuple[str, ...]
    Exits: tuple[str, ...]
    Serial_Status: str
    Parallel_Status: str
    Guards: tuple[str, ...]
    Blockers: tuple[str, ...]
    Adapter: str
    Iteration_Clauses: int

    def _Serialize(self):
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def _Fingerprint(self):
        return hashlib.sha256(self._Serialize().encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class _Map_Plan:
    Version: int
    Kind: str
    Dimensions: int
    Argument_Count: int
    Output: int
    Arrays: tuple[int, ...]
    Scalars: tuple[int, ...]
    Reads: tuple[int, ...]
    Expressions: tuple[str, ...]
    Guards: tuple[str, ...]

    def _Serialize(self):
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

def _Location(Node):
    return (getattr(Node, "lineno", 0), getattr(Node, "col_offset", -1) + 1,
            getattr(Node, "end_lineno", getattr(Node, "lineno", 0)), getattr(Node, "end_col_offset", -1) + 1)

def _Parts(Node):
    yield Node
    for Child in ast.iter_child_nodes(Node):
        if not isinstance(Child, _Scopes):
            yield from _Parts(Child)

def _Names(Node, Context):
    return {Part.id for Part in _Parts(Node) if isinstance(Part, ast.Name) and isinstance(Part.ctx, Context)}

def _Usage(Node):
    Defines = _Names(Node, (ast.Store, ast.Del))
    Uses = _Names(Node, ast.Load)
    for Part in _Parts(Node):
        if isinstance(Part, ast.AugAssign) and isinstance(Part.target, ast.Name):
            Uses.add(Part.target.id)
        if isinstance(Part, (ast.Import, ast.ImportFrom)):
            Defines.update(Alias.asname or Alias.name.split(".")[0] for Alias in Part.names if Alias.name != "*")
        if isinstance(Part, ast.ExceptHandler) and Part.name:
            Defines.add(Part.name)
    return Defines, Uses

def _Targets(Node):
    return _Names(Node, ast.Store)

def _Binding_Targets(Node):
    if isinstance(Node, ast.Name):
        return {Node.id}
    if isinstance(Node, (ast.Tuple, ast.List)):
        return set().union(*(_Binding_Targets(Element) for Element in Node.elts))
    if isinstance(Node, ast.Starred):
        return _Binding_Targets(Node.value)
    return set()

def _Definite_Bindings(Statements, Entering=()):
    Bound = set(Entering)
    for Statement in Statements:
        if any(isinstance(Node, (ast.Yield, ast.YieldFrom, ast.Await)) for Node in ast.walk(Statement)):
            return None
        if isinstance(Statement, ast.Assign):
            Bound.update(set().union(*(_Binding_Targets(Target) for Target in Statement.targets)))
        elif isinstance(Statement, ast.AnnAssign):
            if Statement.value is not None:
                Bound.update(_Binding_Targets(Statement.target))
        elif isinstance(Statement, ast.If):
            Left = _Definite_Bindings(Statement.body, Bound)
            Right = _Definite_Bindings(Statement.orelse, Bound)
            if Left is None or Right is None:
                return None
            Bound = set(Left & Right)
        elif not isinstance(Statement, (ast.Expr, ast.Pass)):
            return None
    return frozenset(Bound)

def _Reads_Before_Definition(Statements, Defined=None):
    Defined = set(Defined or ())
    Reads = set()
    for Statement in Statements:
        if isinstance(Statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            Defined.add(Statement.name)
            continue
        if isinstance(Statement, ast.If):
            Reads.update(_Names(Statement.test, ast.Load) - Defined)
            Left_Reads, Left_Defined = _Reads_Before_Definition(Statement.body, Defined)
            Right_Reads, Right_Defined = _Reads_Before_Definition(Statement.orelse, Defined)
            Reads.update(Left_Reads | Right_Reads)
            Defined.update(Left_Defined & Right_Defined)
            continue
        if isinstance(Statement, (ast.For, ast.AsyncFor, ast.While)):
            Header = Statement.test if isinstance(Statement, ast.While) else Statement.iter
            Reads.update(_Names(Header, ast.Load) - Defined)
            Targets = set() if isinstance(Statement, ast.While) else _Targets(Statement.target)
            Body_Reads, _ = _Reads_Before_Definition(Statement.body, Defined | Targets)
            Else_Reads, _ = _Reads_Before_Definition(Statement.orelse, Defined)
            Reads.update(Body_Reads | Else_Reads)
            continue
        if isinstance(Statement, (ast.Try, getattr(ast, "TryStar", ast.Try), ast.With, ast.AsyncWith, ast.Match)):
            Reads.update(_Usage(Statement)[1] - Defined)
            continue
        New, Used = _Usage(Statement)
        Reads.update(Used - Defined)
        if isinstance(Statement, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Import, ast.ImportFrom)):
            Defined.update(New)
        elif isinstance(Statement, ast.Delete):
            Defined.difference_update(New)
    return Reads, Defined

def _Shape(Node):
    Names = {}
    def Normalize(Value):
        if isinstance(Value, ast.Name):
            Name = Names.setdefault(Value.id, "V" + str(len(Names)))
            return ("Name", Name, type(Value.ctx).__name__)
        if isinstance(Value, ast.AST):
            return (type(Value).__name__, tuple((Key, Normalize(Item)) for Key, Item in ast.iter_fields(Value)
                                               if Key not in ("type_comment", "type_params")))
        if isinstance(Value, list):
            return tuple(Normalize(Item) for Item in Value)
        return Value
    Encoded = json.dumps(Normalize(Node), sort_keys=True, separators=(",", ":"), default=repr)
    return hashlib.sha256(Encoded.encode("utf-8")).hexdigest()

def _Blocks(Node):
    Records = []
    def Add(Current, Parent, Next=None, Loop_Exit=None, Loop_Header=None):
        Index = len(Records)
        if isinstance(Current, (ast.For, ast.AsyncFor)):
            Defines, Uses = _Targets(Current.target), _Usage(Current.iter)[1]
        elif isinstance(Current, (ast.If, ast.While)):
            Defines, Uses = set(), _Usage(Current.test)[1]
        else:
            Defines, Uses = _Usage(Current)
        Exit = type(Current).__name__.lower() if isinstance(Current, (ast.Return, ast.Raise, ast.Break, ast.Continue)) else ""
        Records.append(dict(Id=Index, Parent=Parent, Kind=type(Current).__name__, Location=_Location(Current),
                            Defines=tuple(sorted(Defines)), Uses=tuple(sorted(Uses)), Successors=(), Exit=Exit))
        if isinstance(Current, (ast.For, ast.AsyncFor, ast.While)):
            Else = Sequence(Current.orelse, Index, Next, Loop_Exit, Loop_Header)
            After = Else if Else is not None else Next
            Body = Sequence(Current.body, Index, Index, Next, Index)
            Records[Index]["Successors"] = tuple(Item for Item in (Body, After) if Item is not None)
        elif isinstance(Current, ast.If):
            Yes = Sequence(Current.body, Index, Next, Loop_Exit, Loop_Header)
            No = Sequence(Current.orelse, Index, Next, Loop_Exit, Loop_Header)
            Records[Index]["Successors"] = tuple(dict.fromkeys(Item for Item in (Yes, No) if Item is not None))
        elif isinstance(Current, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for Clause in Current.generators:
                Clause_Index = len(Records)
                Records.append(dict(Id=Clause_Index, Parent=Index, Kind="AsyncComprehension" if Clause.is_async else "Comprehension",
                                    Location=_Location(Clause.iter), Defines=tuple(sorted(_Targets(Clause.target))),
                                    Uses=tuple(sorted(_Usage(Clause)[1])), Successors=(Clause_Index,), Exit="python_iterator"))
            Records[Index]["Successors"] = (Index + 1,) if Current.generators else ()
        elif isinstance(Current, (ast.Try, getattr(ast, "TryStar", ast.Try), ast.With, ast.AsyncWith, ast.Match)):
            Records[Index]["Exit"] = "python_control_boundary"
            Records[Index]["Successors"] = (Next,) if Next is not None else ()
        elif isinstance(Current, ast.Break):
            Records[Index]["Successors"] = (Loop_Exit,) if Loop_Exit is not None else ()
        elif isinstance(Current, ast.Continue):
            Records[Index]["Successors"] = (Loop_Header,) if Loop_Header is not None else ()
        elif not isinstance(Current, (ast.Return, ast.Raise)):
            Records[Index]["Successors"] = (Next,) if Next is not None else ()
        return Index
    def Sequence(Statements, Parent, Next, Loop_Exit, Loop_Header):
        Entry = Next
        for Statement in reversed(Statements):
            Entry = Add(Statement, Parent, Entry, Loop_Exit, Loop_Header)
        return Entry
    Add(Node, None)
    return tuple(_Flow_Block(**Record) for Record in Records)

def _Facts(Function, Node, Inputs, Parents):
    Facts = {}
    if isinstance(Function, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        Arguments = Function.args
        for Argument in (*Arguments.posonlyargs, *Arguments.args, *Arguments.kwonlyargs):
            if Argument.arg in Inputs and Argument.annotation is not None:
                Facts[Argument.arg] = _Type_Fact(Argument.arg, "unknown", "annotation_hint", ast.unparse(Argument.annotation))
    Levels = []
    Current = Node
    while Current in Parents:
        Parent = Parents[Current]
        Body = getattr(Parent, "body", ())
        if isinstance(Body, list) and Current in Body:
            Levels.append(Body[:Body.index(Current)])
        if Parent is Function or isinstance(Parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            break
        Current = Parent
    for Statements in reversed(Levels):
        for Statement in Statements:
            for Name in _Usage(Statement)[0]:
                Facts.pop(Name, None)
            if isinstance(Statement, ast.Assign) and len(Statement.targets) == 1 and isinstance(Statement.targets[0], ast.Name):
                Value = Statement.value
                Negative = isinstance(Value, ast.UnaryOp) and isinstance(Value.op, ast.USub)
                Literal = Value.operand if Negative else Value
                if isinstance(Literal, ast.Constant) and type(Literal.value) in (int, float, bool, str, bytes, type(None)):
                    Kind = type(Literal.value).__name__
                    if not Negative or Kind in ("int", "float"):
                        Facts[Statement.targets[0].id] = _Type_Fact(Statement.targets[0].id, Kind, "static_assignment", ast.unparse(Value))
    for Name in Inputs:
        Facts.setdefault(Name, _Type_Fact(Name, "unknown", "unresolved", "Runtime type and conversion behavior require guards."))
    return tuple(Facts[Name] for Name in sorted(Facts) if Name in Inputs)

def _Indexed(Node):
    Reads, Writes = [], []
    for Part in _Parts(Node):
        if isinstance(Part, ast.Subscript):
            (Reads if isinstance(Part.ctx, ast.Load) else Writes).append(Part)
        elif isinstance(Part, ast.AugAssign) and isinstance(Part.target, ast.Subscript):
            Reads.append(Part.target)
    return Reads, Writes

def _Dependencies(Node, Reads, Writes, Carried):
    Blockers = []
    if Carried:
        Blockers.append("Loop-carried scalar state requires an ordered execution or an exact reduction proof: " + ", ".join(Carried) + ".")
    Targets = set()
    for Part in _Parts(Node):
        if isinstance(Part, (ast.For, ast.AsyncFor)):
            Targets.update(_Targets(Part.target))
        elif isinstance(Part, ast.While) and isinstance(Part.test, ast.Compare) and isinstance(Part.test.left, ast.Name):
            Targets.add(Part.test.left.id)
    for Write in Writes:
        Positions = Write.slice.elts if isinstance(Write.slice, ast.Tuple) else [Write.slice]
        Names = [Position.id for Position in Positions if isinstance(Position, ast.Name)]
        if len(Names) != len(Positions) or len(set(Names)) != len(Names) or not set(Names) <= Targets:
            Blockers.append("Indexed write " + ast.unparse(Write) + " needs a proof of unique, bounded iteration addresses.")
        for Read in Reads:
            if ast.dump(Read.value) == ast.dump(Write.value) and ast.dump(Read.slice) != ast.dump(Write.slice):
                Blockers.append("Potential cross-iteration dependency between " + ast.unparse(Read) + " and " + ast.unparse(Write) + ".")
    return tuple(dict.fromkeys(Blockers))

def _Calls(Node, Math_Calls):
    Result = []
    for Part in _Parts(Node):
        if not isinstance(Part, ast.Call):
            continue
        Name = ast.unparse(Part.func)
        Record = Math_Calls.get((Part.lineno, Part.col_offset + 1))
        if Record is None:
            Conditional = isinstance(Part.func, ast.Name) and Part.func.id in ("range", "len", "enumerate", "zip")
            Result.append(_Call_Plan(Name, _Location(Part), "conditional_builtin" if Conditional else "unknown", "runtime_guard_required",
                                     "guard_required" if Conditional else "python_boundary",
                                     "Binding, argument types and iteration/conversion behavior require validation." if Conditional
                                     else "Preserve call order, conversions, exceptions and observable state until a call contract is established."))
        else:
            Contract = Record.get("Contract", {})
            Binding = Record.get("Binding", {})
            Status = str(Record.get("Status", "python_boundary"))
            Effect = "conditional_numeric" if Status == "Recognized" else "unknown"
            Result.append(_Call_Plan(Name, _Location(Part), Effect, str(Binding.get("Status", "runtime_guard_required")),
                                     Status, str(Record.get("Reason", "Runtime guards required.")),
                                     json.dumps(Contract, sort_keys=True, separators=(",", ":"), default=str)))
    return tuple(sorted(Result, key=lambda Item: Item.Location))

def _Effects(Node):
    Effects = set()
    Exits = {"normal"}
    for Part in _Parts(Node):
        if isinstance(Part, ast.Call):
            Effects.add("call_or_conversion")
            Exits.add("exception")
        elif isinstance(Part, ast.Subscript):
            Effects.add("indexed_read" if isinstance(Part.ctx, ast.Load) else "indexed_write")
            Exits.add("exception")
        elif isinstance(Part, ast.Attribute):
            Effects.add("attribute_read" if isinstance(Part.ctx, ast.Load) else "attribute_write")
            Exits.add("exception")
        elif isinstance(Part, (ast.Global, ast.Nonlocal)):
            Effects.add(type(Part).__name__.lower() + "_state")
        elif isinstance(Part, (ast.Yield, ast.YieldFrom, ast.Await, ast.AsyncFor, ast.AsyncWith)):
            Effects.add("suspension")
            Exits.add("suspension")
        elif isinstance(Part, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            Exits.add(type(Part).__name__.lower())
        elif isinstance(Part, (ast.Try, getattr(ast, "TryStar", ast.Try), ast.With, ast.AsyncWith, ast.Match)):
            Effects.add("python_control_boundary")
        elif isinstance(Part, (ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp)):
            Effects.add("numeric_or_overloaded_operation")
            Exits.add("exception")
        elif isinstance(Part, (ast.Import, ast.ImportFrom, ast.Delete)):
            Effects.add("binding_mutation")
    return tuple(sorted(Effects)), tuple(sorted(Exits))

def _Expressions(Node):
    Result = []
    for Part in _Parts(Node):
        if isinstance(Part, (ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.IfExp, ast.NamedExpr, ast.Call, ast.Subscript)):
            Evaluation = "short_circuit" if isinstance(Part, (ast.BoolOp, ast.IfExp, ast.Compare)) else "python_order"
            Result.append(_Expression_Plan(type(Part).__name__, _Location(Part), ast.unparse(Part), Evaluation))
    return tuple(sorted(Result, key=lambda Item: Item.Location))

def _Inventory(Tree):
    Entries, Parents = [], {}
    def Visit(Node, Scope, Function):
        if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            Scope = (*Scope, Node.name)
            Function = None if isinstance(Node, ast.ClassDef) else Node
        if isinstance(Node, _Loop_Types):
            Entries.append((Node, ".".join(Scope) if Function is not None else None, Function))
        for Child in ast.iter_child_nodes(Node):
            Parents[Child] = Node
            Visit(Child, Scope, Function)
    Visit(Tree, (), None)
    return Entries, Parents

def _Plan_For(Node, Function, Parents, Finding=None, Math_Calls=None):
    Defines, Uses = _Usage(Node)
    Targets = _Targets(Node.target) if isinstance(Node, (ast.For, ast.AsyncFor)) else set()
    if isinstance(Node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        Targets = set().union(*(_Targets(Clause.target) for Clause in Node.generators))
    Before = _Reads_Before_Definition(getattr(Node, "body", []), Targets)[0] if isinstance(getattr(Node, "body", None), list) else Uses
    Header = _Usage(Node.iter)[1] if isinstance(Node, (ast.For, ast.AsyncFor)) else _Usage(Node.test)[1] if isinstance(Node, ast.While) else Uses
    Inputs = tuple(sorted((Before | Header) - Targets))
    Carried = tuple(sorted((Defines & Before) - Targets))
    Scope = Function if Function is not None else Node
    End = (getattr(Node, "end_lineno", Node.lineno), getattr(Node, "end_col_offset", 0))
    Later = {Part.id for Part in _Parts(Scope) if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Load)
             and (getattr(Part, "lineno", 0), getattr(Part, "col_offset", 0)) >= End}
    Live_Out = tuple(sorted(Defines & Later))
    Reads, Writes = _Indexed(Node)
    Calls = _Calls(Node, Math_Calls or {})
    Effects, Exits = _Effects(Node)
    Blockers = list(_Dependencies(Node, Reads, Writes, Carried))
    if "suspension" in Effects:
        Blockers.append("Suspension preserves Python iterator, cancellation and frame-state behavior.")
    if "python_control_boundary" in Effects:
        Blockers.append("Exception, context-manager or pattern-matching boundaries require Python control flow.")
    if any(Item.Effect == "unknown" for Item in Calls):
        Blockers.append("Unknown calls are effect boundaries; preserve their original lookup and execution order.")
    if any(Item in Effects for Item in ("attribute_write", "global_state", "nonlocal_state")):
        Blockers.append("Observable attribute/global/nonlocal state needs explicit mutation and revalidation boundaries.")
    if isinstance(Node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        Blockers.append("Comprehension allocation, scope and iterator consumption retain Python semantics.")
    Serial = "python_retained"
    Parallel = "unproven"
    Guards = ["Preserve evaluation and exception order", "Validate mutable bindings and input types before native entry"]
    Adapter = "analysis_only"
    if Reads or Writes:
        Guards.extend(("Validate shape, layout, writability and every index bound", "Check overlapping array storage before reordering or parallel writes"))
    if Finding is not None:
        Guards.extend(Finding.Constraints)
        if Finding.Change != "Keep original loop":
            Serial = "guarded_candidate"
            Adapter = Finding.Classification
            Parallel = "guarded_candidate" if "OpenMP" in Finding.Change else "not_selected_by_this_plan"
        else:
            Blockers.insert(0, Finding.Reason)
        if Finding.Classification == "Loop_Carried_Dependency":
            Parallel = "rejected_dependency"
    if any("cross-iteration" in Item or "unique, bounded" in Item for Item in Blockers) and Parallel != "guarded_candidate":
        Parallel = "rejected_dependency"
    return _Analysis_Plan(_Plan_Version, type(Node).__name__, _Location(Node), _Shape(Node), _Blocks(Node), Inputs,
                          tuple(sorted(Defines)), Live_Out, Carried, tuple(ast.unparse(Item) for Item in Reads),
                          tuple(ast.unparse(Item) for Item in Writes), Calls, _Expressions(Node), _Facts(Function, Node, Inputs, Parents), Effects, Exits,
                          Serial, Parallel, tuple(dict.fromkeys(Guards)), tuple(dict.fromkeys(Blockers)), Adapter,
                          len(Node.generators) if isinstance(Node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)) else 1)

def _Attach_Common_Plans(Tree, Findings, Edits=None):
    from .Math_Registry import _Math_Calls
    Math_Calls = {(Item["Line"], Item["Column"] + 1): Item for Item in _Math_Calls(Tree)}
    Entries, Parents = _Inventory(Tree)
    By_Location = {}
    for Node, Scope, Function in Entries:
        By_Location.setdefault((Scope, Node.lineno, Node.end_lineno), []).append((Node, Function))
    Result = []
    for Finding in Findings:
        Matches = By_Location.get((Finding.Function, Finding.Line, Finding.End_Line), [])
        if not Matches:
            Result.append(Finding)
            continue
        Node, Function = Matches.pop(0)
        Result.append(replace(Finding, Plan=_Plan_For(Node, Function, Parents, Finding, Math_Calls)))
    return Result

def _Map_Adapter(Plan):
    Names = Plan.get("Kernel_Names", Plan["Names"])
    return _Map_Plan(_Plan_Version, "elementwise_map", len(Plan["Indices"]), len(Names), Names.index(Plan["Output"]),
                     tuple(Index for Index, Name in enumerate(Names) if Name in Plan["Arrays"]),
                     tuple(Index for Index, Name in enumerate(Names) if Name in Plan["Scalars"]), tuple(sorted(Plan["Reads"])),
                     tuple(Plan["Lines"]), ("dtype", "shape", "layout", "writability", "bounds", "aliasing", "arithmetic", "bindings"))

def _Map_Validate(Plan):
    Common = Plan.get("Common")
    if Common is None:
        Common = _Map_Adapter(Plan)
    if Common != _Map_Adapter(Plan):
        raise ValueError("Element-wise plan and common representation disagree; generation was stopped.")
    return Common

def _Capability_Matrix(Findings):
    Rows = []
    for Finding in Findings:
        Plan = getattr(Finding, "Plan", None)
        Rows.append(dict(Source=Finding.Source, Function=Finding.Function, Line=Finding.Line, End_Line=Finding.End_Line,
                         Analysis="covered" if Plan is not None else "native_source_or_unavailable", Classification=Finding.Classification,
                         Serial=Plan.Serial_Status if Plan is not None else "separate_native_contract",
                         Parallel=Plan.Parallel_Status if Plan is not None else "separate_native_contract",
                         Region="partial" if "region" in Finding.Change.lower() or "span" in Finding.Change.lower() else "whole_or_retained",
                         Reason=Finding.Reason, Native_Entry="not_observed_by_static_analysis",
                         Plan_Version=Plan.Version if Plan is not None else None,
                         Iteration_Clauses=Plan.Iteration_Clauses if Plan is not None else None))
    return tuple(Rows)
