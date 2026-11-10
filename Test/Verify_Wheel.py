import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

def _Verify(Wheel, Python=None, Output=None):
    Root = Path(__file__).resolve().parents[1]
    Wheel = Path(Wheel).resolve()
    Python = str(Python or sys.executable)
    if not Wheel.is_file() or Wheel.suffix != ".whl":
        raise ValueError(f"Expected an existing wheel: {Wheel}")
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Work = Path(Output).resolve() if Output is not None else Path(tempfile.mkdtemp(prefix="Installed_Wheel_", dir=Runs))
    Work.mkdir(parents=True, exist_ok=True)
    Library = Work / "Installed"
    if Library.exists():
        raise ValueError(f"Use a fresh wheel-test output directory: {Work}")
    Environment = dict(os.environ, PYTHONNOUSERSITE="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    Commands = ([Python, "-I", "-B", "-m", "pip", "install", "--no-index", "--no-deps", "--target", str(Library), str(Wheel)],
                [Python, "-I", "-B", str(Root / "Test" / "Wheel_Probe.py"), str(Library), str(Work)])
    for Index, Command in enumerate(Commands):
        Result = subprocess.run(Command, cwd=Work, env=Environment, capture_output=True, text=True, timeout=240)
        (Work / f"Step_{Index}.log").write_text(Result.stdout + Result.stderr, encoding="utf-8")
        if Result.returncode:
            raise RuntimeError(f"Installed wheel verification failed; see {Work / f'Step_{Index}.log'}\n{Result.stdout}{Result.stderr}")
    Report = json.loads((Work / "Installed_Wheel.json").read_text(encoding="utf-8"))
    Report.update(Wheel=str(Wheel), Wheel_SHA256=hashlib.sha256(Wheel.read_bytes()).hexdigest())
    (Work / "Installed_Wheel.json").write_text(json.dumps(Report, indent=2), encoding="utf-8")
    return Work / "Installed_Wheel.json"

def _Main():
    Parser = argparse.ArgumentParser(description="Install a wheel into an isolated directory and exercise the native public pipeline.")
    Parser.add_argument("wheel", type=Path)
    Parser.add_argument("--python", help="Interpreter executable; permits stable-ABI cross-interpreter checks")
    Parser.add_argument("--output", type=Path)
    Args = Parser.parse_args()
    print(_Verify(Args.wheel, Args.python, Args.output), flush=True)

if __name__ == "__main__":
    _Main()
