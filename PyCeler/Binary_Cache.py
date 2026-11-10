import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import shlex
import sys
import sysconfig
import tempfile
import time
from pathlib import Path
from .Selection_Cache import _Digest, _Toolchain
from .Source_Inputs import _Dependencies

def _Groups(Paths, Linked):
    Groups = {}
    for Value in Paths:
        Relative = Path(Value)
        Groups.setdefault(Relative.parent if Linked else Relative, []).append(Relative)
    return [sorted(Members, key=lambda Item: (Item.stem != "__init__", Item.name)) for Members in Groups.values()]

def _Products(Members, Loaders):
    Anchor = Members[0].with_suffix(".pyd" if os.name == "nt" else ".so")
    return [Anchor, *([] if Anchor.stem == "__init__" and not Loaders else [Member.with_suffix(".py") for Member in Members[1:]])]

def _Fingerprint(Request):
    from .Native_Build import _Flags
    if Request["Mode"] != "abi" and Request["Version"] != f"{sys.version_info.major}.{sys.version_info.minor}":
        return None
    Compiler = _Toolchain()
    if Compiler is None:
        return None
    Libraries = []
    if os.name == "nt":
        Search = Compiler["Configuration"].get("lib", os.environ.get("LIB", ""))
        Directories = [Path(sys.base_prefix) / "libs", *(Path(Value) for Value in Search.split(";") if Value)]
        for Name in ("python3.lib", "libcmt.lib", "libcpmt.lib", "libucrt.lib", "libvcruntime.lib", "msvcrt.lib", "msvcprt.lib", "ucrt.lib", "vcruntime.lib", "vcomp.lib", "kernel32.lib"):
            File = next((Directory / Name for Directory in Directories if (Directory / Name).is_file()), None)
            if File is not None:
                Libraries.append([str(File.resolve()), _Digest(File)])
        Directory = Path(Compiler["Tools"][0][0]).parent
        Libraries.extend([str(File), _Digest(File)] for File in (Directory / Name for Name in ("c1.dll", "c1xx.dll", "c2.dll")) if File.is_file())
    Versions = {Name: importlib.metadata.version(Name) for Name in ("Cython", "setuptools")}
    try:
        Versions["numpy"] = importlib.metadata.version("numpy")
    except importlib.metadata.PackageNotFoundError:
        Versions["numpy"] = None
    Package = Path(__file__).parent
    Backend = sorted(File for File in Package.iterdir() if File.is_file() and File.stem in ("__init__", "Native_Build", "Binary_Cache", "Source_Inputs", "Selection_Cache"))
    Names = ("CC", "CXX", "CFLAGS", "CPPFLAGS", "LDFLAGS", "CL", "_CL_", "LINK", "INCLUDE", "LIB", "LIBPATH", "VCToolsVersion", "WindowsSDKVersion", "PROCESSOR_IDENTIFIER")
    return dict(Format="PyCeler binary cache 1", Compiler=Compiler, Libraries=Libraries, Versions=Versions, Backend=[[File.name, _Digest(File)] for File in Backend],
                Python=[sys.executable, sys.version, sys.implementation.cache_tag, sysconfig.get_platform()],
                Host=[sys.platform, platform.platform(), platform.machine(), platform.processor()],
                Environment={Name: os.environ.get(Name) for Name in Names}, Flags=[_Flags(False), _Flags(True)],
                Mode=Request["Mode"], Version=Request["Version"], Link=Request["Link"], OpenMP=Request["OpenMP"], Package_Loaders=Request["Package_Loaders"])

