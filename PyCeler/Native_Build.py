import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def _Workspace():
    Root = Path(os.environ.get("PYCELER_BUILD_DIR", Path.cwd() / "Build")).resolve()
    Root.mkdir(parents=True, exist_ok=True)
    with _Temporary_Workspace(Root) as Folder:
        yield Folder

@contextmanager
def _Temporary_Workspace(Root):
    Workspace = tempfile.TemporaryDirectory(prefix="PyCeler_", dir=Root)
    try:
        yield Path(Workspace.name)
    finally:
        _Cleanup_Workspace(Workspace)

def _Cleanup_Workspace(Workspace):
    for Attempt in range(7):
        try:
            Workspace.cleanup()
            return
        except PermissionError:
            if os.name != "nt" or Attempt == 6:
                raise
            time.sleep(0.05 * 2 ** Attempt)

@contextmanager
def _Publication(Output):
    Output.mkdir(parents=True, exist_ok=True)
    Lock = Output / ".PyCeler_Publish"
    try:
        Lock.mkdir()
    except FileExistsError as Error:
        raise RuntimeError(f"Output is being published: {Lock}") from Error
    try:
        yield
    finally:
        Lock.rmdir()

def _Publish(Stage, Output, Paths, Native_Sources=(), Report_Sources=()):
    with _Publication(Output):
        if Native_Sources:
            _Check_Layout(Stage, Output, Paths, Native_Sources)
        Stale = []
        for Source in Report_Sources:
            Relative = Source.with_suffix(".selection.json")
            if Relative not in Paths and (Output / Relative).is_file():
                try:
                    Report = json.loads((Output / Relative).read_text(encoding="utf-8"))
                except (ValueError, UnicodeError):
                    continue
                if isinstance(Report, dict) and Report.get("Format") == "PyCeler selection 1":
                    Stale.append(Relative)
        return _Replace_Outputs(Stage, Output, Paths, Stale)

def _Replace_Outputs(Stage, Output, Paths, Stale, Verify=None):
    Done = []
    with tempfile.TemporaryDirectory(prefix=".pyceler_", dir=Output) as Folder:
        Backup = Path(Folder)
        try:
            for Index, Relative in enumerate(Paths):
                Target = Output / Relative
                Target.parent.mkdir(parents=True, exist_ok=True)
                Pending = Backup / "Pending"
                shutil.copy2(Stage / Relative, Pending)
                Previous = Backup / str(Index) if Target.exists() else None
                if Previous is not None:
                    shutil.copy2(Target, Previous)
                os.replace(Pending, Target)
                Done.append((Target, Previous))
            for Index, Relative in enumerate(Stale, start=len(Paths)):
                Target = Output / Relative
                Previous = Backup / str(Index)
                os.replace(Target, Previous)
                Done.append((Target, Previous))
            if Verify is not None:
                Verify()
        except BaseException:
            for Target, Previous in reversed(Done):
                if Previous is None:
                    Target.unlink()
                else:
                    os.replace(Previous, Target)
            raise
    return tuple(Output / Relative for Relative in Paths)

def _Interpreter(Mode, Version):
    Current = f"{sys.version_info.major}.{sys.version_info.minor}"
    if Mode not in ("simple", "regular", "abi"):
        raise ValueError("Mode must be abi, simple or regular")
    Version = Version or ("3.11" if Mode == "abi" else Current)
    if Mode == "abi" and isinstance(Version, str) and re.fullmatch(r"0[xX]03[0-9a-fA-F]{2}0000", Version):
        Version = "3." + str(int(Version[4:6], 16))
    if not isinstance(Version, str) or not re.fullmatch(r"3\.(0|[1-9][0-9]?)", Version):
        raise ValueError("Python_Version must be a major.minor version such as 3.11")
    Minor = int(Version.split(".")[1])
    if Mode == "abi" and not 11 <= Minor <= sys.version_info.minor:
        raise ValueError("The stable ABI floor must be between 3.11 and the build interpreter version")
    if Mode == "abi" or Version == Current:
        return [sys.executable], Version
    return (["py", "-" + Version] if os.name == "nt" else ["python" + Version]), Version

