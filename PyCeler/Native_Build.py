import json
import math
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

class _Build_Timeout(RuntimeError):

    def __init__(self, Seconds, Elapsed, Log, Cleanup):
        self.Seconds, self.Elapsed, self.Log, self.Cleanup = Seconds, Elapsed, Path(Log), Cleanup
        super().__init__(f"Native build deadline exceeded ({Seconds:g} seconds; elapsed {Elapsed:.3f} seconds). "
                         f"Owned process cleanup: {Cleanup}. Full log: {Log}")

def _Build_Deadline():
    Value = os.environ.get("PYCELER_BUILD_TIMEOUT_SECONDS")
    if Value is None or Value == "":
        return None
    try:
        Seconds = float(Value)
    except ValueError as Error:
        raise ValueError("PYCELER_BUILD_TIMEOUT_SECONDS must be zero or a finite positive number") from Error
    if not math.isfinite(Seconds) or Seconds < 0:
        raise ValueError("PYCELER_BUILD_TIMEOUT_SECONDS must be zero or a finite positive number")
    return Seconds or None

def _Deadline_Log(Stream, Record):
    Stream.write("Build deadline: " + json.dumps(Record, sort_keys=True) + "\n")
    Stream.flush()

def _Deadline_Exception_Log(Stream, Record, Error):
    try:
        _Deadline_Log(Stream, Record)
    except OSError as Log_Error:
        if Error is None:
            raise
        Error.add_note("Build deadline log could not be written: " + str(Log_Error))

def _Run_Bounded_Build(Command, Directory, Stream, Seconds):
    Started = time.monotonic()
    _Deadline_Log(Stream, dict(Status="starting", Seconds=Seconds, Ownership="job" if os.name == "nt" else "session"))
    try:
        Runner = _Windows_Bounded_Build if os.name == "nt" else _Posix_Bounded_Build
        Record = Runner(Command, Directory, Stream, Started + Seconds)
    except BaseException as Error:
        _Deadline_Exception_Log(Stream, dict(Status="interrupted" if isinstance(Error, (KeyboardInterrupt, SystemExit)) else "failed",
                                            Elapsed=time.monotonic() - Started, Error=str(Error)), Error)
        raise
    Record["Seconds"], Record["Elapsed"] = Seconds, time.monotonic() - Started
    _Deadline_Log(Stream, Record)
    if Record["Timed_Out"]:
        raise _Build_Timeout(Seconds, Record["Elapsed"], Stream.name, Record["Cleanup"])
    if Record["Cleanup"] != "complete":
        raise RuntimeError(f"Native build owned-process cleanup failed: {Record['Cleanup']}. Full log: {Stream.name}")
    return Record["Return_Code"]

