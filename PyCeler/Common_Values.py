import ast
# Track observable outputs and stable scalar definitions across extracted region boundaries.
def _Live_Region_Outputs(Function, Outer, Written, Module):
    if Module or any(isinstance(Node, ast.Name) and Node.id == 'dir' for Node in ast.walk(Function)):
        return Written
    Start = (Outer.lineno, Outer.col_offset)
    End = (Outer.end_lineno, Outer.end_col_offset)
    Outside = {Node.id for Node in ast.walk(Function) if isinstance(Node, ast.Name) and not (Start <= (Node.lineno, Node.col_offset) and (Node.end_lineno, Node.end_col_offset) <= End)}
    return tuple(Name for Name in Written if Name in Outside)

def _Stable_Values(Statements):
    Stores = {}
    for Statement in Statements:
        for Node in ast.walk(Statement):
            if isinstance(Node, ast.Name) and isinstance(Node.ctx, (ast.Store, ast.Del)):
                Stores[Node.id] = Stores.get(Node.id, 0) + 1
    Values = {}
    for Statement in Statements:
        if isinstance(Statement, ast.Assign) and len(Statement.targets) == 1 and isinstance(Statement.targets[0], ast.Name):
            Name = Statement.targets[0].id
            if Stores[Name] == 1:
                Values[Name] = Statement.value, (Statement.end_lineno, Statement.end_col_offset)
    return Values

def _Preceding_Value(Node, Values):
    if not isinstance(Node, ast.Name) or Node.id not in Values:
        return None
    Value, End = Values[Node.id]
    return Value if End <= (Node.lineno, Node.col_offset) else None

def _Floating_Value(Node, Buffers, Values, Calls=()):
    if isinstance(Node, ast.Constant):
        return type(Node.value) is float
    if isinstance(Node, ast.Name):
        Value = _Preceding_Value(Node, Values)
        return Value is not None and _Floating_Value(Value, Buffers, Values, Calls)
    if isinstance(Node, ast.Call):
        return ast.unparse(Node.func) in Calls
    if isinstance(Node, ast.Subscript):
        while isinstance(Node, ast.Subscript):
            Node = Node.value
        return isinstance(Node, ast.Name) and Node.id in Buffers
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, (ast.UAdd, ast.USub)):
        return _Floating_Value(Node.operand, Buffers, Values, Calls)
    if isinstance(Node, ast.BinOp) and isinstance(Node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        return _Floating_Value(Node.left, Buffers, Values, Calls) or _Floating_Value(Node.right, Buffers, Values, Calls)
    return False

def _Real_Inputs(Outer, Inputs, Buffers, Carry, Calls=()):
    Values = _Stable_Values(Outer.body)
    Parents = {Child: Parent for Parent in ast.walk(Outer) for Child in ast.iter_child_nodes(Parent)}
    Result = []
    for Name in Inputs:
        if Name in Carry:
            continue
        Uses = [Node for Node in Parents if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Load) and Node.id == Name]
        Valid = bool(Uses)
        for Node in Uses:
            Parent = Parents[Node]
            if isinstance(Parent, ast.Call) and Node in Parent.args and ast.unparse(Parent.func) in Calls:
                continue
            if not isinstance(Parent, ast.BinOp) or not isinstance(Parent.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                Valid = False
                break
            Other = Parent.right if Node is Parent.left else Parent.left
            if not _Floating_Value(Other, Buffers, Values, Calls):
                Valid = False
                break
        if Valid:
            Result.append(Name)
    return tuple(Result)