def _Build(Stage, Paths, Output, Mode, Version, Link, OpenMP, Reports=(), Package_Loaders=False, Cache=False):
    if Mode == "auto":
        Mode = "abi" if sys.version_info >= (3, 11) else "simple"
    Command, Version = _Interpreter(Mode, Version)
    if OpenMP is not None and type(OpenMP) is not bool:
        raise ValueError("OpenMP must be None, True or False")
    Request = dict(Paths=[Path(Item).as_posix() for Item in Paths], Mode=Mode, Version=Version, Link=Link, OpenMP=OpenMP,
                   Package_Loaders=Package_Loaders)
    State = None
    if Cache is not False and Cache is not None:
        from .Binary_Cache import _Prepare_Binary_Cache, _Finish_Binary_Cache
        State = _Prepare_Binary_Cache(Stage, Request, Cache)
        Request["Track_Dependencies"] = State["Status"] == "enabled"
    Spec = Stage / "Request.json"
    Spec.write_text(json.dumps(Request), encoding="utf-8")
    Log_Root = Stage.parent / "Logs"
    Log_Root.mkdir(exist_ok=True)
    Log = Log_Root / (Stage.name + ".log")
    Program = ("import sys, types\nfrom pathlib import Path\nPackage = types.ModuleType('PyCeler')\n"
               "Package.__path__ = [sys.argv[1]]\nsys.modules['PyCeler'] = Package\n"
               "from PyCeler.Native_Build import _Run\n_Run(Path(sys.argv[2]))\n")
    with Log.open("w", encoding="utf-8") as Stream:
        if Request["Paths"]:
            Result = subprocess.run([*Command, "-I", "-B", "-c", Program, str(Path(__file__).resolve().parent), str(Spec)], cwd=Stage,
                                    stdout=Stream, stderr=subprocess.STDOUT)
            Return_Code = Result.returncode
        else:
            (Stage / "Products.json").write_text(json.dumps(Request["Cached_Products"]), encoding="utf-8")
            Stream.write("All native products restored from the compatible binary cache.\n")
            Return_Code = 0
    if Return_Code:
        Tail = Log.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
        raise RuntimeError(f"Native build failed. Full log: {Log}\n" + "\n".join(Tail))
    Products = [Path(Name) for Name in json.loads((Stage / "Products.json").read_text(encoding="utf-8"))]
    if "Product_Order" in Request:
        Order = {Name: Index for Index, Name in enumerate(Request["Product_Order"])}
        Products.sort(key=lambda Value: Order[Value.as_posix()])
    if State is not None:
        _Finish_Binary_Cache(State, Stage, Reports, Log)
    for Report in Reports:
        Target = Stage / "Products" / Report
        Target.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy2(Stage / "Sources" / Report, Target)
    Outputs = _Publish(Stage / "Products", Output, Products + list(Reports), Paths, Paths)[:len(Products)]
    return tuple(Item for Item in Outputs if Item.suffix != ".py")

def _Check_Layout(Stage, Output, Products, Sources):
    Suffix = ".pyd" if os.name == "nt" else ".so"
    for Item in Products:
        if Item.suffix == ".json":
            continue
        if Item.suffix == ".py" and (Output / Item).is_file() and (Output / Item).read_bytes() != (Stage / Item).read_bytes():
            raise ValueError(f"An existing Python source occupies the linked loader path: {Output / Item}")
        Other = Item.with_suffix(".py" if Item.suffix == Suffix else Suffix)
        if (Output / Other).exists():
            raise ValueError(f"Conflicting module {Output / Other}. Choose a separate output directory for this layout.")
    Binaries = set(Products)
    for Item in Sources:
        Individual = Item.with_suffix(Suffix)
        if Individual not in Binaries and (Output / Individual).exists():
            raise ValueError(f"Individual module {Output / Individual} occupies the linked output directory")

@contextmanager
def _Cython_Compatibility():
    import Cython
    if Cython.__version__ != "3.3.0":
        yield
        return
    from Cython.Compiler import ExprNodes, Optimize
    Original = Optimize.FinalOptimizePhase.visit_GeneralCallNode
    def _Visit(Visitor, Node):
        Keywords = Node.keyword_args
        if isinstance(Keywords, ExprNodes.DictNode) and any(not isinstance(Pair.key, ExprNodes.UnicodeNode) for Pair in Keywords.key_value_pairs):
            Visitor.visitchildren(Node)
            return Node
        return Original(Visitor, Node)
    Optimize.FinalOptimizePhase.visit_GeneralCallNode = _Visit
    try:
        yield
    finally:
        Optimize.FinalOptimizePhase.visit_GeneralCallNode = Original

