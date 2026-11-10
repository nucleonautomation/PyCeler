import hashlib
import importlib.metadata
import io
import json
import os
import platform
import shutil
import shlex
import sys
import sysconfig
import tempfile
import tokenize
from pathlib import Path

def _Normalize_Workloads(Workloads):
    if Workloads is None:
        return {}
    if type(Workloads) is not dict:
        raise ValueError("Workloads must map function names to file-based factory specifications")
    Result = {}
    for Name, Spec in Workloads.items():
        if not isinstance(Name, str) or not Name or type(Spec) is not dict or set(Spec) - {"File", "Factory", "Dependencies"}:
            raise ValueError("Each workload requires a function name and File/Factory specification")
        Factory = Spec.get("Factory")
        if not isinstance(Factory, str) or not Factory.isidentifier():
            raise ValueError("A workload Factory must be a Python function identifier")
        File = Path(Spec.get("File", "")).resolve(strict=True)
        if not File.is_file() or File.suffix != ".py":
            raise ValueError("A workload File must be an existing Python file")
        Dependencies = Spec.get("Dependencies", [])
        if not isinstance(Dependencies, (tuple, list)):
            raise ValueError("Workload Dependencies must be a sequence of file paths")
        Paths = [Path(Value).resolve(strict=True) for Value in Dependencies]
        if any(not Value.is_file() for Value in Paths):
            raise ValueError("Workload dependencies must be files")
        Result[Name] = dict(File=str(File), Factory=Factory, Dependencies=[str(Value) for Value in Paths])
    return Result

def _Digest(File):
    Hash = hashlib.sha256()
    with File.open("rb") as Stream:
        for Chunk in iter(lambda: Stream.read(1048576), b""):
            Hash.update(Chunk)
    return Hash.hexdigest()

def _Toolchain():
    Search = os.environ.get("PATH", "")
    Configuration = {}
    if os.name == "nt":
        try:
            from setuptools._distutils._msvccompiler import _get_vc_env
            Target = "x86_amd64" if sysconfig.get_platform() == "win-amd64" else "x86_arm64"
            Environment = _get_vc_env(Target)
            Search = Environment.get("path", Search)
            Configuration = {Name: Environment.get(Name, "") for Name in ("include", "lib", "libpath", "windowssdkdir", "windowssdkversion", "vctoolsversion")}
        except Exception:
            return None
        Names = ("cl.exe", "link.exe")
    else:
        Commands = [os.environ.get(Name) or sysconfig.get_config_var(Name) or Default for Name, Default in (("CC", "gcc"), ("CXX", "g++"))]
        Names = tuple(shlex.split(Command)[0] for Command in Commands) + ("ld",)
        if any(Path(Name).name in ("ccache", "sccache", "distcc") for Name in Names):
            return None
        Configuration = dict(Commands=Commands)
    Tools = []
    for Name in Names:
        File = shutil.which(Name, path=Search)
        if File is None:
            return None
        Path_Value = Path(File).resolve()
        Tools.append([str(Path_Value), _Digest(Path_Value)])
    return dict(Tools=Tools, Configuration=Configuration)

