import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

def _Command(Name, Workspace, Architecture, Version, No_Wheels):
    Image = f"cython_linux_{'amd' if Architecture == 'amd64' else 'arm'}:latest" if Version == "3.14" else "python:3.11-trixie"
    Script = "python -m pip install -r requirements.txt numpy && python -B Compile.py && python -B Test/Run.py"
    if No_Wheels:
        Script += " --no-wheels"
    return ["docker", "run", "--rm", "--name", Name, "--label", "org.pyceler.test=true", "--platform", f"linux/{Architecture}", "--mount", f"type=bind,source={Workspace},target=/work", "--workdir", "/work", "--env", "OMP_NUM_THREADS=2", "--env", "OMP_DYNAMIC=FALSE", "--env", "PYTHONUTF8=1", "--entrypoint", "sh", Image, "-ec", Script]

def _Execute(Command, Name, Stream, Timeout):
    try:
        return subprocess.run(Command, stdout=Stream, stderr=subprocess.STDOUT, timeout=Timeout).returncode
    finally:
        try:
            Cleanup = subprocess.run(["docker", "rm", "--force", Name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
            if Cleanup.returncode and "No such container" not in Cleanup.stdout:
                print(f"Container cleanup needs attention: {Name}: {Cleanup.stdout}", file=sys.stderr)
        except (OSError, subprocess.TimeoutExpired) as Error:
            print(f"Container cleanup needs attention: {Name}: {Error}", file=sys.stderr)

def _Stage(Root, Workspace):
    Workspace.mkdir()
    for Name in ("Compile.py", "requirements.txt", "README.md", "LICENSE.md"):
        shutil.copy2(Root / Name, Workspace / Name)
    for Name in ("PyCeler", "Test"):
        shutil.copytree(Root / Name, Workspace / Name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyd", "*.so"))

def _Run():
    Parser = argparse.ArgumentParser(description="Build and test PyCeler in disposable Linux containers; retain results on the host.")
    Parser.add_argument("--architecture", choices=("amd64", "arm64", "all"), default="amd64")
    Parser.add_argument("--python", choices=("3.11", "3.14", "all"), default="3.14")
    Parser.add_argument("--no-wheels", action="store_true")
    Parser.add_argument("--timeout", type=int, default=3600, help="Maximum seconds per container, including build (default: 3600)")
    Options = Parser.parse_args()
    if Options.timeout <= 0:
        Parser.error("--timeout must be positive")
    Root = Path(__file__).resolve().parents[1]
    Output = Root / "Test_Run" / "Docker"
    Output.mkdir(parents=True, exist_ok=True)
    Run = Path(mkdtemp(prefix="Run_", dir=Output))
    print(f"Docker results: {Run}", flush=True)
    Architectures = ("amd64", "arm64") if Options.architecture == "all" else (Options.architecture,)
    Versions = ("3.11", "3.14") if Options.python == "all" else (Options.python,)
    Failed = False
    for Architecture in Architectures:
        for Version in Versions:
            Name = f"pyceler-test-{Architecture}-{Version.replace('.', '')}-{uuid4().hex[:12]}"
            Workspace = Run / f"{Architecture}-py{Version}"
            _Stage(Root, Workspace)
            Command = _Command(Name, Workspace, Architecture, Version, Options.no_wheels)
            Log = Run / f"{Architecture}-py{Version}.log"
            print(f"Running {Name}; log: {Log}", flush=True)
            with Log.open("w", encoding="utf-8") as Stream:
                print(f"Container: {Name}\nPlatform: linux/{Architecture}\nPython: {Version}\nCommand: {Command}", file=Stream, flush=True)
                try:
                    Status = _Execute(Command, Name, Stream, Options.timeout)
                except subprocess.TimeoutExpired:
                    Status = 124
                except KeyboardInterrupt:
                    print("Interrupted; container cleanup requested. Host results retained.", file=Stream, flush=True)
                    return 130
                print(f"Exit status: {Status}", file=Stream, flush=True)
            Failed = Failed or Status != 0
            print(f"{Name}: exit {Status}", flush=True)
    return 1 if Failed else 0

if __name__ == "__main__":
    sys.exit(_Run())