def _Flags(Parallel):
    if os.name == "nt":
        return ["/O2", "/DNDEBUG", "/fp:strict"] + (["/openmp"] if Parallel else []), ["/DEBUG:NONE", "/OPT:REF", "/OPT:ICF", "/NOCOFFGRPINFO"]
    Shared = ["-fopenmp"] if Parallel else []
    return ["-O2", "-DNDEBUG", "-g0", "-ffp-contract=off", *Shared], ["-Wl,--strip-all", *Shared]

def _Module_Name(Relative):
    Parts = Relative.with_suffix("").parts
    if Parts[-1] == "__init__" and len(Parts) > 1:
        Parts = Parts[:-1]
    if not all(Name.isidentifier() and Name.isascii() for Name in Parts):
        raise ValueError(f"Invalid native module name: {Relative}")
    return ".".join(Parts)

def _Member_Alias(Name, Members):
    Alias = "_Pyceler_Member_" + Name
    while Alias in Members:
        Alias += "_"
    return Alias

def _Compile_Object(Compiler, Stage, Relative, Macros, Enable, Grouped, Track_Dependencies=False):
    import tokenize
    from Cython.Compiler.Main import CompilationOptions, compile as Cython_Compile, default_options
    File = Stage / "Sources" / Relative
    Name = _Module_Name(Relative)
    Directory = Stage / "Objects" / Relative.with_suffix("")
    Directory.mkdir(parents=True)
    with tokenize.open(str(File)) as Stream:
        Source_Text = Stream.read()
    CPlus = bool(re.search(r"(?m)^\s*#\s*distutils:\s*language\s*=\s*c\+\+\s*$", Source_Text))
    Generated = Directory / ("Module.cpp" if CPlus else "Module.c")
    Directives = dict(language_level=3, annotation_typing=False, infer_types=False, binding=True)
    Options = CompilationOptions(default_options, output_file=str(Generated), compiler_directives=Directives, cplus=CPlus,
                                 include_path=[str(File.parent), str(Stage / "Sources")])
    print(f"Cython {Name}", flush=True)
    with _Cython_Compatibility():
        if Cython_Compile(str(File), options=Options, full_module_name=Name).num_errors:
            raise ValueError(f"Cython generation failed for {Relative}")
    Content = Generated.read_text(encoding="utf-8")
    Parallel = Enable is not False and "#pragma omp " in Content
    if Grouped:
        Local = re.sub(r"(?m)^int (__Pyx_ApplySequenceOrMappingFlag\s*\()", r"static int \1", Content)
        if Local != Content:
            Generated.write_text(Local, encoding="utf-8")
    Compile_Args, Link_Args = _Flags(Parallel)
    if Track_Dependencies:
        Compile_Args.extend(["/sourceDependencies", "Dependencies.json"] if os.name == "nt" else ["-MD", "-MF", "Dependencies.d"])
    if CPlus and os.name == "nt":
        Compile_Args.append("/EHsc")
    Includes = [sysconfig.get_path("include"), sysconfig.get_path("platinclude"), str(File.parent)]
    if re.search(r'#include\s+[<"]numpy/', Content):
        import numpy
        Includes.append(numpy.get_include())
    print(f"Compile {Relative}: {Compile_Args}", flush=True)
    Original = Path.cwd()
    try:
        os.chdir(Directory)
        Objects = Compiler.compile([Generated.name], macros=Macros, include_dirs=Includes, extra_postargs=Compile_Args)
        return [Path(Item).resolve() for Item in Objects], Parallel, CPlus
    finally:
        os.chdir(Original)

def _Loader(Anchor, Alias=None):
    return f"""def _Load_Member():
    import importlib.util
    import sys
    from pathlib import Path
    Binary = Path(__file__).with_name({Anchor!r})
    Prefix = __name__.rpartition(".")[0]
    Name = __name__ if {Alias!r} is None else (Prefix + "." if Prefix else "") + {Alias!r}
    Spec = importlib.util.spec_from_file_location(Name, Binary)
    Module = importlib.util.module_from_spec(Spec)
    sys.modules[__name__] = Module
    Spec.loader.exec_module(Module)
    Module.__name__ = __name__
    Module.__package__ = __package__
    Module.__spec__ = importlib.util.spec_from_file_location(__name__, Binary)
_Load_Member()
"""

