import argparse
import ast
import base64
import csv
import hashlib
import importlib.util
import io
import json
import os
import platform
import re
import shutil
import sys
import sysconfig
import tempfile
import zipfile
from pathlib import Path

def _Backend(Root):
    Spec = importlib.util.spec_from_file_location("Native_Build", Root / "PyCeler" / "Native_Build.py")
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Identity(Root):
    Spec = importlib.util.spec_from_file_location("_PyCeler_Build_Identity", Root / "PyCeler" / "Build_Identity.py")
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Embedded_Resources(Package):
    Files = [*sorted(Package.glob("*.pxi.in")), Package / "Selection_Environment.py"]
    Resources = {File.name: File.read_text(encoding="utf-8") for File in Files}
    return ("cdef dict _Resources = " + repr(Resources) + "\n\ndef _Resource(Name):\n"
            "    if Name not in _Resources:\n        raise ValueError(f'Unknown PyCeler runtime resource: {Name}')\n"
            "    return _Resources[Name]\n")

def _Stage_Package(Root, Stage):
    Package = Root / "PyCeler"
    Sources = Stage / "Sources" / "PyCeler"
    Sources.mkdir(parents=True)
    Paths = []
    for File in [Package / "Engine.pyx", *sorted(Package.glob("*.py"))]:
        if File.name in ("__init__.py", "Runtime_Resources.py"):
            continue
        shutil.copy2(File, Sources / File.name)
        Paths.append(Path("PyCeler") / File.name)
    for File in sorted(Package.glob("*.pxi")):
        shutil.copy2(File, Sources / File.name)
    Resource = Path("PyCeler/Runtime_Resources.pyx")
    (Stage / "Sources" / Resource).write_text(_Embedded_Resources(Package), encoding="utf-8")
    Paths.append(Resource)
    return Paths

def _Package_Init(Package, Build_Id=None, Source_Fingerprint=None):
    Tree = ast.parse((Package / "__init__.py").read_text(encoding="utf-8"))
    Versions = [Node.value.value for Node in Tree.body if isinstance(Node, ast.Assign) and
                any(isinstance(Target, ast.Name) and Target.id == "__version__" for Target in Node.targets) and
                isinstance(Node.value, ast.Constant) and isinstance(Node.value.value, str)]
    if len(Versions) != 1:
        raise ValueError("The source package must define one literal __version__")
    return ("from .Loop_Detector import Loop_Finding\nfrom .Engine import Analyze, Convert, Compile\n\n"
            "__version__ = " + repr(Versions[0]) + "\n__build_id__ = " + repr(Build_Id) + "\n__source_fingerprint__ = " + repr(Source_Fingerprint) +
            "\n__all__ = ['Analyze', 'Convert', 'Compile', 'Loop_Finding']\n")

def _Target(Target):
    System = platform.system().lower()
    Machine = sysconfig.get_platform().lower().replace("_", "-").removeprefix("win-").removeprefix("linux-")
    if Machine == "x86-64":
        Machine = "x86_64"
    Architecture = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(Machine, Machine)
    Host = System + "-" + Architecture
    Supported = ("windows-x64", "linux-x64", "linux-arm64")
    if Host not in Supported:
        raise ValueError(f"Native package target {Host} is not supported; supported targets are {', '.join(Supported)}")
    if Target not in ("native", Host):
        raise ValueError(f"Requested target {Target} differs from host {Host}; build on that platform with its native toolchain")
    return Host

def _Managed_Cache(Relative):
    return (len(Relative.parts) == 2 and Relative.parts[0] == "__pycache__" and
            re.fullmatch(r"__init__\.[A-Za-z0-9_-]+(?:\.opt-[0-9]+)?\.pyc", Relative.name) is not None)

