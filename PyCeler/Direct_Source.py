import ast
import copy
import re
from .Direct_Bindings import _Direct_Builtin_Bindings
from .Direct_Scopes import _Direct_Scopes, _Scope_Runtime
# Lower generated source fragments into editable definitions, avoiding runtime source-string execution.
class _Namespace_Names(ast.NodeTransformer):
    def __init__(self, Prefix):
        self._Prefix = Prefix

    def visit_Name(self, Node):
        if isinstance(Node.ctx, ast.Load):
            Result = ast.Call(func=ast.Name(id=self._Prefix + 'Direct_Value', ctx=ast.Load()), args=[ast.Name(id='Namespace', ctx=ast.Load()), ast.Constant(Node.id)], keywords=[])
        else:
            Result = ast.Subscript(value=ast.Name(id='Namespace', ctx=ast.Load()), slice=ast.Constant(Node.id), ctx=Node.ctx)
        return ast.copy_location(Result, Node)

    def visit_AugAssign(self, Node):
        if not isinstance(Node.target, ast.Name):
            return self.generic_visit(Node)
        Name = Node.target.id
        Temporary = self._Prefix + 'Augmented_Value'  # Read once and apply the actual in-place operation before publishing the replacement.
        Read = self.visit_Name(ast.Name(id=Name, ctx=ast.Load()))
        Target = self.visit_Name(ast.Name(id=Name, ctx=ast.Store()))
        return [ast.Assign(targets=[ast.Name(id=Temporary, ctx=ast.Store())], value=Read), ast.AugAssign(target=ast.Name(id=Temporary, ctx=ast.Store()), op=Node.op, value=self.visit(Node.value)), ast.Assign(targets=[Target], value=ast.Name(id=Temporary, ctx=ast.Load()))]

def _Namespace_Block(Name, Source, Mode='exec', Prefix='_Pyceler_'):
    Tree = ast.parse(Source, mode=Mode)
    Tree = _Namespace_Names(Prefix).visit(Tree)
    for Node in ast.walk(Tree):
        if isinstance(Node, (ast.For, ast.While)):
            Node.body.insert(0, ast.Expr(value=ast.Call(func=ast.Name(id=Prefix + 'Direct_Checkpoint', ctx=ast.Load()), args=[], keywords=[])))
    Body = [ast.Return(Tree.body)] if Mode == 'eval' else Tree.body
    Function = ast.parse(f'def {Name}(Namespace):\n    pass').body[0]
    Function.body = Body or [ast.Pass()]
    return ast.unparse(ast.fix_missing_locations(Function)) + '\n'

def _Literal_Constants(Source):
    Values = []
    for Node in ast.walk(ast.parse(Source)):
        if not isinstance(Node, (ast.Constant, ast.UnaryOp, ast.Tuple)):
            continue
        try:
            Value = ast.literal_eval(Node)
        except (ValueError, TypeError):
            continue
        if not any(type(Previous) is type(Value) and repr(Previous) == repr(Value) for Previous in Values):
            Values.append(Value)
    return ast.unparse(ast.Tuple(elts=[ast.Constant(Value) for Value in Values], ctx=ast.Load()))
# Expand nested baseline wrappers too; leaving one source string would break standalone readability.
def _Direct_Baselines(Text, Prefix):
    Lines = []
    Pattern = re.compile(r'^(\s*)(?:cdef object )?(\w+) = (.*)$')
    for Line in Text.splitlines():
        Match = Pattern.match(Line)
        if Match is None or Prefix + 'Baseline(' not in Match[3]:
            Lines.append(Line)
            continue
        Expression = ast.parse(Match[3], mode='eval')
        Calls = [Node for Node in ast.walk(Expression) if isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id == Prefix + 'Baseline']
        Replacements = {}
        for Position, Call in enumerate(Calls):
            Source = ast.literal_eval(Call.args[0])
            Functions = [Node for Node in ast.parse(Source).body if isinstance(Node, ast.FunctionDef)]
            Name = ast.literal_eval(Call.args[3]) if len(Call.args) > 3 else Functions[0].name
            Function = copy.deepcopy(next(Node for Node in Functions if Node.name == Name))
            Function.name = Match[2] if Call is Expression.body else Match[2] + '_Body_' + str(Position)  # Nested baseline wrappers need distinct callable names instead of embedded source.
            Function.decorator_list = []
            Rows = ast.unparse(ast.fix_missing_locations(Function)).splitlines()
            Rows.extend([f'{Function.name}.__builtins__ = {Prefix}Python_Builtins.__dict__', f'{Function.name}._Pyceler_Constants = {_Literal_Constants(Source)}'])
            Lines.extend(Match[1] + Row for Row in Rows)
            Replacements[Call] = ast.Name(id=Function.name, ctx=ast.Load())
        if Expression.body not in Replacements:
            class Replace(ast.NodeTransformer):
                def visit_Call(self, Node):
                    return Replacements.get(Node, self.generic_visit(Node))
            Lines.append(Match[1] + Match[2] + ' = ' + ast.unparse(Replace().visit(Expression)))
    return '\n'.join(Lines)
