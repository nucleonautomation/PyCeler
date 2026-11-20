import ast
import re
# Test support/workload for generated source.
def _Python_Source(Text):
    Marker = re.search(r'(?m)^_Pyceler_X*Direct_Application_Begin = None\n', Text)
    if Marker is not None:
        return Text[Marker.end():]
    Sources = []
    for Line in Text.splitlines():
        if Line[:1].isspace() or ".exec(" not in Line:
            continue
        Tree = ast.parse(Line)
        for Node in ast.walk(Tree):
            if isinstance(Node, ast.Call) and isinstance(Node.func, ast.Attribute) and Node.func.attr == "compile" and Node.args:
                Value = Node.args[0]
                if isinstance(Value, ast.Constant) and type(Value.value) is str:
                    Sources.append(Value.value)
    if len(Sources) != 1:
        raise ValueError("Expected one embedded CPython module source")
    return Sources[0]
