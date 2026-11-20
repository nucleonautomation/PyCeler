import ast
# Recognize supported builtin call shapes and generate runtime checks for their original bindings.
_Builtin_Numeric = {'abs': dict(Arity=1, Effect='pure_for_exact_numeric_types', Result='operand_numeric_kind', Identity='float_fresh_integer_sign_dependent')}

def _Builtin_Call(Node):
    if not isinstance(Node, ast.Call) or not isinstance(Node.func, ast.Name) or Node.keywords:
        return None
    Contract = _Builtin_Numeric.get(Node.func.id)
    return Node.func.id if Contract is not None and len(Node.args) == Contract['Arity'] else None

def _Builtin_Guards(Names, Prefix, Namespace='Source_Globals'):
    Lines = []
    for Name in Names:
        if Name not in _Builtin_Numeric:
            continue
        Lines.extend([f'if {Namespace}.get({Name!r}, B.__dict__.get({Name!r})) is not B.__dict__.get({Name!r}):', '    return None', f'Callable = B.__dict__.get({Name!r})', f'if B.type(Callable) is not {Prefix}Types.BuiltinFunctionType or Callable.__self__ is not B or Callable.__name__ != {Name!r}:', '    return None'])
    return Lines