# Literal snippets are parsed during conversion and become ordinary callable definitions.
def _Direct_Compiled_Blocks(Native, Prefix):
    Lines = []
    Pattern = re.compile(r'^cdef object (\w+) = (?:\w+\.)?compile\((.*)\)$')
    for Line in Native.splitlines():
        Match = Pattern.match(Line)
        if Match is None:
            Lines.append(Line)
            continue
        Call = ast.parse('compile(' + Match[2] + ')', mode='eval').body
        Source, Mode = ast.literal_eval(Call.args[0]), ast.literal_eval(Call.args[2])
        Lines.append(_Namespace_Block(Match[1], Source, Mode, Prefix))
    Text = '\n'.join(Lines)
    Text = re.sub(r'\bB\.(?:exec|eval)\((\w+), Namespace\)', r'\1(Namespace)', Text)
    Text = re.sub(r'\bB\.eval\((\w+), dict\(Namespace, range=B.range, len=B.len\)\)', r'\1(dict(Namespace, range=B.range, len=B.len))', Text)
    return Text
# Normalize the Cython unbound-local message where callers observe exact exception arguments.
def _Direct_Function_Errors(Source, Prefix):
    Tree = ast.parse(Source)
    Lines = Source.splitlines()
    for Function in reversed([Node for Node in Tree.body if isinstance(Node, (ast.FunctionDef, ast.AsyncFunctionDef))]):
        Body = Function.body
        if isinstance(Body[0], ast.Expr) and isinstance(Body[0].value, ast.Constant) and isinstance(Body[0].value.value, str):
            Body = Body[1:]
        if not Body or Body[0].lineno == Function.lineno:
            continue
        Start, End = Body[0].lineno - 1, Function.end_lineno
        Indent = ' ' * Body[0].col_offset
        Rows = [Indent + 'try:', *('    ' + Row if Row.strip() else Row for Row in Lines[Start:End]), f'{Indent}except {Prefix}Python_Builtins.UnboundLocalError as {Prefix}Unbound:', f'{Indent}    {Prefix}Direct_Unbound({Prefix}Unbound)', Indent + '    raise']
        Lines[Start:End] = Rows
    return '\n'.join(Lines)
# Compiled Python-style loops still need cooperative signal handling and thread scheduling.
def _Direct_Checkpoints(Source, Prefix):
    Tree = ast.parse(Source)
    Lines = Source.splitlines()
    for Loop in sorted((Node for Node in ast.walk(Tree) if isinstance(Node, (ast.For, ast.While))), key=lambda Node: (Node.lineno, Node.col_offset), reverse=True):
        First = Loop.body[0]
        if First.lineno == Loop.lineno:
            Loop.body.insert(0, ast.Expr(value=ast.Call(func=ast.Name(id=Prefix + 'Direct_Checkpoint', ctx=ast.Load()), args=[], keywords=[])))
            Lines[Loop.lineno - 1:Loop.end_lineno] = [' ' * Loop.col_offset + Row for Row in ast.unparse(ast.fix_missing_locations(Loop)).splitlines()]
        else:
            Lines.insert(First.lineno - 1, ' ' * First.col_offset + Prefix + 'Direct_Checkpoint()')
    return '\n'.join(Lines)
