import importlib.metadata
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

def _Backend():
    if __package__:
        from . import Native_Build
        return Native_Build
    File = Path(__file__).with_name("Native_Build.py")
    Spec = importlib.util.spec_from_file_location("PyCeler_Doctor_Backend", File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Dependency_Versions():
    Results = {}
    for Name in ("Cython", "numpy", "setuptools"):
        try:
            Results[Name] = dict(Status="installed", Version=importlib.metadata.version(Name))
        except importlib.metadata.PackageNotFoundError:
            Results[Name] = dict(Status="missing", Version=None)
    return Results

def _Compiler_Paths():
    Names = ("cl", "link", "gcc", "g++", "clang", "clang++")
    Found = {Name: shutil.which(Name) for Name in Names}
    Visual_Studio = []
    if os.name == "nt":
        for Base in dict.fromkeys(os.environ.get(Name) for Name in ("ProgramFiles", "ProgramFiles(x86)")):
            if Base:
                Root = Path(Base) / "Microsoft Visual Studio"
                Visual_Studio.extend(str(File) for File in Root.glob("*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe") if File.is_file())
    return dict(On_Path=Found, MSVC_Installations=sorted(set(Visual_Studio)),
                Required="MSVC Build Tools and Windows SDK" if os.name == "nt" else "GCC, Python development headers and an OpenMP runtime")

def _Probe_Toolchain(Backend, Parallel, Mode, Python_Version):
    Name = "Toolchain_OpenMP" if Parallel else "Toolchain_Serial"
    Body = "from cython.parallel cimport prange\n" if Parallel else ""
    Loop = "prange(8, nogil=True, schedule='static')" if Parallel else "range(8)"
    Body += "def Probe():\n    cdef long Index, Total = 0\n    for Index in " + Loop + ":\n        Total += Index\n    return Total\n"
    with Backend._Workspace() as Stage:
        Sources = Stage / "Sources"
        Sources.mkdir()
        Relative = Path(Name + ".pyx")
        (Sources / Relative).write_text(Body, encoding="utf-8")
        Log = Stage.parent / "Logs" / (Stage.name + ".log")
        try:
            Binary = Backend._Build(Stage, [Relative], Stage / "Loaded", Mode, Python_Version, False, Parallel)[0]
            Command, Version = Backend._Interpreter("abi" if Mode == "auto" else Mode, Python_Version)
            Program = "import sys\nsys.path.insert(0, sys.argv[1])\nfrom " + Name + " import Probe\nassert Probe() == 28\n"
            Process = subprocess.run([*Command, "-I", "-B", "-c", Program, str(Binary.parent)], capture_output=True, text=True, timeout=30)
            if Process.returncode:
                return dict(Status="import failed", Diagnostic=(Process.stderr or Process.stdout)[-8000:], Build_Log=str(Log))
            return dict(Status="passed", Build_Log=str(Log), Python_Target=Version)
        except (OSError, ValueError, RuntimeError, ImportError, subprocess.TimeoutExpired) as Error:
            return dict(Status="failed", Diagnostic=str(Error)[-8000:], Build_Log=str(Log))

def Doctor(*, Build_Check=False, Mode="abi", Python_Version=None, OpenMP=None):
    if type(Build_Check) is not bool or (OpenMP is not None and type(OpenMP) is not bool):
        raise ValueError("Build_Check must be boolean and OpenMP must be None or boolean")
    Backend = _Backend()
    try:
        Command, Version = Backend._Interpreter("abi" if Mode == "auto" else Mode, Python_Version)
        Interpreter = dict(Status="configured", Command=Command, Target=Version)
    except ValueError as Error:
        Interpreter = dict(Status="invalid", Diagnostic=str(Error))
    Report = dict(Format="PyCeler environment 1", Platform=platform.platform(), Machine=platform.machine(),
                  Python=dict(Executable=sys.executable, Version=sys.version, Requested=Interpreter,
                              Headers=sysconfig.get_path("include"), Free_Threaded=bool(sysconfig.get_config_var("Py_GIL_DISABLED"))),
                  Dependencies=_Dependency_Versions(), Compiler=_Compiler_Paths(),
                  OpenMP_Environment={Name: os.environ.get(Name) for Name in ("OMP_NUM_THREADS", "OMP_DYNAMIC", "OMP_PROC_BIND", "OMP_PLACES")},
                  Build_Check=Build_Check, Candidates={})
    Machine = sysconfig.get_platform().lower().replace("_", "-").removeprefix("win-").removeprefix("linux-")
    if Machine == "x86-64":
        Machine = "x86_64"
    Architecture = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(Machine, Machine)
    Host = platform.system().lower() + "-" + Architecture
    Report["Target"] = dict(Native=Host, Supported=Host in ("windows-x64", "linux-x64", "linux-arm64"),
                            Cross_Compilation=False, Requirement="Build each target on its native platform and interpreter architecture")
    for Name, Parallel in (("Serial", False), ("OpenMP", True)):
        if Parallel and OpenMP is False:
            Report["Candidates"][Name] = dict(Status="disabled")
        elif not Build_Check:
            Report["Candidates"][Name] = dict(Status="not run", Reason="Use --build-check to compile and import an isolated probe")
        elif Interpreter["Status"] != "configured":
            Report["Candidates"][Name] = dict(Status="not run", Reason="Invalid interpreter configuration")
        else:
            try:
                Report["Candidates"][Name] = _Probe_Toolchain(Backend, Parallel, Mode, Python_Version)
            except (OSError, ValueError, RuntimeError, ImportError, subprocess.TimeoutExpired) as Error:
                Report["Candidates"][Name] = dict(Status="failed", Diagnostic=str(Error)[-8000:])
    return Report