def _Windows_Build_API():
    import ctypes as C
    from ctypes import wintypes as W
    class _Startup(C.Structure):
        _fields_ = [("cb", W.DWORD), ("lpReserved", W.LPWSTR), ("lpDesktop", W.LPWSTR), ("lpTitle", W.LPWSTR),
                    ("dwX", W.DWORD), ("dwY", W.DWORD), ("dwXSize", W.DWORD), ("dwYSize", W.DWORD),
                    ("dwXCountChars", W.DWORD), ("dwYCountChars", W.DWORD), ("dwFillAttribute", W.DWORD),
                    ("dwFlags", W.DWORD), ("wShowWindow", W.WORD), ("cbReserved2", W.WORD),
                    ("lpReserved2", C.POINTER(W.BYTE)), ("hStdInput", W.HANDLE), ("hStdOutput", W.HANDLE), ("hStdError", W.HANDLE)]
    class _Startup_Extended(C.Structure):
        _fields_ = [("StartupInfo", _Startup), ("lpAttributeList", C.c_void_p)]
    class _Process(C.Structure):
        _fields_ = [("hProcess", W.HANDLE), ("hThread", W.HANDLE), ("dwProcessId", W.DWORD), ("dwThreadId", W.DWORD)]
    class _Limits(C.Structure):
        _fields_ = [("PerProcessUserTimeLimit", C.c_longlong), ("PerJobUserTimeLimit", C.c_longlong), ("LimitFlags", W.DWORD),
                    ("MinimumWorkingSetSize", C.c_size_t), ("MaximumWorkingSetSize", C.c_size_t), ("ActiveProcessLimit", W.DWORD),
                    ("Affinity", C.c_size_t), ("PriorityClass", W.DWORD), ("SchedulingClass", W.DWORD)]
    class _Io(C.Structure):
        _fields_ = [(Name, C.c_ulonglong) for Name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]
    class _Extended_Limits(C.Structure):
        _fields_ = [("BasicLimitInformation", _Limits), ("IoInfo", _Io), ("ProcessMemoryLimit", C.c_size_t),
                    ("JobMemoryLimit", C.c_size_t), ("PeakProcessMemoryUsed", C.c_size_t), ("PeakJobMemoryUsed", C.c_size_t)]
    class _Accounting(C.Structure):
        _fields_ = [("TotalUserTime", C.c_longlong), ("TotalKernelTime", C.c_longlong), ("ThisPeriodTotalUserTime", C.c_longlong),
                    ("ThisPeriodTotalKernelTime", C.c_longlong), ("TotalPageFaultCount", W.DWORD), ("TotalProcesses", W.DWORD),
                    ("ActiveProcesses", W.DWORD), ("TotalTerminatedProcesses", W.DWORD)]
    Api = C.WinDLL("kernel32", use_last_error=True)
    Functions = {
        "CreateJobObjectW": (W.HANDLE, [C.c_void_p, W.LPCWSTR]),
        "SetInformationJobObject": (W.BOOL, [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]),
        "InitializeProcThreadAttributeList": (W.BOOL, [C.c_void_p, W.DWORD, W.DWORD, C.POINTER(C.c_size_t)]),
        "UpdateProcThreadAttribute": (W.BOOL, [C.c_void_p, W.DWORD, C.c_size_t, C.c_void_p, C.c_size_t, C.c_void_p, C.c_void_p]),
        "DeleteProcThreadAttributeList": (None, [C.c_void_p]),
        "GetCurrentProcess": (W.HANDLE, []),
        "DuplicateHandle": (W.BOOL, [W.HANDLE, W.HANDLE, W.HANDLE, C.POINTER(W.HANDLE), W.DWORD, W.BOOL, W.DWORD]),
        "CreateProcessW": (W.BOOL, [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD, C.c_void_p, W.LPCWSTR, C.POINTER(_Startup), C.POINTER(_Process)]),
        "WaitForSingleObject": (W.DWORD, [W.HANDLE, W.DWORD]),
        "GetExitCodeProcess": (W.BOOL, [W.HANDLE, C.POINTER(W.DWORD)]),
        "TerminateJobObject": (W.BOOL, [W.HANDLE, W.UINT]),
        "QueryInformationJobObject": (W.BOOL, [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p]),
        "CloseHandle": (W.BOOL, [W.HANDLE])}
    for Name, (Result, Arguments) in Functions.items():
        Function = getattr(Api, Name)
        Function.restype, Function.argtypes = Result, Arguments
    return C, W, Api, _Startup, _Startup_Extended, _Process, _Extended_Limits, _Accounting

def _Windows_Job_Cleanup(Api, C, Job, Accounting):
    if not Api.TerminateJobObject(Job, 1):
        return "TerminateJobObject failed: " + str(C.WinError(C.get_last_error()))
    Deadline = time.monotonic() + 5.0
    State = Accounting()
    while True:
        if not Api.QueryInformationJobObject(Job, 1, C.byref(State), C.sizeof(State), None):
            return "QueryInformationJobObject failed: " + str(C.WinError(C.get_last_error()))
        if State.ActiveProcesses == 0:
            return "complete"
        if time.monotonic() >= Deadline:
            return f"{State.ActiveProcesses} owned job processes did not exit within cleanup grace"
        time.sleep(0.01)