def _Snapshots(Sources, Members):
    from Cython.Build.Dependencies import DependencyTree
    from Cython.Compiler.Main import CompilationOptions, Context, default_options
    Pending = [Sources / Member for Member in Members]
    Files = set()
    for File in Pending:
        Context_Value = Context.from_options(CompilationOptions(default_options, language_level=3, include_path=[str(File.parent), str(Sources)]))
        Files.update(Path(Value).resolve() for Value in DependencyTree(Context_Value, quiet=True).all_dependencies(str(File)))
    Pending = list(Files)
    Visited = set()
    while Pending:
        File = Pending.pop()
        if File in Visited:
            continue
        Visited.add(File)
        if File.is_relative_to(Sources):
            Pending.extend(_Dependencies(File, Sources))
    return [(File, _Digest(File)) for File in sorted(Visited)]

def _Read(Directory, Manifest, Products, Destination):
    try:
        if Directory.is_symlink():
            return False
        Record = json.loads((Directory / "Manifest.json").read_text(encoding="utf-8"))
        Expected = [Value.as_posix() for Value in Products]
        if Record.get("Build") != Manifest or sorted(Record.get("Products", {})) != sorted(Expected):
            return False
        Headers = Record["External_Headers"]
        if not isinstance(Headers, list) or any(not Path(Name).is_file() or _Digest(Path(Name)) != Digest for Name, Digest in Headers):
            return False
        Contents = {}
        for Relative in Products:
            Source = Directory / "Products" / Relative
            if not Source.resolve().is_relative_to(Directory.resolve()) or Source.is_symlink():
                return False
            Data = Source.read_bytes()
            if hashlib.sha256(Data).hexdigest() != Record["Products"][Relative.as_posix()]:
                return False
            Contents[Relative] = Data
    except (OSError, ValueError, KeyError, TypeError):
        return False
    if Destination is not None:
        for Relative, Data in Contents.items():
            Target = Destination / Relative
            Target.parent.mkdir(parents=True, exist_ok=True)
            Target.write_bytes(Data)
    return True

