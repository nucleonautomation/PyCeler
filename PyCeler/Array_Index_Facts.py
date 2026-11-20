import ast
# Infer integer-index buffer roles and required padding for representative selection workloads.
def _Array_Index_Facts(Plan, Outer):
    Definitions = {}
    Indices = []
    def Walk(Value):
        if not isinstance(Value, tuple):
            return
        if Value and Value[0] == 'store':
            Definitions.setdefault(Value[1], []).append(Value[2])
        if Value and Value[0] == 'array_index':
            Indices.append(Value[1])
        for Part in Value:
            Walk(Part)
    Walk(Plan['Program'])
    Buffers, Seen = set(), set()
    def Require(Value):
        if not isinstance(Value, tuple) or not Value:
            return
        if Value[0] == 'local' and Value[1] not in Seen:
            Seen.add(Value[1])
            for Definition in Definitions.get(Value[1], ()):
                Require(Definition)
        elif Value[0] == 'array_buffer':
            Buffers.add(Value[1])
        for Part in Value:
            Require(Part)
    for Value in Indices:  # Trace index dependencies through local assignments instead of guessing from variable names.
        Require(Value)
    Plan['Buffers'] = {Name: (Slot, Rank, 'integer' if Slot in Buffers else Kind) for Name, (Slot, Rank, Kind) in Plan['Buffers'].items()}
    Padding = {Name: [0] * Rank for Name, (Slot, Rank, Kind) in Plan['Buffers'].items()}
    for Node in ast.walk(Outer):
        if not isinstance(Node, ast.Subscript):
            continue
        Coordinates = []
        while isinstance(Node, ast.Subscript):
            Coordinates.insert(0, Node.slice)
            Node = Node.value
        if not isinstance(Node, ast.Name) or Node.id not in Padding or len(Coordinates) != len(Padding[Node.id]):
            continue
        for Axis, Value in enumerate(Coordinates):
            if isinstance(Value, ast.BinOp) and isinstance(Value.op, ast.Add) and isinstance(Value.right, ast.Constant) and type(Value.right.value) is int and 0 < Value.right.value <= 64:
                Padding[Node.id][Axis] = max(Padding[Node.id][Axis], Value.right.value)
    Plan['Array_Padding'] = {Name: tuple(Values) for Name, Values in Padding.items()}
