import ast
import builtins
from .Direct_Bindings import _Builtin_Bindings

# Keep Python's binding rules even when Cython folds dead assignments or rejects deleted captures.
class _Scope_Index(_Builtin_Bindings):
    def __init__(self, Source, Prefix):
        super().__init__(Source, Prefix)
        self._Root = self._Scope
        self._Parents = {}
        self._Functions = {}
        self._References = {}
        self._Class = ''

    def _Global(self, Name):
        return False

    def visit_Global(self, Node):
        # Indexing must not remove declarations; the later builtin rewrite owns that mutation.
        return Node

    def _Child(self, Name, Line):
        Child = super()._Child(Name, Line)
        self._Parents[Child] = self._Scope
        return Child

    def visit_Name(self, Node):
        if any(Node.id in Names for Names in self._Comprehension_Locals):
            return Node
        Name = Node.id
        if self._Class and Name.startswith('__') and not Name.endswith('__'):
            Name = '_' + self._Class.lstrip('_') + Name
        try:
            Symbol = self._Scope.lookup(Name)
        except KeyError:
            return Node
        Owner = self._Scope
        if Symbol.is_global():
            Owner = self._Root
        elif Symbol.is_free():
            Owner = self._Parents.get(Owner)
            while Owner is not None:
                if Owner.get_type() == 'function' and Name in Owner.get_identifiers() and Owner.lookup(Name).is_local():
                    break
                Owner = self._Parents.get(Owner)
        self._References[Node] = (Owner, Name, self._Scope)
        return Node

    def _Definition(self, Node):
        Child = self._Child(Node.name, Node.lineno)
        Node.decorator_list = [self.visit(Value) for Value in Node.decorator_list]
        if isinstance(Node, ast.ClassDef):
            Node.bases = [self.visit(Value) for Value in Node.bases]
            Node.keywords = [self.visit(Value) for Value in Node.keywords]
        else:
            Node.args.defaults = [self.visit(Value) for Value in Node.args.defaults]
            Node.args.kw_defaults = [self.visit(Value) if Value is not None else None for Value in Node.args.kw_defaults]
            self._Functions[Node] = Child
        Previous, Class = self._Scope, self._Class
        self._Scope = Child
        if isinstance(Node, ast.ClassDef):
            self._Class = Node.name
        for Statement in Node.body:
            self.visit(Statement)
        self._Scope, self._Class = Previous, Class
        return Node

