import ast
import symtable
# Use Python symbol tables to distinguish locals, captures, globals and class-mangled names.
def _Function_Scopes(Tree, Text=None):
    Definitions = [Node for Node in ast.walk(Tree) if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    if Text is None:
        Text = ast.unparse(Tree)
        Normal = [Node for Node in ast.walk(ast.parse(Text)) if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    else:
        Normal = Definitions
    if len(Normal) != len(Definitions) or any(type(Left) is not type(Right) or Left.name != Right.name for Left, Right in zip(Normal, Definitions)):  # Reject mismatched AST/symbol-table mappings rather than binding the wrong scope.
        raise ValueError('Scope source and syntax tree disagree')
    Nodes = {('class' if isinstance(New, ast.ClassDef) else 'function', New.lineno, New.name): Old for New, Old in zip(Normal, Definitions)}
    Result = []
    def Visit(Table, Scope, Class):
        Kind, Name = str(Table.get_type()), Table.get_name()
        Node = Nodes.get((Kind, Table.get_lineno(), Name))
        if Node is not None:
            Scope = (*Scope, Name)
            if isinstance(Node, ast.ClassDef):
                Class = Name.lstrip('_')
            elif isinstance(Node, ast.FunctionDef):
                Raw = {Part.id for Part in ast.walk(Node) if isinstance(Part, ast.Name)}
                Raw.update(Part.arg for Part in ast.walk(Node) if isinstance(Part, ast.arg))
                Mapped = {Value: '_' + Class + Value if Class and Value.startswith('__') and not Value.endswith('__') and '.' not in Value else Value for Value in Raw}  # Python class-private names are mangled in symbol tables but retain source spellings in the AST.
                Free, Local, Global = set(Table.get_frees()), set(Table.get_locals()), set(Table.get_globals())
                Captures = frozenset(Raw for Raw, Symbol in Mapped.items() if Symbol in Free)
                Locals = frozenset(Local | {Raw for Raw, Symbol in Mapped.items() if Symbol in Local})
                Globals = {Raw: Symbol for Raw, Symbol in Mapped.items() if Symbol in Global}
                Result.append((Node, '.'.join(Scope), Captures, Locals, Globals))
        for Child in Table.get_children():
            Visit(Child, Scope, Class)
    Visit(symtable.symtable(Text, '<PyCeler scope analysis>', 'exec'), (), '')
    return tuple(Result)

def _Bind_Region_Scope(Plan, Scope, Captures, Locals, Globals, Available):
    Roots = {Root for Root, Name, Module in Plan['Math']['Bindings']} | set(Plan.get('Random', {}).values())
    Roots.update(Plan.get('Helper_Roots', ()))
    Roots.difference_update(Plan.get('Helper_Globals', ()))
    Used = {Node.id for Loop in Plan['Loops'] for Node in ast.walk(Loop) if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Load)}
    Roots.update({'len', 'range'} & Used)
    if ((Roots | set(Plan['Names']) | set(Plan['Builtins'])) & set(Locals)) - set(Available):
        return False
    Plan['Scope'] = Scope
    Plan['Global_Names'] = dict(Globals)
    Plan['Captured_Inputs'] = tuple(sorted((set(Plan['Names']) | set(Plan['Output_Guards']) | Roots) & set(Captures)))
    Plan['Local_Bindings'] = tuple(sorted(set(Plan['Local_Bindings']) | (Roots & set(Captures))))
    if 'Alternate' in Plan:
        if not _Bind_Region_Scope(Plan['Alternate'], Scope, Captures, Locals, Globals, Available):
            return False
    return True

def _Scope_Error_Declaration(Prefix):
    return '\n'.join([f'from cpython.object cimport PyObject as {Prefix}Object', 'cdef extern from "Python.h":', f'    {Prefix}Object* {Prefix}Name_Error_Type "PyExc_NameError"', f'{Prefix}Name_Error = <object>{Prefix}Name_Error_Type'])
