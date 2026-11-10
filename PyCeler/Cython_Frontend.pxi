class _Cython_Static_Error(Exception):
    pass

cdef list _Cython_Children(object Node):
    Children = []
    for Attribute in getattr(Node, "child_attrs", ()):
        Value = getattr(Node, Attribute, None)
        if isinstance(Value, (list, tuple)):
            Children.extend(Item for Item in Value if hasattr(Item, "child_attrs"))
        elif hasattr(Value, "child_attrs"):
            Children.append(Value)
    return Children

cdef list _Cython_Tokens(str Text):
    from io import StringIO
    return list(tokenize.generate_tokens(StringIO(Text).readline))

cdef void _Cython_Preflight(object File, object Context, dict Sources, set Active) except *:
    from Cython.Compiler.Scanning import FileSourceDescriptor
    File = Path(File).resolve()
    if File in Active:
        raise _Cython_Static_Error(File, 1, "Recursive Cython includes require a finite include graph.")
    if File in Sources:
        return
    with tokenize.open(str(File)) as Stream:
        Text = Stream.read()
    Tokens = _Cython_Tokens(Text)
    Sources[File] = (Text, Tokens)
    Active.add(File)
    for Position, Token in enumerate(Tokens):
        if Token.type != tokenize.NAME:
            continue
        if Token.string in ("DEF", "IF", "ELIF", "ELSE"):
            raise _Cython_Static_Error(File, Token.start[0], "Cython compile-time expressions are preserved without evaluation during static analysis.")
        if Token.string == "include":
            Following = Tokens[Position + 1]
            if Following.type != tokenize.STRING:
                raise _Cython_Static_Error(File, Token.start[0], "A literal include path is required for read-only Cython analysis.")
            try:
                Name = ast.literal_eval(Following.string)
            except (ValueError, SyntaxError):
                raise _Cython_Static_Error(File, Token.start[0], "The Cython include path is not a supported literal string.")
            if not isinstance(Name, str):
                raise _Cython_Static_Error(File, Token.start[0], "The Cython include path must be a string.")
            Include = Context.find_include_file(Name, (FileSourceDescriptor(str(File)), *Token.start))
            if Include is None:
                raise _Cython_Static_Error(File, Token.start[0], f"Cython include {Name!r} was not found in the source context.")
            _Cython_Preflight(Include, Context, Sources, Active)
    Active.remove(File)

cdef object _Cython_Expression(object Node):
    if Node is None:
        return None
    Kind = type(Node).__name__
    if Kind == "NameNode":
        return str(Node.name)
    if Kind in ("IntNode", "FloatNode", "BoolNode"):
        return str(Node.value)
    if Kind in ("TupleNode", "ListNode"):
        Values = [_Cython_Expression(Item) for Item in Node.args]
        return ", ".join(Values) if all(Value is not None for Value in Values) else None
    if Kind == "IndexNode":
        Base, Index = _Cython_Expression(Node.base), _Cython_Expression(Node.index)
        return f"{Base}[{Index}]" if Base is not None and Index is not None else None
    if Kind == "AttributeNode":
        Base = _Cython_Expression(Node.obj)
        return f"{Base}.{Node.attribute}" if Base is not None else None
    if hasattr(Node, "operand1") and hasattr(Node, "operand2") and hasattr(Node, "operator"):
        Left, Right = _Cython_Expression(Node.operand1), _Cython_Expression(Node.operand2)
        return f"{Left} {Node.operator} {Right}" if Left is not None and Right is not None else None
    if hasattr(Node, "operand") and hasattr(Node, "operator"):
        Value = _Cython_Expression(Node.operand)
        return f"{Node.operator}{Value}" if Value is not None else None
    return None

cdef void _Cython_Accesses(object Node, list Reads, list Writes, bint Store=False) except *:
    Kind = type(Node).__name__
    if Kind in ("ForInStatNode", "ForFromStatNode", "WhileStatNode", "DefNode", "CFuncDefNode", "PyClassDefNode", "CClassDefNode"):
        return
    if Kind in ("SingleAssignmentNode", "InPlaceAssignmentNode"):
        if Kind == "InPlaceAssignmentNode":
            _Cython_Accesses(Node.lhs, Reads, Writes)
        _Cython_Accesses(Node.lhs, Reads, Writes, True)
        _Cython_Accesses(Node.rhs, Reads, Writes)
        return
    if Kind == "CascadedAssignmentNode":
        for Target in Node.lhs_list:
            _Cython_Accesses(Target, Reads, Writes, True)
        _Cython_Accesses(Node.rhs, Reads, Writes)
        return
    if Kind == "IndexNode":
        Expression = _Cython_Expression(Node)
        if Expression is not None:
            (Writes if Store else Reads).append(Expression)
        _Cython_Accesses(Node.base, Reads, Writes)
        _Cython_Accesses(Node.index, Reads, Writes)
        return
    for Child in _Cython_Children(Node):
        _Cython_Accesses(Child, Reads, Writes, Store)

cdef str _Cython_Scope_Name(object Node):
    Name = getattr(Node, "name", None) or getattr(Node, "class_name", None)
    if Name:
        return str(Name)
    Declarator = getattr(Node, "declarator", None)
    while Declarator is not None:
        Name = getattr(Declarator, "name", None)
        if Name:
            return str(Name)
        Declarator = getattr(Declarator, "base", None)
    return "<anonymous>"