def _Prepare_Binary_Cache(Stage, Request, Cache):
    if Cache is not True and not isinstance(Cache, (str, os.PathLike)):
        raise ValueError("Cache must be False, True or a cache directory path")
    Root = Path(os.environ.get("PYCELER_CACHE_DIR", Path.cwd() / "Build" / "Cache") if Cache is True else Cache).resolve() / "Native"
    Groups = []
    Snapshot_Time = time.time_ns()
    try:
        Fingerprint = _Fingerprint(Request)
        if Fingerprint is None:
            return dict(Status="unavailable", Reason="Compiler or selected interpreter identity could not be verified", Groups=[])
        Root.mkdir(parents=True, exist_ok=True)
        Sources = (Stage / "Sources").resolve()
        for Members in _Groups(Request["Paths"], Request["Link"]):
            Snapshots = _Snapshots(Sources, Members)
            Dependencies = [[File.relative_to(Sources).as_posix() if File.is_relative_to(Sources) else str(File), Digest] for File, Digest in Snapshots]
            Manifest = dict(Fingerprint, Members=[Value.as_posix() for Value in Members], Dependencies=Dependencies)
            Manifest = json.loads(json.dumps(Manifest))
            Key = hashlib.sha256(json.dumps(Manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            Products = _Products(Members, Request["Package_Loaders"])
            Directory = Root / Key
            Hit = _Read(Directory, Manifest, Products, Stage / "Products")
            Groups.append(dict(Members=Members, Products=Products, Directory=Directory, Manifest=Manifest, Snapshots=Snapshots, Snapshot_Time=Snapshot_Time, Status="hit" if Hit else "miss"))
    except (OSError, ValueError, RuntimeError, ImportError) as Error:
        return dict(Status="unavailable", Reason=str(Error), Groups=[])
    Request["Paths"] = [Member.as_posix() for Group in Groups if Group["Status"] != "hit" for Member in Group["Members"]]
    Request["Cached_Products"] = [Product.as_posix() for Group in Groups if Group["Status"] == "hit" for Product in Group["Products"]]
    Request["Product_Order"] = [Product.as_posix() for Group in Groups for Product in Group["Products"]]
    return dict(Status="enabled", Groups=Groups)

def _External_Headers(Group, Stage):
    Files = set()
    for Member in Group["Members"]:
        Directory = Stage / "Objects" / Member.with_suffix("")
        if os.name == "nt":
            File = Directory / "Dependencies.json"
            if not File.is_file():
                return None
            Data = json.loads(File.read_text(encoding="utf-8-sig"))["Data"]
            Headers = Data["Includes"]
        else:
            File = Directory / "Dependencies.d"
            if not File.is_file():
                return None
            Text = File.read_text(encoding="utf-8").replace("\\\n", "")
            Headers = shlex.split(Text.split(":", 1)[1])
        for Name in Headers:
            Path_Value = Path(Name)
            Path_Value = (Directory / Path_Value).resolve() if not Path_Value.is_absolute() else Path_Value.resolve()
            if not Path_Value.is_relative_to(Stage.resolve()):
                Files.add(Path_Value)
    Headers = []
    for File in sorted(Files):
        Before = File.stat()
        Digest = _Digest(File)
        After = File.stat()
        if Before.st_mtime_ns > Group["Snapshot_Time"] or (Before.st_mtime_ns, Before.st_size) != (After.st_mtime_ns, After.st_size):
            raise ValueError("An external compiler header changed during the build; binary was not cached")
        Headers.append([str(File), Digest])
    return Headers

def _Store(Group, Stage):
    Directory = Group["Directory"]
    if any(not File.is_file() or _Digest(File) != Digest for File, Digest in Group["Snapshots"]):
        return
    Headers = _External_Headers(Group, Stage)
    if Headers is None:
        raise ValueError("Compiler dependency tracking was unavailable; binary was not cached")
    Lock = Directory.with_suffix(".lock")
    try:
        Lock.mkdir()
    except FileExistsError:
        return
    try:
        if _Read(Directory, Group["Manifest"], Group["Products"], None):
            return
        if Directory.is_symlink() or Directory.resolve().parent != Directory.parent.resolve():
            raise ValueError("Cache entry is not a direct local child of the cache directory")
        with tempfile.TemporaryDirectory(prefix="Pending_", dir=Directory.parent) as Temporary:
            Pending = Path(Temporary) / "Entry"
            Hashes = {}
            for Relative in Group["Products"]:
                Target = Pending / "Products" / Relative
                Target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Stage / "Products" / Relative, Target)
                Hashes[Relative.as_posix()] = _Digest(Target)
            (Pending / "Manifest.json").write_text(json.dumps(dict(Build=Group["Manifest"], Products=Hashes, External_Headers=Headers), indent=2), encoding="utf-8")
            Previous = Path(Temporary) / "Previous"
            if Directory.exists():
                os.replace(Directory, Previous)
            try:
                os.replace(Pending, Directory)
            except OSError:
                if Previous.exists():
                    os.replace(Previous, Directory)
                raise
    finally:
        Lock.rmdir()

def _Finish_Binary_Cache(State, Stage, Reports, Log):
    Summary = {Key: Value for Key, Value in State.items() if Key != "Groups"}
    Summary["Modules"] = []
    for Group in State["Groups"]:
        Item = dict(Sources=[Value.as_posix() for Value in Group["Members"]], Status=Group["Status"], Key=Group["Directory"].name)
        if Group["Status"] == "miss":
            try:
                _Store(Group, Stage)
            except (OSError, ValueError, KeyError, TypeError) as Error:
                Item["Write_Error"] = str(Error)
        Summary["Modules"].append(Item)
    with Log.open("a", encoding="utf-8") as Stream:
        Stream.write("\nBinary cache: " + json.dumps(Summary) + "\n")
    for Relative in Reports:
        File = Stage / "Sources" / Relative
        Report = json.loads(File.read_text(encoding="utf-8"))
        Report["Binary_Cache"] = Summary
        File.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    (Stage / "Binary_Cache.json").write_text(json.dumps(Summary, indent=2), encoding="utf-8")