def _Existing_Files(Destination):
    Files = []
    if not Destination.exists():
        return Files
    for File in Destination.rglob("*"):
        Relative = File.relative_to(Destination)
        if File.is_symlink() or not File.resolve().is_relative_to(Destination):
            raise ValueError(f"Package output contains a linked path: {File}; choose a clean output directory")
        if File.is_dir():
            if Relative != Path("__pycache__"):
                raise ValueError(f"Package output contains an unmanaged directory: {File}; choose a clean output directory")
        elif File.is_file():
            if not (len(Relative.parts) == 1 and (File.name == "__init__.py" or File.suffix in (".pyd", ".so"))) and not _Managed_Cache(Relative):
                raise ValueError(f"Package output contains non-distribution files: {File}; choose a clean output directory")
            Files.append(Path("PyCeler") / Relative)
    return Files

def _Previous_Manifest(Output):
    File = Output / "PyCeler.manifest.json"
    if not File.exists():
        return {}
    if File.is_symlink():
        raise ValueError(f"The package manifest is a linked file: {File}")
    try:
        Manifest = json.loads(File.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as Error:
        raise ValueError(f"Cannot replace an unrecognized package manifest: {File}") from Error
    if not isinstance(Manifest, dict) or Manifest.get("Format") != "PyCeler native package 1" or not isinstance(Manifest.get("Files"), dict):
        raise ValueError(f"Cannot replace an unrecognized package manifest: {File}")
    return Manifest["Files"]

def _Publish_Package(Backend, Built, Output, Products, Report):
    Manifest = Path("PyCeler.manifest.json")
    (Built / Manifest).write_text(json.dumps(Report, indent=2), encoding="utf-8")
    Destination = Output / "PyCeler"
    Expected = set(Products)
    with Backend._Publication(Output):
        Previous = _Previous_Manifest(Output)
        Stale = []
        for Relative in _Existing_Files(Destination):
            if Relative in Expected:
                continue
            File = Output / Relative
            if _Managed_Cache(Relative.relative_to("PyCeler")):
                Stale.append(Relative)
            elif Previous.get(Relative.as_posix(), Previous.get(str(Relative))) == hashlib.sha256(File.read_bytes()).hexdigest():
                Stale.append(Relative)
            else:
                raise ValueError(f"Package output contains an unowned or modified binary: {File}; choose a clean output directory")
        def _Verify():
            if set(_Existing_Files(Destination)) != Expected:
                raise RuntimeError("Published package inventory changed during publication")
        Backend._Replace_Outputs(Built, Output, Products + [Manifest], Stale, Verify=_Verify)
        Cache = Destination / "__pycache__"
        if Cache.is_dir() and not any(Cache.iterdir()):
            Cache.rmdir()

def Build_Package(Output_Directory=None, *, Mode="abi", Python_Version=None, OpenMP=None, Target="native"):
    Root = Path(__file__).resolve().parent
    Host_Target = _Target(Target)
    Output = Path(Output_Directory).resolve() if Output_Directory is not None else (Root / "Build" / "Lib").resolve()
    Destination = (Output / "PyCeler").resolve()
    Source = Root / "PyCeler"
    if Destination == Source or Destination.is_relative_to(Source) or Source.is_relative_to(Destination):
        raise ValueError("Choose a package output separate from the development source tree")
    _Existing_Files(Destination)
    _Previous_Manifest(Output)
    Backend = _Backend(Root)
    Identity = _Identity(Root)
    State = Identity._Source_State(Root)
    with Backend._Workspace() as Stage:
        Paths = _Stage_Package(Root, Stage)
        Built = Stage / "Distribution"
        Backend._Build(Stage, Paths, Built, Mode, Python_Version, False, OpenMP)
        Environment_Path = Stage / "Build_Environment.json"
        Environment = json.loads(Environment_Path.read_text(encoding="utf-8")) if Environment_Path.is_file() else {}
        if Environment.get("Pointer_Bits", 64) != 64:
            raise ValueError("The selected build interpreter must be 64-bit for the requested package target")
        if State != Identity._Source_State(Root):
            raise RuntimeError("PyCeler source or build dependencies changed during compilation; rebuild before publishing the package")
        Build_Id = Identity._Digest(dict(State=State, Target=Host_Target, Mode=Mode, Python_Version=Python_Version, OpenMP=OpenMP, Environment=Environment))
        (Built / "PyCeler" / "__init__.py").write_text(_Package_Init(Source, Build_Id, State["Source_Fingerprint"]), encoding="utf-8")
        Products = [File.relative_to(Built) for File in sorted((Built / "PyCeler").iterdir()) if File.is_file()]
        Suffix = ".pyd" if os.name == "nt" else ".so"
        Expected = {Relative.with_suffix(Suffix) for Relative in Paths} | {Path("PyCeler/__init__.py")}
        if set(Products) != Expected:
            raise RuntimeError("Distribution contains unexpected or missing files")
        Report = dict(Format="PyCeler native package 1", Mode=Mode, Python_Version=Python_Version or ("3.11" if Mode in ("abi", "auto") else None),
                      Target=Host_Target, Platform=platform.platform(), Machine=platform.machine(),
                      Build_Id=Build_Id, **State,
                      Build_Environment=Environment,
                      Files={Relative.as_posix(): hashlib.sha256((Built / Relative).read_bytes()).hexdigest() for Relative in Products},
                      Embedded_Resources=[File.name for File in sorted(Source.glob("*.pxi.in"))] + ["Selection_Environment.py"])
        Report_Path = Stage.parent / "Logs" / (Stage.name + ".package.json")
        Report_Path.parent.mkdir(parents=True, exist_ok=True)
        Report_Path.write_text(json.dumps(Report, indent=2), encoding="utf-8")
        _Publish_Package(Backend, Built, Output, Products, Report)
    return Destination

def Build_Wheel(Output_Directory=None, *, Library_Directory=None, Mode="abi", Python_Version=None, OpenMP=None, Target="native"):
    Root = Path(__file__).resolve().parent
    if Library_Directory is None:
        Package = Build_Package(Mode=Mode, Python_Version=Python_Version, OpenMP=OpenMP, Target=Target)
    else:
        Library = Path(Library_Directory).resolve()
        Package = Library if Library.name.casefold() == "pyceler" else Library / "PyCeler"
    Report = _Identity(Root)._Verify_Development(Root, Package)
    Host = _Target(Target)
    if Report["Target"] != Host:
        raise ValueError("Wheel packaging requires a verified package built for this native host")
    Environment = Report["Build_Environment"]
    Stable = Environment.get("Mode", Report["Mode"]) == "abi"
    Version = ast.literal_eval(next(Node.value for Node in ast.parse((Package / "__init__.py").read_text(encoding="utf-8")).body
                                   if isinstance(Node, ast.Assign) and any(isinstance(Target, ast.Name) and Target.id == "__version__" for Target in Node.targets)))
    Python_Tag = "cp" + (Environment.get("ABI_Floor") or Report.get("Python_Version") or f"{sys.version_info.major}.{sys.version_info.minor}").replace(".", "")
    if not Stable:
        Python_Tag = "cp" + Environment.get("Python", platform.python_version()).split()[0].rsplit(".", 1)[0].replace(".", "")
    ABI_Tag = "abi3" if Stable else Environment.get("ABI_Tag")
    if not Stable and (not isinstance(ABI_Tag, str) or not re.fullmatch(re.escape(Python_Tag) + r"t?d?", ABI_Tag)):
        raise ValueError("The package does not record its exact interpreter ABI; rebuild before creating a regular-mode wheel")
    Platform_Tag = {"windows-x64": "win_amd64", "linux-x64": "linux_x86_64", "linux-arm64": "linux_aarch64"}[Host]
    Tag = f"{Python_Tag}-{ABI_Tag}-{Platform_Tag}"
    Metadata_Directory = f"pyceler-{Version}.dist-info"
    Contents = {Name: (Package.parent / Name).read_bytes() for Name in sorted(Report["Files"])}
    Contents[Metadata_Directory + "/METADATA"] = (f"Metadata-Version: 2.4\nName: PyCeler\nVersion: {Version}\nSummary: Measured native specialization of Python numeric loops\n"
                                                    "Requires-Python: >=3.11\nLicense-Expression: MIT\nLicense-File: LICENSE.md\n"
                                                    "Requires-Dist: Cython>=3.1\nRequires-Dist: setuptools\nRequires-Dist: numpy; extra == 'test'\nProvides-Extra: test\n").encode("utf-8")
    Contents[Metadata_Directory + "/WHEEL"] = (f"Wheel-Version: 1.0\nGenerator: PyCeler {Version}\nRoot-Is-Purelib: false\nTag: {Tag}\n").encode("utf-8")
    Contents[Metadata_Directory + "/licenses/LICENSE.md"] = (Root / "LICENSE.md").read_bytes()
    Contents[Metadata_Directory + "/PyCeler.manifest.json"] = json.dumps(Report, indent=2, sort_keys=True).encode("utf-8")
    Record = io.StringIO(newline="")
    Writer = csv.writer(Record, lineterminator="\n")
    for Name, Content in sorted(Contents.items()):
        Writer.writerow((Name, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(Content).digest()).rstrip(b"=").decode("ascii"), len(Content)))
    Writer.writerow((Metadata_Directory + "/RECORD", "", ""))
    Contents[Metadata_Directory + "/RECORD"] = Record.getvalue().encode("utf-8")
    Output = Path(Output_Directory).resolve() if Output_Directory is not None else Root / "Build" / "Wheels"
    if Output == Root / "PyCeler" or Output.is_relative_to(Root / "PyCeler"):
        raise ValueError("Choose a wheel output separate from the development source tree")
    Output.mkdir(parents=True, exist_ok=True)
    Wheel = Output / f"pyceler-{Version}-{Tag}.whl"
    with tempfile.TemporaryDirectory(prefix="Wheel_", dir=Output) as Folder:
        Pending = Path(Folder) / Wheel.name
        with zipfile.ZipFile(Pending, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as Archive:
            for Name, Content in sorted(Contents.items()):
                Info = zipfile.ZipInfo(Name, date_time=(1980, 1, 1, 0, 0, 0))
                Info.create_system = 3
                Info.external_attr = 0o100644 << 16
                Info.compress_type = zipfile.ZIP_DEFLATED
                Archive.writestr(Info, Content, compresslevel=9)
        os.replace(Pending, Wheel)
    return Wheel

def _Engine(Args):
    return Build_Package(Args.output, Mode=Args.mode, Python_Version=Args.python_version, OpenMP=Args.openmp, Target=Args.target)

def _Print_Selection_Summary(Output):
    Report = Path(Output).with_suffix(".selection.json")
    if not Report.is_file():
        return
    try:
        Data = json.loads(Report.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    Summary = Data.get("Summary")
    if not isinstance(Summary, dict):
        return
    if Data.get("Measurement") is False:
        print(f"  Static analysis: {Summary['Candidate_Regions']} eligible regions, {Summary['Skipped_Loops']} skipped loops.")
        print("  Measurement disabled; eligible native candidates are generated without a measured speedup claim.")
        print(f"  Report: {Report}")
        return
    print(f"  Selection: {Summary['Candidate_Regions']} candidate regions, {Summary['Native_Selected_Regions']} with native dispatch, {Summary['Skipped_Loops']} skipped loops.")
    if Data.get("Status") == "no_candidates":
        print("  No specialized native kernel was generated; the original loops remain unchanged.")
    elif not Summary["Native_Selected_Regions"]:
        print("  Selection retained Python for all candidate regions; inspect validation and timing outcomes in the report.")
    print(f"  Report: {Report}")

def _Main():
    sys.dont_write_bytecode = True
    Parser = argparse.ArgumentParser(description="Build PyCeler locally or process Python and Cython sources.")
    Parser.add_argument("action", nargs="?", choices=("engine", "analyze", "convert", "compile", "doctor", "package", "wheel"))
    Parser.add_argument("--input", help=".py, .pyx, .pxi file or source directory")
    Parser.add_argument("--output", help="Directory for generated sources/native modules; package writes its PyCeler folder here")
    Parser.add_argument("--library", help="With wheel, package an existing verified library directory instead of rebuilding")
    Parser.add_argument("--mode", choices=("abi", "simple", "regular", "auto"), default="abi")
    Parser.add_argument("--build", help="Directory for temporary builds and compiler logs")
    Parser.add_argument("--python-version", "--limited-api", help="ABI floor (default 3.11) or simple-mode interpreter version")
    Layout = Parser.add_mutually_exclusive_group()
    Layout.add_argument("--layout", choices=("grouped", "individual"), default="individual")
    Layout.add_argument("--link", action="store_true", help="Link modules in each input directory together")
    Parser.add_argument("--openmp", action=argparse.BooleanOptionalAction, default=None)
    Parser.add_argument("--select", action=argparse.BooleanOptionalAction, default=True, help="Validate and measure eligible implementations during conversion")
    Parser.add_argument("--minimum-speedup", type=float, default=1.10)
    Parser.add_argument("--rank", action="store_true", help="Show analysis findings in descending static inspection priority")
    Parser.add_argument("--compile-only", action="store_true", help="Compile existing sources without PyCeler analysis, conversion or measured selection")
    Parser.add_argument("--workloads", help="JSON mapping qualified functions to representative workload factories")
    Parser.add_argument("--cache", nargs="?", const=True, default=False, metavar="DIRECTORY", help="Reuse compatible selection results and final native binaries, optionally in DIRECTORY")
    Parser.add_argument("--tune", action="store_true", help="Measure bounded thread-count and tile-size alternatives")
    Parser.add_argument("--tuning", metavar="FILE.json", help="Threads, Tiles and Budget_Seconds tuning configuration")
    Parser.add_argument("--profile", action="store_true", help="Profile isolated Python reference workloads during selection")
    Parser.add_argument("--elide-temporaries", action="store_true", help="Allow removal of nonescaping temporary allocations, including their possible allocation failures")
    Parser.add_argument("--build-check", action="store_true", help="With doctor, compile and import isolated serial and OpenMP probes")
    Parser.add_argument("--target", choices=("native", "windows-x64", "linux-x64", "linux-arm64"), default="native",
                        help="Native platform for engine/package builds; cross-compilation is not configured")
    Args = Parser.parse_args()
    if Args.build:
        os.environ["PYCELER_BUILD_DIR"] = Args.build
    Action = Args.action or ("compile" if Args.input else "engine")
    if Args.build_check and Action != "doctor":
        Parser.error("--build-check requires the doctor action")
    if Args.rank and Action != "analyze":
        Parser.error("--rank requires the analyze action")
    if Args.target != "native" and Action not in ("engine", "package", "wheel"):
        Parser.error("--target applies to engine/package builds")
    if Args.library and Action != "wheel":
        Parser.error("--library requires the wheel action")
    if Args.compile_only and Action != "compile":
        Parser.error("--compile-only requires the compile action")
    if Args.compile_only and (Args.workloads or Args.elide_temporaries or Args.tune or Args.tuning or Args.profile):
        Parser.error("--workloads, --elide-temporaries, --tune, --tuning and --profile require conversion")
    if (Args.tune or Args.tuning or Args.profile) and Action not in ("convert", "compile"):
        Parser.error("Tuning and profiling require convert or compile")
    Tuning = True if Args.tune else None
    if Args.tuning:
        try:
            Tuning = json.loads(Path(Args.tuning).read_text(encoding="utf-8"))
        except (OSError, ValueError) as Error:
            Parser.error(f"Cannot read tuning configuration: {Error}")
    Workloads = None
    if Args.workloads:
        try:
            Workloads = json.loads(Path(Args.workloads).read_text(encoding="utf-8"))
        except (OSError, ValueError) as Error:
            Parser.error(f"Cannot read workload configuration: {Error}")
    if Action == "doctor":
        if Args.input or Args.output:
            Parser.error("doctor inspects the local toolchain and does not accept --input or --output")
        Spec = importlib.util.spec_from_file_location("PyCeler_Environment_Checker", Path(__file__).resolve().parent / "PyCeler" / "Environment_Checker.py")
        Checker = importlib.util.module_from_spec(Spec)
        Spec.loader.exec_module(Checker)
        print(json.dumps(Checker.Doctor(Build_Check=Args.build_check, Mode=Args.mode, Python_Version=Args.python_version, OpenMP=Args.openmp), indent=2))
        return
    if Action == "package":
        if Args.input or Args.link or Args.layout == "grouped":
            Parser.error("package builds individual PyCeler modules from this checkout and does not accept --input or grouped linking")
        print(Build_Package(Args.output, Mode=Args.mode, Python_Version=Args.python_version, OpenMP=Args.openmp, Target=Args.target))
        return
    if Action == "wheel":
        if Args.input or Args.link or Args.layout == "grouped":
            Parser.error("wheel packages individual PyCeler modules and does not accept --input or grouped linking")
        print(Build_Wheel(Args.output, Library_Directory=Args.library, Mode=Args.mode, Python_Version=Args.python_version, OpenMP=Args.openmp, Target=Args.target))
        return
    if Action == "engine":
        if Args.input or Args.link or Args.layout == "grouped":
            Parser.error("engine builds the complete PyCeler library as individual modules; use compile for input sources")
        Outputs = _Engine(Args)
    else:
        if not Args.input:
            Parser.error(f"{Action} requires --input")
        import PyCeler
        if Action == "analyze":
            Findings = PyCeler.Analyze(Args.input, OpenMP=bool(Args.openmp), Elide_Temporaries=Args.elide_temporaries)
            if Args.rank:
                Findings = sorted(Findings, key=lambda Item: -Item.Cost_Score)
            for Item in Findings:
                print(f"{Item.Source}:{Item.Line}-{Item.End_Line} {Item.Function or '<module>'} | {Item.Change} | {Item.Reason}")
                for Diagnostic in Item.Diagnostics:
                    print(f"  {Diagnostic['Severity']} {Diagnostic['Code']} at {Diagnostic['Line']}:{Diagnostic['Column']}: {Diagnostic['Message']}")
                    print(f"    {Diagnostic['Suggestion']}")
                if Args.rank:
                    print(f"  Inspection score {Item.Cost_Score}: {Item.Cost_Reason}")
            if not Findings:
                print("No loops found. Conversion will use standard Cython compilation.")
            return
        if Action == "convert":
            Outputs = PyCeler.Convert(Args.input, Args.output, OpenMP=Args.openmp, Select=Args.select, Minimum_Speedup=Args.minimum_speedup,
                                      Mode=Args.mode, Python_Version=Args.python_version, Workloads=Workloads, Cache=Args.cache,
                                      Elide_Temporaries=Args.elide_temporaries, Tuning=Tuning, Profile=Args.profile)
        else:
            Outputs = PyCeler.Compile(Args.input, Args.output, Mode=Args.mode, Python_Version=Args.python_version,
                                      Link=Args.link or Args.layout == "grouped", OpenMP=Args.openmp, Select=Args.select, Minimum_Speedup=Args.minimum_speedup,
                                      Convert=not Args.compile_only, Workloads=Workloads, Cache=Args.cache, Elide_Temporaries=Args.elide_temporaries, Tuning=Tuning, Profile=Args.profile)
    for Item in Outputs if isinstance(Outputs, tuple) else (Outputs,):
        print(Item)
        if Action in ("convert", "compile") and not Args.compile_only and Args.select:
            _Print_Selection_Summary(Item)
    if Action == "compile" and Args.compile_only:
        print("Compilation completed with optimization analysis and measured selection disabled.")

if __name__ == "__main__":
    _Main()
