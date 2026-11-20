import ast
import builtins
import symtable
# Keep user-shadowed builtins separate from native helper bindings in a single compiled module.
class _Builtin_Bindings(ast.NodeTransformer):
    def __init__(self, Source, Prefix):
        self._Scope = symtable.symtable(Source, '<PyCeler direct bindings>', 'exec')
        self._Names = {Symbol.get_name() for Symbol in self._Scope.get_symbols() if not Symbol.get_name().startswith('_') and Symbol.get_name() in vars(builtins) and (Symbol.is_assigned() or Symbol.is_imported() or Symbol.is_namespace())}
        # Cython can bind zip/range/len and other builtins statically even when callers later replace module globals.
        # Frame-sensitive calls must retain Cython's handling of the current frame unless explicitly shadowed.
        Contextual = {'locals', 'globals', 'vars', 'dir', 'super', 'eval', 'exec'}
        def References(Scope):
            for Symbol in Scope.get_symbols():
                Name = Symbol.get_name()
                if Symbol.is_global() and Symbol.is_referenced() and Name in vars(builtins) and Name not in Contextual and not Name.startswith('_'):
                    self._Names.add(Name)
            for Child in Scope.get_children():
                References(Child)
        References(self._Scope)
        self._Prefix = Prefix
        self._Used = set()
        self._Comprehension_Locals = []

    def _Global(self, Name):
        if any(Name in Names for Names in self._Comprehension_Locals):
            return False
        if Name not in self._Names:
            return False
        try:
            return self._Scope.lookup(Name).is_global()
        except KeyError:
            return True

    def _Namespace(self):
        return ast.Call(func=ast.Name(id=self._Prefix + 'Direct_Globals', ctx=ast.Load()), args=[], keywords=[])

    def visit_Name(self, Node):
        if not self._Global(Node.id):
            return Node
        if isinstance(Node.ctx, ast.Load):
            Result = ast.Call(func=ast.Name(id=self._Prefix + 'Direct_Value', ctx=ast.Load()), args=[self._Namespace(), ast.Constant(Node.id)], keywords=[])
        else:
            Result = ast.Subscript(value=self._Namespace(), slice=ast.Constant(Node.id), ctx=Node.ctx)
        return ast.copy_location(Result, Node)

    def visit_Global(self, Node):
        Node.names = [Name for Name in Node.names if Name not in self._Names]
        return Node if Node.names else ast.copy_location(ast.Pass(), Node)

    def _Child(self, Name, Line):
        for Child in self._Scope.get_children():
            if Child not in self._Used and Child.get_name() == Name and Child.get_lineno() == Line:
                self._Used.add(Child)
                return Child
        raise ValueError(f'Cannot resolve direct Cython scope {Name!r} at line {Line}')

    def _Definition(self, Node):
        Name = Node.name
        Rename = self._Global(Name)
        Child = self._Child(Name, Node.lineno)
        Node.decorator_list = [self.visit(Value) for Value in Node.decorator_list]
        if isinstance(Node, ast.ClassDef):
            Node.bases = [self.visit(Value) for Value in Node.bases]
            Node.keywords = [self.visit(Value) for Value in Node.keywords]
        else:
            Node.args.defaults = [self.visit(Value) for Value in Node.args.defaults]
            Node.args.kw_defaults = [self.visit(Value) if Value is not None else None for Value in Node.args.kw_defaults]
        Previous = self._Scope
        self._Scope = Child
        Body = []
        for Statement in Node.body:
            Value = self.visit(Statement)
            Body.extend(Value if isinstance(Value, list) else [Value] if Value is not None else [])
        Node.body = Body
        self._Scope = Previous
        if not Rename:
            return Node
        Node.name = self._Prefix + 'User_' + Name
        Value = ast.Name(id=Node.name, ctx=ast.Load())
        Target = ast.Subscript(value=self._Namespace(), slice=ast.Constant(Name), ctx=ast.Store())
        Public_Name = ast.Assign(targets=[ast.Attribute(value=Value, attr='__name__', ctx=ast.Store())], value=ast.Constant(Name))
        return [Node, Public_Name, ast.Assign(targets=[Target], value=Value)]

    def visit_FunctionDef(self, Node):
        return self._Definition(Node)

    def visit_AsyncFunctionDef(self, Node):
        return self._Definition(Node)

    def visit_ClassDef(self, Node):
        return self._Definition(Node)

    def visit_Lambda(self, Node):
        Node.args.defaults = [self.visit(Value) for Value in Node.args.defaults]
        Node.args.kw_defaults = [self.visit(Value) if Value is not None else None for Value in Node.args.kw_defaults]
        Previous = self._Scope
        self._Scope = self._Child('lambda', Node.lineno)
        Node.body = self.visit(Node.body)
        self._Scope = Previous
        return Node

    def _Import(self, Node):
        Assignments = []
        for Alias in Node.names:
            Name = Alias.asname or Alias.name.split('.')[0]
            if self._Global(Name):
                Alias.asname = self._Prefix + 'User_' + Name
                Target = ast.Subscript(value=self._Namespace(), slice=ast.Constant(Name), ctx=ast.Store())
                Assignments.append(ast.Assign(targets=[Target], value=ast.Name(id=Alias.asname, ctx=ast.Load())))
        return [Node, *Assignments]

    def visit_Import(self, Node):
        return self._Import(Node)

    def visit_ImportFrom(self, Node):
        return self._Import(Node)

    def visit_NamedExpr(self, Node):
        if isinstance(Node.target, ast.Name) and self._Global(Node.target.id):
            return ast.Call(func=ast.Name(id=self._Prefix + 'Direct_Set_Global', ctx=ast.Load()), args=[ast.Constant(Node.target.id), self.visit(Node.value)], keywords=[])
        return self.generic_visit(Node)

    def _Comprehension(self, Node, Name):
        First = self.visit(Node.generators[0].iter)  # The outermost iterable belongs to the enclosing scope, not the comprehension locals.
        Previous = self._Scope
        if Name == 'genexpr' or any(Child.get_name() == Name and Child.get_lineno() == Node.lineno for Child in self._Scope.get_children()):  # Recent Python versions inline list/set/dict comprehensions and may omit a child table.
            self._Scope = self._Child(Name, Node.lineno)
        self._Comprehension_Locals.append({Value.id for Generator in Node.generators for Value in ast.walk(Generator.target) if isinstance(Value, ast.Name)})
        for Position, Generator in enumerate(Node.generators):
            Generator.iter = First if Position == 0 else self.visit(Generator.iter)
            Generator.ifs = [self.visit(Value) for Value in Generator.ifs]
        if isinstance(Node, ast.DictComp):
            Node.key, Node.value = self.visit(Node.key), self.visit(Node.value)
        else:
            Node.elt = self.visit(Node.elt)
        self._Scope = Previous
        self._Comprehension_Locals.pop()
        return Node

    def visit_ListComp(self, Node):
        return self._Comprehension(Node, 'listcomp')

    def visit_SetComp(self, Node):
        return self._Comprehension(Node, 'setcomp')

    def visit_DictComp(self, Node):
        return self._Comprehension(Node, 'dictcomp')

    def visit_GeneratorExp(self, Node):
        return self._Comprehension(Node, 'genexpr')

def _Direct_Builtin_Bindings(Source, Prefix):
    Rewrite = _Builtin_Bindings(Source, Prefix)
    if not Rewrite._Names:
        return Source
    return ast.unparse(ast.fix_missing_locations(Rewrite.visit(ast.parse(Source))))
