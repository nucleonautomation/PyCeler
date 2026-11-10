import io
import json
import os
import re
import shutil
import tokenize
from pathlib import Path

def _Source_Inputs(Source_Path):
    Source = Path(Source_Path).resolve(strict=True)
    if Source.is_file():
        if Source.suffix not in (".py", ".pyx", ".pxi"):
            raise ValueError("Expected a .py, .pyx or .pxi source file")
        Root = Source.parent.parent if Source.stem == "__init__" else Source.parent
        return Source, Root, [Source]
    if not Source.is_dir():
        raise ValueError("Expected a source file or directory")
    Files = sorted(File for File in Source.rglob("*") if File.is_file() and File.suffix in (".py", ".pyx"))
    if not Files:
        raise ValueError("No .py or .pyx modules found; select a .pxi file explicitly or provide its owning module")
    Modules = {}
    for File in Files:
        Key = os.path.normcase(str(File.relative_to(Source).with_suffix("")))
        if Key in Modules:
            raise ValueError(f"Ambiguous module sources: {Modules[Key]} and {File}; select one file explicitly")
        Modules[Key] = File
        if not File.resolve().is_relative_to(Source):
            raise ValueError(f"Source link leaves the input tree: {File}")
    Root = Source.parent if any((Source / ("__init__" + Suffix)).is_file() for Suffix in (".py", ".pyx")) else Source
    return Source, Root, Files

def _Read_Source(File):
    with tokenize.open(str(File)) as Stream:
        return Stream.read()

def _Resolve_Dependency(Name, File, Root, Required=False):
    Candidate = Path(Name)
    if Candidate.is_absolute():
        raise ValueError(f"Absolute source dependency is not isolated: {Name} in {File}")
    for Parent in dict.fromkeys((File.parent, Root)):
        Found = (Parent / Candidate).resolve()
        if Found.is_file():
            if not Found.is_relative_to(Root):
                raise ValueError(f"Dependency {Found} is outside source root {Root}; select an enclosing source directory")
            return Found
    if Required:
        raise FileNotFoundError(f"Cannot find local include {Name!r} required by {File}")
    return None

def _Cimport_Dependencies(Name, File, Root):
    Relative = len(Name) - len(Name.lstrip("."))
    Module = Name.lstrip(".").replace(".", "/")
    if Relative:
        Parent = File.parent
        for Level in range(Relative - 1):
            Parent = Parent.parent
        Parents = (Parent,)
    else:
        Parents = tuple(dict.fromkeys((File.parent, Root)))
    for Parent in Parents:
        Stem = Parent / Module
        for Candidate in (Stem.with_suffix(".pxd"), Stem / "__init__.pxd") if Module else (Parent / "__init__.pxd",):
            Found = Candidate.resolve()
            if Found.is_file():
                if not Found.is_relative_to(Root):
                    raise ValueError(f"Cimport dependency {Found} is outside source root {Root}; select an enclosing source directory")
                yield Found

def _Dependencies(File, Root):
    Text = _Read_Source(File) if File.suffix in (".py", ".pyx", ".pxi", ".pxd") else File.read_text(encoding="utf-8", errors="replace")
    if File.suffix in (".py", ".pyx", ".pxi", ".pxd"):
        for Statement in _Dependency_Statements(Text):
            if len(Statement) >= 2 and Statement[0] == "include":
                Name = _Literal_Dependency(Statement[1])
                if Name is not None:
                    yield _Resolve_Dependency(Name, File, Root, True)
            if Statement[:3] == ["cdef", "extern", "from"] and len(Statement) >= 4:
                Name = _Literal_Dependency(Statement[3])
                Header = _Resolve_Dependency(Name, File, Root) if Name is not None else None
                if Header is not None:
                    yield Header
            if "cimport" not in Statement:
                continue
            Position = Statement.index("cimport")
            Prefix = "".join(Statement[1:Position]) if Statement[0] == "from" else ""
            if Prefix:
                yield from _Cimport_Dependencies(Prefix, File, Root)
            Names = " ".join(Statement[Position + 1:]).strip(" ()").split(",")
            for Item in Names:
                Name = Item.split(" as ")[0].replace(" ", "")
                if re.fullmatch(r"\.*[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", Name):
                    Name = Prefix + ("" if Prefix.endswith(".") else ".") + Name if Prefix else Name
                    yield from _Cimport_Dependencies(Name, File, Root)
        Sibling = File.with_suffix(".pxd")
        if File.suffix in (".py", ".pyx") and Sibling.is_file():
            yield Sibling.resolve()
        return
    for Match in re.finditer(r'(?m)^\s*#\s*include\s*(["])([^"\r\n]+)\1', Text):
        Header = _Resolve_Dependency(Match[2], File, Root)
        if Header is not None:
            yield Header

def _Literal_Dependency(Value):
    import ast
    try:
        Literal = ast.literal_eval(Value)
    except (SyntaxError, ValueError):
        return None
    return Literal if isinstance(Literal, str) else None

def _Dependency_Statements(Text):
    Statement = []
    try:
        for Token in tokenize.generate_tokens(io.StringIO(Text).readline):
            if Token.type in (tokenize.NEWLINE, tokenize.ENDMARKER) or Token.string == ";":
                if Statement:
                    yield Statement
                Statement = []
            elif Token.type not in (tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT, tokenize.ENCODING):
                Statement.append(Token.string)
    except (tokenize.TokenError, IndentationError):
        if Statement:
            yield Statement

def _Stage_Dependencies(Root, Files, Staging):
    Root = Path(Root).resolve()
    Pending = [Path(File).resolve() for File in Files]
    Inputs = set(Pending)
    Seen = set()
    Supporting = []
    while Pending:
        File = Pending.pop()
        if File in Seen:
            continue
        Seen.add(File)
        if not File.is_relative_to(Root):
            raise ValueError(f"Source dependency leaves the input tree: {File}")
        Pending.extend(_Dependencies(File, Root))
        if File in Inputs:
            continue
        Relative = File.relative_to(Root)
        Target = Staging / Relative
        Target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(File, Target)
        Supporting.append(Relative)
    return sorted(Supporting)

def _Stage_Compile_Sources(Root, Files, Staging):
    Supporting = _Stage_Dependencies(Root, Files, Staging)
    Paths = []
    for File in Files:
        Relative = File.relative_to(Root)
        Target = Staging / Relative
        Target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(File, Target)
        if File.suffix == ".pxi":
            Relative = Relative.with_suffix(".pyx")
            (Staging / Relative).write_text("include " + json.dumps(File.name) + "\n", encoding="utf-8")
        Paths.append(Relative)
    return Paths, Supporting
