cdef str _Python_Module(str Source, str Native, object File, str Prefix):
    Source, Native = _Dispatch_Instrument(Source, Native, Prefix)
    Source = re.sub(r"(?m)^cdef object (" + re.escape(Prefix) + r"Original_\d+ = )", r"\1", Source)
    Tree = ast.parse(Source, filename=str(File))
    Calls = {Node.func.id for Node in ast.walk(Tree) if isinstance(Node, ast.Call) and isinstance(Node.func, ast.Name) and Node.func.id.startswith(Prefix)}
    for Name in Calls:
        Native = re.sub(r"(?m)^cdef (object|bint|int|void) (" + re.escape(Name) + r"\()", r"cpdef \1 \2", Native)
    Builtins = Prefix + "Python_Builtins"
    Execute = f"import builtins as {Builtins}\n{Builtins}.exec({Builtins}.compile({Source!r}, {str(File)!r}, 'exec', dont_inherit=True), globals())\n"
    return Native + "\n" + Execute
