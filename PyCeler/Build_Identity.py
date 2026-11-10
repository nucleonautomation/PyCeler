import hashlib
import importlib.metadata
import json
from pathlib import Path

def _Digest(Value):
    return hashlib.sha256(json.dumps(Value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

def _Source_State(Root):
    Root = Path(Root).resolve()
    Package = Root / "PyCeler"
    Paths = [Root / "Compile.py", *sorted(File for File in Package.iterdir() if File.is_file() and File.suffix in (".py", ".pyx", ".pxi", ".in"))]
    if (Root / "requirements.txt").is_file():
        Paths.append(Root / "requirements.txt")
    Sources = {File.relative_to(Root).as_posix(): hashlib.sha256(File.read_bytes()).hexdigest() for File in Paths}
    Dependencies = {}
    for Name in ("Cython", "setuptools", "numpy"):
        try:
            Dependencies[Name] = importlib.metadata.version(Name)
        except importlib.metadata.PackageNotFoundError:
            Dependencies[Name] = None
    return dict(Source_Fingerprint=_Digest(dict(Sources=Sources, Dependencies=Dependencies)), Sources=Sources, Dependencies=Dependencies)

def _Verify_Development(Root, Package):
    Root, Package = Path(Root).resolve(), Path(Package).resolve()
    Hint = f"Run python -B Compile.py from {Root}."
    try:
        Report = json.loads((Package.parent / "PyCeler.manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as Error:
        raise ImportError(f"PyCeler build provenance is missing or unreadable at {Package}. {Hint}") from Error
    Current = _Source_State(Root)
    if Report.get("Source_Fingerprint") != Current["Source_Fingerprint"]:
        Old = Report.get("Sources", {})
        Changed = sorted(Name for Name in set(Old) | set(Current["Sources"]) if Old.get(Name) != Current["Sources"].get(Name))
        Detail = ", ".join(Changed[:6]) or "build dependencies"
        raise ImportError(f"PyCeler's compiled package is stale at {Package}; changed: {Detail}. {Hint}")
    Files = Report.get("Files")
    if not isinstance(Files, dict) or not isinstance(Report.get("Build_Id"), str):
        raise ImportError(f"PyCeler build provenance is incomplete at {Package}. {Hint}")
    Actual = {File.relative_to(Package.parent).as_posix() for File in Package.iterdir() if File.is_file()}
    if Actual != set(Files):
        raise ImportError(f"PyCeler's compiled package inventory differs from its provenance at {Package}. {Hint}")
    for Name, Expected in Files.items():
        File = Package.parent / Name
        if not File.resolve().is_relative_to(Package) or not File.is_file() or hashlib.sha256(File.read_bytes()).hexdigest() != Expected:
            raise ImportError(f"PyCeler's compiled package has a missing or modified artifact: {Name}. {Hint}")
    return Report
