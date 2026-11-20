import ast
# Bound random draws per iteration so speculative kernels can stage and replay RNG state exactly.
def _Random_Draw_Bounds(Node, Calls):
    if isinstance(Node, (list, tuple)):
        Values = [_Random_Draw_Bounds(Part, Calls) for Part in Node]
        return sum(Value[0] for Value in Values), sum(Value[1] for Value in Values)
    if isinstance(Node, ast.Call) and (Node.lineno, Node.col_offset) in Calls:
        return 1, 1
    if isinstance(Node, (ast.If, ast.IfExp)):
        Test = _Random_Draw_Bounds(Node.test, Calls)
        Yes = _Random_Draw_Bounds(Node.body, Calls)
        No = _Random_Draw_Bounds(Node.orelse, Calls)
        return Test[0] + min(Yes[0], No[0]), Test[1] + max(Yes[1], No[1])
    if isinstance(Node, ast.BoolOp):
        Values = [_Random_Draw_Bounds(Part, Calls) for Part in Node.values]
        return Values[0][0], sum(Value[1] for Value in Values)
    return _Random_Draw_Bounds(tuple(ast.iter_child_nodes(Node)), Calls)
