cdef object _Scalar_Size_Operand(object Node, tuple Names):
    if isinstance(Node, ast.Name) and Node.id in Names:
        return True, Names.index(Node.id)
    Sign = 1
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, (ast.USub, ast.UAdd)):
        Sign = -1 if isinstance(Node.op, ast.USub) else 1
        Node = Node.operand
    if isinstance(Node, ast.Constant) and type(Node.value) is int:
        return False, Sign * Node.value
    return None

cdef set _Scalar_Size_Overwritten(object Function, object Loop):
    if Function is None:
        return set()
    Parents, Stores, Pending = {}, [], [Function]
    while Pending:
        Node = Pending.pop()
        if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Store):
            Stores.append(Node)
        for Child in ast.iter_child_nodes(Node):
            if isinstance(Child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            Parents[Child] = Node
            Pending.append(Child)
    Boundary = (Loop.lineno, Loop.col_offset)
    Changed = {Node.id for Node in Stores if (Node.lineno, Node.col_offset) < Boundary}
    Parent = Parents.get(Loop)
    while Parent is not None:
        if isinstance(Parent, (ast.For, ast.While)):
            Changed.update(Node.id for Node in ast.walk(Parent) if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Store))
        Parent = Parents.get(Parent)
    return Changed

def _Scalar_Size_Plan(Plan):
    Names = Plan["Names"]
    Ranges, Bounds, Arguments, Vary = [], [], [], []
    Parent = None
    Complete = True
    Overwritten = set()
    for Loop in Plan["Loops"]:
        if Parent is not None and Loop not in Parent.body:
            Complete = False
            break
        if isinstance(Loop, ast.For):
            Call = Loop.iter
            if not isinstance(Call, ast.Call) or not _Name(Call.func, "range") or not 1 <= len(Call.args) <= 3:
                Complete = False
                break
            Start = (False, 0) if len(Call.args) == 1 else _Scalar_Size_Operand(Call.args[0], Names)
            Stop = _Scalar_Size_Operand(Call.args[0 if len(Call.args) == 1 else 1], Names)
            Step = (False, 1) if len(Call.args) < 3 else _Scalar_Size_Operand(Call.args[2], Names)
            if Start is None or Stop is None or Step is None or not Step[0] and not Step[1]:
                Complete = False
                break
            Dependencies = {Names[Operand[1]] for Operand in (Start, Stop, Step) if Operand[0]}
            Overwritten = Dependencies & _Scalar_Size_Overwritten(Plan.get("Size_Function"), Loop)
            if Overwritten:
                Complete = False
                break
            Ranges.append((*Start, *Stop, Step if Step[0] else Step[1]))
            for Operand in (Start, Stop, Step):
                if Operand[0] and Operand[1] not in Arguments:
                    Arguments.append(Operand[1])
            Slot = Stop[1] if Stop[0] else Start[1] if Start[0] else None
            if Slot is not None and Slot not in Vary:
                Vary.append(Slot)
            if any(isinstance(Part, (ast.Break, ast.Return, ast.Raise)) for Part in ast.walk(Loop)):
                Complete = False
        elif isinstance(Loop, ast.While):
            Test = Loop.test
            if not isinstance(Test, ast.Compare) or len(Test.ops) != 1:
                Complete = False
                break
            Dependencies = [Part.id for Part in (Test.comparators[0], Test.left) if isinstance(Part, ast.Name) and Part.id in Names]
            if not Dependencies:
                Complete = False
                break
            Overwritten = set(Dependencies) & _Scalar_Size_Overwritten(Plan.get("Size_Function"), Loop)
            if Overwritten:
                Complete = False
                break
            Slot = Names.index(Dependencies[0])
            Bounds.append(Slot)
            if Slot not in Arguments:
                Arguments.append(Slot)
            if Slot not in Vary:
                Vary.append(Slot)
            Complete = False
        else:
            Complete = False
            break
        Parent = Loop
    if Overwritten:
        Reason = "Only previously proven outer bounds are used; input bounds assigned before this loop or inside an enclosing loop cannot be sized from their original arguments: " + ", ".join(sorted(Overwritten)) + "."
    elif not Ranges and not Bounds:
        Reason = "No direct input-dependent range or comparison bound; use one fixed-workload band without guessing an argument."
    elif Complete:
        Reason = "Exact product of rectangular range lengths, including start offsets and snapshotted integer steps."
    else:
        Reason = "Range lengths and explicit comparison bounds estimate the outer workload; data-dependent inner work is not an exact iteration count."
    return dict(Ranges=Ranges, Bounds=Bounds, Arguments=Arguments, Vary=Vary, Exact=Complete and not Bounds, Reason=Reason, Overwritten_Arguments=sorted(Overwritten))