def _Windows_Bounded_Build(Command, Directory, Stream, Deadline):
    import msvcrt
    C, W, Api, Startup, Startup_Extended, Process, Extended_Limits, Accounting = _Windows_Build_API()
    Job, Handles, Attributes, Initialized, Launched, Cleaned = None, [], None, False, False, False
    Information = Process()
    try:
        Job = Api.CreateJobObjectW(None, None)
        if not Job:
            raise C.WinError(C.get_last_error())
        Limits = Extended_Limits()
        Limits.BasicLimitInformation.LimitFlags = 0x2000
        if not Api.SetInformationJobObject(Job, 9, C.byref(Limits), C.sizeof(Limits)):
            raise C.WinError(C.get_last_error())
        Size = C.c_size_t()
        Api.InitializeProcThreadAttributeList(None, 2, 0, C.byref(Size))
        if not Size.value:
            raise C.WinError(C.get_last_error())
        Attributes = C.create_string_buffer(Size.value)
        if not Api.InitializeProcThreadAttributeList(Attributes, 2, 0, C.byref(Size)):
            raise C.WinError(C.get_last_error())
        Initialized = True
        Jobs = (W.HANDLE * 1)(Job)
        if not Api.UpdateProcThreadAttribute(Attributes, 0, 0x2000D, Jobs, C.sizeof(Jobs), None, None):
            raise RuntimeError("A bounded build requires creation-time Windows job assignment") from C.WinError(C.get_last_error())
        Current = Api.GetCurrentProcess()
        with open(os.devnull, "rb") as Input:
            for File in (Input, Stream):
                Handle = W.HANDLE()
                if not Api.DuplicateHandle(Current, msvcrt.get_osfhandle(File.fileno()), Current, C.byref(Handle), 0, True, 2):
                    raise C.WinError(C.get_last_error())
                Handles.append(Handle.value)
        Inherited = (W.HANDLE * len(Handles))(*Handles)
        if not Api.UpdateProcThreadAttribute(Attributes, 0, 0x20002, Inherited, C.sizeof(Inherited), None, None):
            raise C.WinError(C.get_last_error())
        Start = Startup_Extended()
        Start.StartupInfo.cb = C.sizeof(Start)
        Start.StartupInfo.dwFlags, Start.StartupInfo.wShowWindow = 0x101, 0
        Start.StartupInfo.hStdInput, Start.StartupInfo.hStdOutput, Start.StartupInfo.hStdError = Handles[0], Handles[1], Handles[1]
        Start.lpAttributeList = C.cast(Attributes, C.c_void_p)
        Executable = shutil.which(Command[0])
        if Executable is None:
            raise FileNotFoundError(Command[0])
        Arguments = C.create_unicode_buffer(subprocess.list2cmdline(Command))
        if time.monotonic() >= Deadline:
            return dict(Return_Code=None, Timed_Out=True, Cleanup="complete", Launched=False)
        if not Api.CreateProcessW(Executable, Arguments, None, None, True, 0x80000 | 0x8000000, None, str(Directory), C.cast(C.byref(Start), C.POINTER(Startup)), C.byref(Information)):
            raise RuntimeError("Bounded build worker creation failed before execution: " + str(C.WinError(C.get_last_error())))
        Launched = True
        while Handles:
            Api.CloseHandle(Handles.pop())
        Timed_Out, Return_Code = False, None
        while True:
            Remaining = Deadline - time.monotonic()
            Wait = Api.WaitForSingleObject(Information.hProcess, math.ceil(max(0, min(0.05, Remaining)) * 1000))
            if Wait == 0:
                Code = W.DWORD()
                if not Api.GetExitCodeProcess(Information.hProcess, C.byref(Code)):
                    raise C.WinError(C.get_last_error())
                Return_Code = Code.value
                break
            if Wait != 258:
                raise C.WinError(C.get_last_error())
            if Remaining <= 0:
                Timed_Out = True
                break
        Cleanup = _Windows_Job_Cleanup(Api, C, Job, Accounting)
        Cleaned = True
        return dict(Return_Code=Return_Code, Timed_Out=Timed_Out, Cleanup=Cleanup, Launched=True)
    finally:
        Error = sys.exc_info()[1]
        try:
            if Launched and not Cleaned:
                Cleanup = _Windows_Job_Cleanup(Api, C, Job, Accounting)
                _Deadline_Exception_Log(Stream, dict(Status="exception cleanup", Cleanup=Cleanup), Error)
        finally:
            for Handle in (Information.hThread, Information.hProcess, *Handles):
                if Handle:
                    Api.CloseHandle(Handle)
            if Initialized:
                Api.DeleteProcThreadAttributeList(Attributes)
            if Job:
                Api.CloseHandle(Job)