# Only deleted closure bindings use a sentinel; ordinary hot-path locals retain direct access.
class _Scope_Repair(ast.NodeTransformer):
    def __init__(self, Index, Prefix):
        self._Index, self._Prefix = Index, Prefix
        Captures = {(Owner, Name) for Owner, Name, Scope in Index._References.values() if Owner is not None and Owner is not Scope and Owner is not Index._Root}
        self._Deleted = {(Owner, Name) for Node, (Owner, Name, Scope) in Index._References.items() if isinstance(Node.ctx, ast.Del) and (Owner, Name) in Captures}
        Bound = {Symbol.get_name() for Symbol in Index._Root.get_symbols() if Symbol.is_assigned() or Symbol.is_imported() or Symbol.is_namespace()}
        self._Unknown = {Name for Owner, Name, Scope in Index._References.values() if Owner is Index._Root and Name not in Bound and Name not in vars(builtins) and not Name.startswith(Prefix)}

    def _Call(self, Name, Args):
        return ast.Call(func=ast.Name(id=self._Prefix + Name, ctx=ast.Load()), args=Args, keywords=[])

    def _Binding(self, Node):
        Item = self._Index._References.get(Node)
        return Item if Item is not None and Item[:2] in self._Deleted else None

    def _Read(self, Node, Item):
        Owner, Name, Scope = Item
        return self._Call('Direct_Cell_Value', [ast.Name(id=Node.id, ctx=ast.Load()), ast.Constant(Name), ast.Constant(Owner is not Scope)])

    def visit_Name(self, Node):
        if not isinstance(Node.ctx, ast.Load):
            return Node
        Item = self._Binding(Node)
        if Item:
            return ast.copy_location(self._Read(Node, Item), Node)
        Item = self._Index._References.get(Node)
        if Item and Item[0] is self._Index._Root and Item[1] in self._Unknown:
            return ast.copy_location(self._Call('Direct_Value', [self._Call('Direct_Globals', []), ast.Constant(Item[1])]), Node)
        return Node

    def visit_Delete(self, Node):
        # Split targets in order so a failed deletion leaves the same earlier mutations visible.
        Rows = []
        def Delete(Target):
            if isinstance(Target, (ast.Tuple, ast.List)):
                for Item in Target.elts:
                    Delete(Item)
                return
            Item = self._Binding(Target)
            if Item:
                Rows.append(ast.Expr(value=self._Read(Target, Item)))
                Rows.append(ast.Assign(targets=[ast.Name(id=Target.id, ctx=ast.Store())], value=ast.Name(id=self._Prefix + 'Direct_Empty', ctx=ast.Load())))
            else:
                Rows.append(ast.Delete(targets=[self.visit(Target)]))
        for Target in Node.targets:
            Delete(Target)
        return Rows

    def visit_AugAssign(self, Node):
        Item = self._Binding(Node.target)
        Node.value = self.visit(Node.value)
        if Item:
            return [ast.Expr(value=self._Read(Node.target, Item)), Node]
        Node.target = self.visit(Node.target)
        return Node

    def _Function(self, Node):
        Scope = self._Index._Functions[Node]
        self.generic_visit(Node)
        Body = Node.body
        Doc = []
        if Body and isinstance(Body[0], ast.Expr) and isinstance(Body[0].value, ast.Constant) and isinstance(Body[0].value.value, str):
            Doc, Body = Body[:1], Body[1:]
        Locals = [Symbol for Symbol in Scope.get_symbols() if Symbol.is_local() and not Symbol.is_parameter() and not Symbol.get_name().startswith(self._Prefix)]
        Names = [Symbol.get_name() for Symbol in Locals if (Scope, Symbol.get_name()) not in self._Deleted]
        Prelude = []
        # An opaque false branch establishes lexical locals without assigning them at runtime.
        if Names:
            Prelude.append(ast.If(test=self._Call('Direct_Unreachable', []), body=[ast.Assign(targets=[ast.Name(id=Name, ctx=ast.Store()) for Name in Names], value=ast.Constant(None))], orelse=[]))
        for Owner, Name in sorted(self._Deleted, key=lambda Item: Item[1]):
            if Owner is Scope and not Scope.lookup(Name).is_parameter():
                Prelude.append(ast.Assign(targets=[ast.Name(id=Name, ctx=ast.Store())], value=ast.Name(id=self._Prefix + 'Direct_Empty', ctx=ast.Load())))
        # Normalize errors in nested functions and methods as well as module-level functions.
        Error = self._Prefix + 'Unbound'
        Handler = ast.ExceptHandler(type=ast.Attribute(value=ast.Name(id=self._Prefix + 'Python_Builtins', ctx=ast.Load()), attr='UnboundLocalError', ctx=ast.Load()), name=Error, body=[ast.Expr(value=self._Call('Direct_Unbound', [ast.Name(id=Error, ctx=ast.Load())])), ast.Raise()])
        Node.body = Doc + Prelude + [ast.Try(body=Body or [ast.Pass()], handlers=[Handler], orelse=[], finalbody=[])]
        return Node

    def visit_FunctionDef(self, Node):
        return self._Function(Node)

    def visit_AsyncFunctionDef(self, Node):
        return self._Function(Node)

def _Direct_Scopes(Source, Prefix):
    Tree = ast.parse(Source)
    Index = _Scope_Index(Source, Prefix)
    Index.visit(Tree)
    return ast.unparse(ast.fix_missing_locations(_Scope_Repair(Index, Prefix).visit(Tree)))

def _Scope_Runtime(Prefix):
    # A sentinel preserves the shared closure variable, including later nonlocal rebinding.
    return [f'cdef object {Prefix}Direct_Empty = {Prefix}Python_Builtins.object()',
            f'cdef bint {Prefix}Direct_Unreachable():', '    return False',
            f'cdef object {Prefix}Direct_Cell_Value(object Value, str Name, bint Free):',
            f'    if Value is not {Prefix}Direct_Empty:', '        return Value',
            '    if Free:', f'        raise {Prefix}Python_Builtins.NameError("cannot access free variable " + {Prefix}Python_Builtins.repr(Name) + " where it is not associated with a value in enclosing scope", name=Name)',
            f'    raise {Prefix}Python_Builtins.UnboundLocalError("cannot access local variable " + {Prefix}Python_Builtins.repr(Name) + " where it is not associated with a value")']
