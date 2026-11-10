cdef object _Exact_Read(object Function):
    if not isinstance(Function, ast.FunctionDef) or Function.decorator_list or getattr(Function, "type_params", ()):
        return None
    Args = Function.args
    Names = tuple(Arg.arg for Arg in Args.posonlyargs + Args.args)
    Body = Function.body[1:] if ast.get_docstring(Function, clean=False) is not None else Function.body
    if len(Names) != 2 or Args.kwonlyargs or Args.vararg or Args.kwarg or len(Body) != 3:
        return None
    Init, Loop, End = Body
    if not isinstance(Init, ast.Assign) or len(Init.targets) != 1 or not isinstance(Init.targets[0], ast.Name) or not isinstance(Init.value, ast.Constant) or Init.value.value != b"":
        return None
    Data = Init.targets[0].id
    if not isinstance(End, ast.Return) or not _Name(End.value, Data) or not isinstance(Loop, ast.While) or Loop.orelse or len(Loop.body) != 3:
        return None
    Test = Loop.test
    if not isinstance(Test, ast.Compare) or len(Test.ops) != 1 or not isinstance(Test.ops[0], ast.Lt) or not isinstance(Test.comparators[0], ast.Name):
        return None
    Length = Test.left
    if not isinstance(Length, ast.Call) or not _Name(Length.func, "len") or Length.keywords or len(Length.args) != 1 or not _Name(Length.args[0], Data):
        return None
    Need = Test.comparators[0].id
    Read, Check, Append = Loop.body
    if isinstance(Read, ast.Try):
        if len(Read.body) != 1 or Read.orelse or Read.finalbody:
            return None
        for Handler in Read.handlers:
            if Handler.name or len(Handler.body) != 1:
                return None
            Type = Handler.type
            if Type is not None and not (_Name(Type, "Exception") or _Name(Type, "TimeoutError") or
                    (isinstance(Type, ast.Attribute) and Type.attr == "timeout" and _Name(Type.value, "socket"))):
                return None
            Action = Handler.body[0]
            if not ((isinstance(Action, ast.Raise) and Action.exc is None) or _Returns_None(Action)):
                return None
        Read = Read.body[0]
    if not isinstance(Read, ast.Assign) or len(Read.targets) != 1 or not isinstance(Read.targets[0], ast.Name):
        return None
    Chunk, Call = Read.targets[0].id, Read.value
    if not isinstance(Call, ast.Call) or Call.keywords or len(Call.args) != 1 or not isinstance(Call.func, ast.Attribute) or Call.func.attr != "recv" or not isinstance(Call.func.value, ast.Name):
        return None
    Socket, Amount = Call.func.value.id, Call.args[0]
    if not isinstance(Amount, ast.BinOp) or not isinstance(Amount.op, ast.Sub) or not _Name(Amount.left, Need) or ast.dump(Amount.right) != ast.dump(Length):
        return None
    if not isinstance(Check, ast.If) or Check.orelse or len(Check.body) != 1 or not _Returns_None(Check.body[0]) or not isinstance(Check.test, ast.UnaryOp) or not isinstance(Check.test.op, ast.Not) or not _Name(Check.test.operand, Chunk):
        return None
    if not isinstance(Append, ast.AugAssign) or not isinstance(Append.op, ast.Add) or not _Name(Append.target, Data) or not _Name(Append.value, Chunk):
        return None
    Variables = {Data, Chunk, Socket, Need}
    if (set(Names) != {Socket, Need} or len(Variables) != 4 or Variables & {"len", "socket", "Exception", "TimeoutError"} or
            any(Name.startswith("_Pyceler_") for Name in Variables)):
        return None
    return dict(Kind="receive", Names=Names, Key=Need, Output=Need, Start=Init.lineno, Loops=[Loop], Reader=Names.index(Socket),
                Loop=Loop, Length=Length, Data=Data, Chunk=Chunk)

cdef bint _Returns_None(object Node):
    return isinstance(Node, ast.Return) and (Node.value is None or (isinstance(Node.value, ast.Constant) and Node.value.value is None))

cdef str _Receive_Kernel(dict Plan, int Line):
    Loop = copy.deepcopy(Plan["Loop"])
    Length = ast.parse("_Pyceler_State.Length(_Pyceler_Base)", mode="eval").body
    Loop.test.left = Length
    Read = Loop.body[0]
    if isinstance(Read, ast.Try):
        Read = Read.body[0]
    Read.value.args[0].right = Length
    Loop.body[-1] = ast.parse(f"_Pyceler_State.Append({Plan['Chunk']})").body[0]
    Parameters = ", ".join("object " + Name for Name in Plan["Names"])
    Lines = [f"cdef object _Pyceler_Special_{Line}({Parameters}, object _Pyceler_Base, bint _Pyceler_Unused):",
             "    global socket, Exception, TimeoutError", "    cdef _Pyceler_Chunks _Pyceler_State = _Pyceler_Chunks()"]
    Lines.extend("    " + Part for Part in ast.unparse(Loop).splitlines())
    Lines.append("    return _Pyceler_State.Materialize()")
    return "\n".join(Lines)