cdef str _Scalar_Size_Probe(dict Plan, tuple Names, str Prefix):
    Sizing = _Scalar_Size_Plan(Plan)
    Args = "(" + ", ".join(Names) + ("," if Names else "") + ")"
    return f"({Prefix}Scalar_Size({Args}, {tuple(Sizing['Ranges'])!r}, {tuple(Sizing['Bounds'])!r}),)"

def _Scalar_Workload_Size(Sizing, Args):
    Size = 1
    for Start_Argument, Start, Stop_Argument, Stop, Step in Sizing["Ranges"]:
        Begin = Args[Start] if Start_Argument else Start
        End = Args[Stop] if Stop_Argument else Stop
        Step = Args[Step[1]] if isinstance(Step, (tuple, list)) else Step
        if type(Begin) is not int or type(End) is not int or type(Step) is not int or Step == 0:
            return 0
        Count = max(0, (End - Begin + Step - 1) // Step) if Step > 0 else max(0, (Begin - End - Step - 1) // -Step)
        Size *= Count
    for Slot in Sizing["Bounds"]:
        Bound = Args[Slot]
        if type(Bound) is not int:
            return 0
        Size *= max(0, Bound)
    return Size

def _Scalar_Size_Cases(Item):
    Sizing = Item["Size_Plan"]
    Depth = sum((Start_Argument or Stop_Argument) and not (Start_Argument and Stop_Argument and Start == Stop)
                for Start_Argument, Start, Stop_Argument, Stop, Step in Sizing["Ranges"]) + len(Sizing["Bounds"])
    Targets = sorted({max(1, round(Target ** (1 / Depth))) for Target in (16, 1024, 36864)}) if Depth > 1 else [4, 256, 32768] if Depth else [1]
    Seen = set()
    for Count in Targets:
        Args = [2] * Item["Arguments"]
        for Start_Argument, Start, Stop_Argument, Stop, Step in Sizing["Ranges"]:
            Step = Args[Step[1]] if isinstance(Step, (tuple, list)) else Step
            if Stop_Argument and not (Start_Argument and Start == Stop):
                Begin = Args[Start] if Start_Argument else Start
                Args[Stop] = Begin + Count * Step
            elif Start_Argument and not Stop_Argument:
                Args[Start] = Stop - Count * Step
        for Slot in Sizing["Bounds"]:
            Args[Slot] = Count
        Args = tuple(Args)
        if Args in Seen:
            continue
        Seen.add(Args)
        yield "int", _Scalar_Workload_Size(Sizing, Args), (), Args

cdef str _Scalar_Sizing_Runtime = """cdef object _Pyceler_Scalar_Size(tuple Args, tuple Ranges, tuple Bounds):
    import builtins as B
    Size = 1
    for Start_Argument, Start, Stop_Argument, Stop, Step in Ranges:
        Begin = Args[Start] if Start_Argument else Start
        End = Args[Stop] if Stop_Argument else Stop
        Step = Args[Step[1]] if B.isinstance(Step, (B.tuple, B.list)) else Step
        if B.type(Begin) is not B.int or B.type(End) is not B.int or B.type(Step) is not B.int or Step == 0:
            return 0
        if Step > 0:
            Count = (End - Begin + Step - 1) // Step if End > Begin else 0
        else:
            Count = (Begin - End - Step - 1) // -Step if Begin > End else 0
        Size *= Count
    for Slot in Bounds:
        Bound = Args[Slot]
        if B.type(Bound) is not B.int:
            return 0
        Size *= Bound if Bound > 0 else 0
    return Size
"""