def _Run(Spec):
    import Cython
    import platform
    import struct
    from setuptools._distutils.ccompiler import new_compiler
    from setuptools._distutils.sysconfig import customize_compiler
    Request = json.loads(Spec.read_text(encoding="utf-8"))
    Stage = Spec.parent
    Stable = Request["Mode"] == "abi"
    Version = Request["Version"]
    if not Stable and Version != f"{sys.version_info.major}.{sys.version_info.minor}":
        raise ValueError(f"The selected interpreter does not match Python {Version}")
    if Stable and sysconfig.get_config_var("Py_GIL_DISABLED"):
        raise ValueError("Stable ABI builds require a GIL-enabled CPython interpreter")
    Macros = [("CYTHON_USE_PYLONG_INTERNALS", "0")]
    if Stable:
        Macros.append(("Py_LIMITED_API", f"0x03{int(Version.split('.')[1]):02X}0000"))
    print(f"Python {sys.version} | Cython {Cython.__version__} | mode {Request['Mode']} | macros {Macros}", flush=True)
    Compiler = new_compiler()
    customize_compiler(Compiler)
    Libraries, Dirs = [], []
    if os.name == "nt":
        Compiler.initialize()
        Dirs = [str(Path(sys.base_prefix) / "libs")]
        Libraries = ["python3" if Stable else Path(sysconfig.get_config_var("LIBRARY") or f"python{sys.version_info.major}{sys.version_info.minor}.lib").stem]
    Environment = dict(Python=sys.version, Executable=sys.executable, Platform=platform.platform(), Machine=platform.machine(),
                       Pointer_Bits=8 * struct.calcsize("P"), Cython=Cython.__version__, Compiler=Compiler.compiler_type,
                       Mode=Request["Mode"], ABI_Floor=Version if Stable else None, Macros=Macros,
                       Serial_Flags=_Flags(False), OpenMP_Flags=_Flags(True))
    (Stage / "Build_Environment.json").write_text(json.dumps(Environment, indent=2), encoding="utf-8")
    Groups = {}
    for Item in Request["Paths"]:
        Relative = Path(Item)
        Key = Relative.parent if Request["Link"] else Relative
        Groups.setdefault(Key, []).append(Relative)
    Products = [Path(Name) for Name in Request.get("Cached_Products", [])]
    Suffix = ".pyd" if os.name == "nt" else ".so"
    for Members in Groups.values():
        Members.sort(key=lambda Item: (Item.stem != "__init__", Item.name))
        Anchor = Members[0].with_suffix(Suffix)
        Binary = Stage / "Products" / Anchor
        Binary.parent.mkdir(parents=True, exist_ok=True)
        Objects, Exports, Parallel, CPlus, Aliases = [], [], False, False, {}
        Names = {Member.stem for Member in Members}
        for Member in Members:
            Symbol = "PyInit_" + _Module_Name(Member).split(".")[-1]
            Module_Macros = Macros
            if Symbol in Exports:
                Alias = "PyInit_" + _Member_Alias(Member.stem, Names)
                Module_Macros = [*Macros, (Symbol, Alias)]
                Symbol = Alias
                Aliases[Member] = Alias[len("PyInit_"):]
            Exports.append(Symbol)
            Native, Uses_OpenMP, Uses_CPlus = _Compile_Object(Compiler, Stage, Member, Module_Macros, Request["OpenMP"], len(Members) > 1, Request.get("Track_Dependencies", False))
            Objects.extend(str(Item) for Item in Native)
            Parallel |= Uses_OpenMP
            CPlus |= Uses_CPlus
        Link_Args = _Flags(Parallel)[1]
        print(f"Link {Anchor}: {Exports} {Libraries} {Link_Args}", flush=True)
        Compiler.link_shared_object(Objects, str(Binary), libraries=Libraries, library_dirs=Dirs,
                                    export_symbols=Exports, extra_postargs=Link_Args, target_lang="c++" if CPlus else "c")
        Products.append(Anchor)
        if Anchor.stem == "__init__" and not Request.get("Package_Loaders", False):
            continue
        for Member in Members[1:]:
            Shim = Member.with_suffix(".py")
            (Stage / "Products" / Shim).write_text(_Loader(Anchor.name, Aliases.get(Member)), encoding="utf-8")
            Products.append(Shim)
    (Stage / "Products.json").write_text(json.dumps([Item.as_posix() for Item in Products]), encoding="utf-8")

if __name__ == "__main__":
    _Run(Path(sys.argv[1]))