# Preserve future imports and application definitions while placing native support code before use.
def _Direct_Module(Source, Native, File, Prefix):
    Source = re.sub(r'(?m)^cdef object (' + re.escape(Prefix) + r'Original_\d+ = )', r'\1', Source)
    Source, Native = _Direct_Baselines(Source, Prefix), _Direct_Baselines(Native, Prefix)
    Source = _Direct_Checkpoints(Source, Prefix)
    Native = _Direct_Compiled_Blocks(Native, Prefix)
    Tree = ast.parse(Source, filename=str(File))
    Lines = Source.splitlines()
    Header = []
    for Position, Node in enumerate(Tree.body):
        if isinstance(Node, ast.ImportFrom) and Node.module == '__future__' or Position == 0 and isinstance(Node, ast.Expr) and isinstance(Node.value, ast.Constant) and isinstance(Node.value.value, str):
            Header.append(ast.unparse(Node))
            Tail = Lines[Node.end_lineno - 1].encode('utf-8')[Node.end_col_offset:].decode('utf-8').lstrip()
            Lines[Node.lineno - 1:Node.end_lineno] = [''] * (Node.end_lineno - Node.lineno + 1)
            if Tail.startswith(';'):  # Moving a future import must not discard statements sharing its source line.
                Lines[Node.end_lineno - 1] = Tail[1:].lstrip()
    if Prefix + 'Helper_Originals' in Native:
        Names = set()
        Match = re.search(re.escape(Prefix) + r'Helper_Names = (.*)', Native)
        if Match:
            Names = set(ast.literal_eval(Match[1]))
        for Node in reversed(Tree.body):
            if isinstance(Node, ast.FunctionDef) and Node.name in Names:
                Lines.insert(Node.end_lineno, f'{Prefix}Helper_Originals[{Node.name!r}] = {Node.name}')
    Runtime = [f'import builtins as {Prefix}Python_Builtins', f'cdef void {Prefix}Direct_Unbound(object Error):', '    Text = str(Error)', '    if Text.startswith("local variable ") and Text.endswith(" referenced before assignment"):', '        Name = Text[len("local variable "):-len(" referenced before assignment")]', '        Error.args = ("cannot access local variable " + Name + " where it is not associated with a value",)', f'cdef object {Prefix}Direct_Value(dict Namespace, str Name):', '    if Name in Namespace:', '        return Namespace[Name]', f'    Builtins = Namespace.get("__builtins__", {Prefix}Python_Builtins)', '    if not isinstance(Builtins, dict):', '        Builtins = vars(Builtins)', '    if Name in Builtins:', '        return Builtins[Name]', '    raise NameError("name " + repr(Name) + " is not defined", name=Name)']
    Runtime = [Row.replace('str(Error)', Prefix + 'Python_Builtins.str(Error)').replace('len("', Prefix + 'Python_Builtins.len("').replace('isinstance(Builtins, dict)', Prefix + 'Python_Builtins.isinstance(Builtins, ' + Prefix + 'Python_Builtins.dict)').replace('vars(Builtins)', Prefix + 'Python_Builtins.vars(Builtins)').replace('raise NameError(', 'raise ' + Prefix + 'Python_Builtins.NameError(').replace('repr(Name)', Prefix + 'Python_Builtins.repr(Name)') for Row in Runtime]
    Runtime.extend([f'from cpython.exc cimport PyErr_CheckSignals as {Prefix}Direct_Signals', f'cdef unsigned int {Prefix}Direct_Ticks = 0', f'cdef void {Prefix}Direct_Checkpoint() except *:', f'    global {Prefix}Direct_Ticks', f'    {Prefix}Direct_Ticks += 1', f'    if {Prefix}Direct_Ticks & 1023 == 0:', f'        {Prefix}Direct_Signals()', '        with nogil:', '            pass'])
    Runtime.extend([f'cdef dict {Prefix}Direct_Globals():', '    return globals()'])
    Runtime.extend([f'cdef object {Prefix}Direct_Set_Global(str Name, object Value):', '    globals()[Name] = Value', '    return Value'])
    Runtime.extend(_Scope_Runtime(Prefix))
    Source = _Direct_Builtin_Bindings(_Direct_Scopes('\n'.join(Lines), Prefix), Prefix)
    return '\n'.join([*Header, *Runtime, Native, f'{Prefix}Direct_Application_Begin = None', Source]) + '\n'
