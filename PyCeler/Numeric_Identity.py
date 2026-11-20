import ast
# Track object origins so numeric list optimization preserves observable identity relationships.
def _Identity(Node, Kind, Source=None):
    if Source is not None and not any(isinstance(Part, (ast.Name, ast.Subscript, ast.Call)) for Part in ast.walk(Source)):
        return ('cached',) if Node[0] == 'literal' and Kind in ('integer', 'boolean') and -5 <= Node[1] <= 256 else ('unknown',)
    Operation = Node[0]
    if Operation == 'helper':
        return ('fresh',)
    if Operation == 'local':
        return ('reuse', Node[1])
    if Operation == 'literal':
        return ('cached',) if Kind in ('integer', 'boolean') and -5 <= Node[1] <= 256 else ('unknown',)
    if Operation == 'absolute':
        Operand = _Identity(Node[1], 'integer', Source.args[0] if isinstance(Source, ast.Call) else None)
        return ('fresh',) if Kind == 'float' or Operand[0] in ('fresh', 'cached') else ('unknown',)
    if Operation == 'conditional':
        Left = _Identity(Node[2], Kind, Source.body if isinstance(Source, ast.IfExp) else None)
        Right = _Identity(Node[3], Kind, Source.orelse if isinstance(Source, ast.IfExp) else None)
        return Left if Left == Right else ('unknown',)
    if Operation in ('arithmetic', 'checked_integer', 'integer_negative', 'negative', 'python_power', 'call', 'dimension', 'dimension_path'):
        return ('fresh',)
    return ('unknown',)

def _Identity_Emit(Recipe, Target, Lines, Indent):
    if Recipe[0] == 'fresh':
        Lines.extend([Indent + 'if Sequence[0] > <long long>9223372036854775807 - Sequence[1]:', Indent + '    Valid[0] = False', Indent + '    return 0.0', Indent + 'Sequence[0] += Sequence[1]', Indent + Target + ' = Sequence[0]'])
    else:
        Value = f'Origins[{Recipe[1]}]' if Recipe[0] == 'reuse' else '-1' if Recipe[0] == 'cached' else '0'
        Lines.append(Indent + Target + ' = ' + Value)
