import ast
from .Common_Values import _Preceding_Value
# Prove affine index relationships using runtime integer parameters before permitting parallel writes.
def _Parameterized_Affine(Node, Index, Values, Parameters):
    if isinstance(Node, ast.Name) and Node.id in {Index, *Parameters}:
        return {Node.id: 1}
    Value = _Preceding_Value(Node, Values)
    if Value is not None:
        return _Parameterized_Affine(Value, Index, Values, Parameters)
    if isinstance(Node, ast.Constant) and type(Node.value) is int:
        return {'': Node.value}
    if isinstance(Node, ast.UnaryOp) and isinstance(Node.op, (ast.UAdd, ast.USub)):
        Result = _Parameterized_Affine(Node.operand, Index, Values, Parameters)
        return None if Result is None else {Name: -Value if isinstance(Node.op, ast.USub) else Value for Name, Value in Result.items()}
    if not isinstance(Node, ast.BinOp) or not isinstance(Node.op, (ast.Add, ast.Sub, ast.Mult)):
        return None
    Left = _Parameterized_Affine(Node.left, Index, Values, Parameters)
    Right = _Parameterized_Affine(Node.right, Index, Values, Parameters)
    if Left is None or Right is None:
        return None
    if isinstance(Node.op, ast.Mult):
        if set(Right) <= {''}:
            return {Name: Value * Right.get('', 0) for Name, Value in Left.items() if Value * Right.get('', 0)}
        if set(Left) <= {''}:
            return {Name: Value * Left.get('', 0) for Name, Value in Right.items() if Value * Left.get('', 0)}
        return None
    Sign = -1 if isinstance(Node.op, ast.Sub) else 1
    Result = {Name: Left.get(Name, 0) + Sign * Right.get(Name, 0) for Name in Left.keys() | Right.keys()}
    return {Name: Value for Name, Value in Result.items() if Value}

def _Shifted_Forms(Nodes, Plan, Values):
    Index = Plan['Index']
    Parameters = {Name for Name, Kind in Plan['Input_Types'].items() if Kind == 'integer' and Name not in Plan['Written']}
    Results = [_Parameterized_Affine(Node, Index, Values, Parameters) for Node in Nodes]
    if not Results or any(Result is None for Result in Results):
        return None
    Shifts = {tuple(sorted((Name, Value) for Name, Value in Result.items() if Name not in ('', Index))) for Result in Results}
    if len(Shifts) != 1:
        return None
    return [(Result.get(Index, 0), Result.get('', 0)) for Result in Results], Shifts.pop()