cdef int _Cython_End_Line(object Node, object File, dict Sources):
    Last = Node.pos[1]
    Pending = [Node]
    while Pending:
        Current = Pending.pop()
        Position = getattr(Current, "pos", None)
        if Position is not None and Path(Position[0].filename).resolve() == File:
            Last = max(Last, Position[1])
        Pending.extend(_Cython_Children(Current))
    if File in Sources:
        for Token in Sources[File][1]:
            if Token.type == tokenize.NEWLINE and Token.start[0] >= Last:
                return Token.start[0]
    return Last

cdef bint _Cython_Parallel_Loop(object Node):
    Iterator = getattr(Node, "iterator", None)
    Call = getattr(Iterator, "sequence", None)
    Function = _Cython_Expression(getattr(Call, "function", None))
    return Function in ("prange", "cython.parallel.prange")

cdef void _Cython_Find_Loops(object Node, tuple Scope, object Function, list Findings, dict Sources) except *:
    Kind = type(Node).__name__
    if Kind in ("DefNode", "CFuncDefNode", "PyClassDefNode", "CClassDefNode"):
        Scope = (*Scope, _Cython_Scope_Name(Node))
        Function = None if Kind in ("PyClassDefNode", "CClassDefNode") else Node
    if Kind in ("ForInStatNode", "ForFromStatNode", "WhileStatNode"):
        File = Path(Node.pos[0].filename).resolve()
        Reads, Writes = [], []
        _Cython_Accesses(Node.body, Reads, Writes)
        Classification = "Cython_Loop"
        Reason = "Native Cython loop retained; its declared types, directives, exception behavior and dependencies require a native-semantics proof before rewriting."
        if Kind == "WhileStatNode":
            Reason = "Cython while loop retained; termination, native arithmetic and loop-carried state require separate qualification."
        elif _Cython_Parallel_Loop(Node):
            Classification = "Existing_OpenMP_Loop"
            Reason = "An existing prange call is retained with its original scheduling and directives; its binding and iteration independence are not inferred from the call name."
        Target = _Cython_Expression(getattr(Node, "target", None))
        if Target is not None:
            for Write in Writes:
                Tail = "[" + Target + "]"
                if Write.endswith(Tail) and Write[:-len(Tail)] + "[" + Target + " - 1]" in Reads:
                    Classification = "Loop_Carried_Dependency"
                    Reason = "An indexed read uses the preceding iteration's write; the Cython loop is preserved and independent parallel execution is ineligible."
                    break
        Findings.append(Loop_Finding(".".join(Scope) if Function is not None else None, Node.pos[1], _Cython_End_Line(Node, File, Sources),
                                     tuple(Reads), tuple(Writes), Classification, Reason, "Keep original Cython loop", str(File)))
    for Child in _Cython_Children(Node):
        _Cython_Find_Loops(Child, Scope, Function, Findings, Sources)

cdef tuple _Cython_Plan(object File, str Text):
    try:
        from Cython.Compiler import Errors
        from Cython.Compiler.Main import Context, CompilationOptions, default_options
        from Cython.Compiler.Scanning import FileSourceDescriptor
        from Cython.Compiler.Symtab import ModuleScope
    except ImportError as Error:
        raise RuntimeError("Cython is required to analyze .pyx and .pxi sources") from Error
    Options = CompilationOptions(default_options, language_level=3, include_path=[str(File.parent)])
    Context = Context.from_options(Options)
    Sources = {}
    Findings = []
    try:
        with Errors.local_errors(ignore=True) as Diagnostics:
            _Cython_Preflight(File, Context, Sources, set())
            Scope = ModuleScope(File.stem, parent_module=None, context=Context)
            Tree = Context.parse(FileSourceDescriptor(str(File)), Scope, False, File.stem)
            if Diagnostics:
                raise Diagnostics[0]
    except _Cython_Static_Error as Error:
        Source, Line, Reason = Error.args
        Findings.append(Loop_Finding(None, Line, Line, (), (), "Cython_Static_Unsupported", Reason, "Keep original Cython source", str(Source)))
        return Text, Findings, {}, None
    except (Errors.CompileError, IndentationError, tokenize.TokenError) as Error:
        Position = getattr(Error, "position", None)
        Line = Position[1] if Position else getattr(Error, "lineno", 1) or 1
        if File.suffix == ".pxi":
            Reason = "This include could not be parsed standalone; analyze its owning .pyx to supply context, or check the include syntax. " + str(Error)
            Findings.append(Loop_Finding(None, Line, Line, (), (), "Cython_Context_Required", Reason, "Keep original Cython include", str(File)))
            return Text, Findings, {}, None
        raise SyntaxError(f"Unable to parse Cython source {File}: {Error}") from Error
    _Cython_Find_Loops(Tree, (), None, Findings, Sources)
    from .Native_Optimizer import _Plans as _Native_Plans, _Findings as _Native_Findings
    Findings = _Native_Findings(Findings, _Native_Plans(Text, File))
    return Text, Findings, {}, None
