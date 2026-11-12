import argparse
import hashlib
import json
import platform
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

_Root = Path(__file__).resolve().parents[1]
if str(_Root) not in sys.path:
    sys.path.insert(0, str(_Root))

def _Run(Inputs, Output):
    import PyCeler
    from PyCeler.Common_Analysis import _Capability_Matrix
    Files = []
    for Input in Inputs:
        Input = Path(Input).resolve()
        Files.extend(sorted(File for File in Input.rglob("*") if File.suffix in (".py", ".pyx", ".pxi")) if Input.is_dir() else (Input,))
    Files = tuple(dict.fromkeys(Files))
    Output.mkdir(parents=True, exist_ok=True)
    Records = []
    for Index, File in enumerate(Files):
        Data = File.read_bytes()
        Snapshot = Output / "Sources" / (str(Index).zfill(4) + "_" + File.name)
        Snapshot.parent.mkdir(parents=True, exist_ok=True)
        Snapshot.write_bytes(Data)
        Findings = PyCeler.Analyze(File, OpenMP=True)
        Records.append(dict(Source=str(File), Snapshot=str(Snapshot), SHA256=hashlib.sha256(Data).hexdigest(),
                            Findings=[asdict(Item) for Item in Findings], Capabilities=_Capability_Matrix(Findings)))
    Report = dict(Version=1, PyCeler=PyCeler.__version__, Python=sys.version, Platform=platform.platform(),
                  Execution="static_source_only", Native_Entry="not_observed", Inputs=Records)
    Pathname = Output / "Coverage.json"
    Pathname.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(Pathname)
    return Pathname

def _Main():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--input", action="append")
    Parser.add_argument("--output", type=Path)
    Arguments = Parser.parse_args()
    Inputs = Arguments.input or [str(_Root / "Test" / Name) for Name in ("Coverage_Loops.py", "Numeric_Loops.py", "Scalar_Regions.py", "Structural_Loops.py", "Classic_Transport_Loops.py")]
    Base = _Root / "Test_Run"
    Base.mkdir(exist_ok=True)
    Output = Arguments.output or Path(tempfile.mkdtemp(prefix="Coverage_", dir=Base))
    _Run(Inputs, Output)

if __name__ == "__main__":
    _Main()