def _Cache_Context(File, Mode, Version, Parallel, Gain, Workloads, Cache, Elide_Temporaries=False, Source_Text=None, Configuration=None):
    if Cache is False or Cache is None:
        return None
    if Cache is not True and not isinstance(Cache, (str, os.PathLike)):
        raise ValueError("Cache must be False, True or a cache directory path")
    if Mode != "abi" and Version != f"{sys.version_info.major}.{sys.version_info.minor}":
        return None
    Compiler = _Toolchain()
    if Compiler is None:
        return None
    Engine = Path(__file__).parent
    Source_Bytes = File.read_bytes()
    Encoding = tokenize.detect_encoding(io.BytesIO(Source_Bytes).readline)[0]
    Current_Text = Source_Bytes.decode(Encoding).replace("\r\n", "\n").replace("\r", "\n")
    if Source_Text is not None and Current_Text != Source_Text:
        return None
    Sources = sorted(Value for Value in Engine.iterdir() if Value.is_file() and Value.suffix in (".py", ".pyx", ".pxi", ".pxd", ".in", ".h", ".hpp", ".pyd", ".so"))
    Versions = {}
    for Name in ("Cython", "numpy", "setuptools"):
        try:
            Versions[Name] = importlib.metadata.version(Name)
        except importlib.metadata.PackageNotFoundError:
            Versions[Name] = None
    Dependencies = sorted({Path(Spec["File"]) for Spec in Workloads.values()} | {Path(Value) for Spec in Workloads.values() for Value in Spec["Dependencies"]})
    Environment = {Key: Value for Key, Value in os.environ.items() if Key.startswith(("OMP_", "MKL_", "OPENBLAS_", "BLIS_")) or Key in ("CC", "CXX", "CFLAGS", "CPPFLAGS", "LDFLAGS", "CL", "_CL_", "LINK", "INCLUDE", "LIB", "LIBPATH", "VCToolsVersion", "WindowsSDKVersion", "PROCESSOR_IDENTIFIER")}
    Manifest = dict(Format="PyCeler selection cache 1", Source=[str(File.resolve()), hashlib.sha256(Source_Bytes).hexdigest()], Package=str(Engine.resolve()),
                    Engine=[[Value.name, _Digest(Value)] for Value in Sources], Dependencies=[[str(Value), _Digest(Value)] for Value in Dependencies],
                    Versions=Versions, Mode=Mode, Version=Version, Parallel=Parallel, Minimum_Speedup=Gain, Workloads=Workloads,
                    Elide_Temporaries=Elide_Temporaries, Configuration=Configuration, Compiler=Compiler, Python=[sys.executable, sys.version, sys.implementation.cache_tag],
                    Platform=[sys.platform, platform.platform(), platform.node(), platform.machine(), platform.processor(), os.cpu_count()], Environment=Environment)
    Key = hashlib.sha256(json.dumps(Manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    Root = Path(os.environ.get("PYCELER_CACHE_DIR", Path.cwd() / "Build" / "Cache") if Cache is True else Cache).resolve()
    Root.mkdir(parents=True, exist_ok=True)
    return Root, Key, Manifest

def _Cache_Read(Context):
    from .Selection_Policy import _Candidate_Name
    if Context is None:
        return None
    Root, Key, Manifest = Context
    try:
        Directory = Root / Key
        if Directory.is_symlink() or Directory.resolve().parent != Root.resolve():
            return None
        Record = json.loads((Directory / "Result.json").read_text(encoding="utf-8"))
        if Record.get("Manifest") != Manifest:
            return None
        Result = Record["Result"]
        if Record.get("Digest") != hashlib.sha256(json.dumps(Result, sort_keys=True).encode("utf-8")).hexdigest():
            return None
        Choices = {int(Line): Table for Line, Table in Result["Choices"].items()}
        for Table in Choices.values():
            if type(Table) is not dict or any(type(Bands) is not list or any(type(Band) is not list or len(Band) != 2 or type(Band[0]) is not int or Band[0] < 0 or type(Band[1]) is not int or not _Candidate_Name(Band[1]) for Band in Bands) for Bands in Table.values()):
                return None
        Choices = {Line: {Key: [tuple(Band) for Band in Bands] for Key, Bands in Table.items()} for Line, Table in Choices.items()}
        Report = Result["Report"]
        if Report.get("Format") != "PyCeler selection 1":
            return None
        Report["Cache"] = dict(Status="hit", Key=Key, Directory=str(Root / Key))
        for Variant, Build in Report.get("Builds", {}).items():
            Log = Root / Key / "Artifacts" / ("Probe_" + Variant + ".log")
            if Log.is_file():
                Build["Log"] = str(Log)
        return Choices, Result["Environment"], Report
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None

def _Cache_Write(Context, Choices, Environment, Report, Folder):
    if Context is None or Environment is None or any("Probe_Error" in Item or "Reason" in Item for Item in Report["Items"]):
        return
    if any(Build.get("Status") != "built" for Build in Report["Builds"].values()):
        return
    Root, Key, Manifest = Context
    if "Package" in Manifest:
        Files = [Manifest["Source"], *Manifest["Dependencies"], *[[str(Path(Manifest["Package"]) / Name), Digest] for Name, Digest in Manifest["Engine"]]]
        if any(not Path(Name).is_file() or _Digest(Path(Name)) != Digest for Name, Digest in Files):
            return
    Directory = Root / Key
    if Directory.is_symlink() or Directory.resolve().parent != Root.resolve():
        raise OSError("Cache entry is not a direct local child of the cache directory")
    Lock = Root / (Key + ".lock")
    try:
        Lock.mkdir()
    except FileExistsError:
        return
    try:
        if _Cache_Read(Context) is not None:
            return
        with tempfile.TemporaryDirectory(prefix="Pending_", dir=Root) as Temporary:
            Pending = Path(Temporary) / Key
            Pending.mkdir()
            Artifacts = []
            for File in sorted(Folder.rglob("*")):
                if File.is_file() and File.suffix in (".py", ".pyx", ".pyd", ".so", ".json", ".result", ".log"):
                    Relative = File.relative_to(Folder)
                    Target = Pending / "Artifacts" / Relative
                    Target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(File, Target)
                    Artifacts.append([Relative.as_posix(), _Digest(Target)])
            Result = json.loads(json.dumps(dict(Choices=Choices, Environment=Environment, Report=Report)))
            Digest = hashlib.sha256(json.dumps(Result, sort_keys=True).encode("utf-8")).hexdigest()
            (Pending / "Result.json").write_text(json.dumps(dict(Manifest=Manifest, Artifacts=Artifacts, Result=Result, Digest=Digest), indent=2), encoding="utf-8")
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