def _Posix_Child_State(Process):
    try:
        return os.waitid(os.P_PID, Process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError as Error:
        raise RuntimeError("Build child ownership was lost to an external reaper; no process-group signal was sent") from Error

def _Posix_Group_Signal(Process, Signal):
    _Posix_Child_State(Process)
    try:
        os.killpg(Process.pid, Signal)
    except ProcessLookupError:
        pass

def _Posix_Group_Cleanup(Process, Graceful):
    import signal
    try:
        if Graceful:
            _Posix_Group_Signal(Process, signal.SIGTERM)
            End = time.monotonic() + 0.25
            while time.monotonic() < End and _Posix_Child_State(Process) is None:
                time.sleep(0.01)
        _Posix_Group_Signal(Process, signal.SIGKILL)
        Process.wait(timeout=5)
        End = time.monotonic() + 5.0
        while True:
            try:
                os.killpg(Process.pid, 0)
            except ProcessLookupError:
                return "complete"
            if time.monotonic() >= End:
                return "owned process group exit could not be confirmed within cleanup grace"
            time.sleep(0.01)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as Error:
        return str(Error)

def _Posix_Bounded_Build(Command, Directory, Stream, Deadline):
    import signal
    if not all(hasattr(os, Name) for Name in ("waitid", "WNOWAIT", "WEXITED", "WNOHANG", "P_PID", "killpg")):
        raise RuntimeError("Bounded builds require POSIX waitid/WNOWAIT and owned process groups")
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        raise RuntimeError("Bounded builds require default SIGCHLD handling and exclusive child reaping")
    if time.monotonic() >= Deadline:
        return dict(Return_Code=None, Timed_Out=True, Cleanup="complete", Launched=False)
    Process = subprocess.Popen(Command, cwd=Directory, stdin=subprocess.DEVNULL, stdout=Stream, stderr=subprocess.STDOUT, start_new_session=True)
    Cleaned = False
    try:
        while True:
            State = _Posix_Child_State(Process)
            if State is not None:
                Timed_Out = False
                break
            if time.monotonic() >= Deadline:
                Timed_Out = True
                break
            time.sleep(min(0.01, max(0, Deadline - time.monotonic())))
        Cleanup = _Posix_Group_Cleanup(Process, Timed_Out)
        Cleaned = True
        return dict(Return_Code=Process.returncode, Timed_Out=Timed_Out, Cleanup=Cleanup, Launched=True)
    finally:
        if not Cleaned:
            Error = sys.exc_info()[1]
            Cleanup = _Posix_Group_Cleanup(Process, True)
            _Deadline_Exception_Log(Stream, dict(Status="exception cleanup", Cleanup=Cleanup), Error)

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
    Deadline = _Build_Deadline()
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
            Worker = [*Command, "-I", "-B", "-c", Program, str(Path(__file__).resolve().parent), str(Spec)]
            if Deadline is None:
                Return_Code = subprocess.run(Worker, cwd=Stage, stdout=Stream, stderr=subprocess.STDOUT).returncode
            else:
                Return_Code = _Run_Bounded_Build(Worker, Stage, Stream, Deadline)
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

def _Interpreter_ABI():
    Tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        Tag += "t"
    if sysconfig.get_config_var("Py_DEBUG") or hasattr(sys, "gettotalrefcount"):
        Tag += "d"
    return Tag

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
                       ABI_Tag="abi3" if Stable else _Interpreter_ABI(), GIL_Disabled=bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
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
