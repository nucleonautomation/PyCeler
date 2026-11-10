def _Built_Package_Path():
    import os
    from importlib.machinery import EXTENSION_SUFFIXES
    from pathlib import Path
    Source = Path(__file__).resolve().parent
    if not (Source / "Engine.pyx").is_file():
        return None
    Configured = os.environ.get("PYCELER_LIBRARY_DIR")
    Library = Path(Configured).expanduser().resolve() if Configured else Source.parent / "Build" / "Lib"
    Package = Library if Library.name.casefold() == "pyceler" else Library / "PyCeler"
    if not (Package / "__init__.py").is_file() or not all(any((Package / (Name + Suffix)).is_file() for Suffix in EXTENSION_SUFFIXES) for Name in ("Engine", "Loop_Detector")):
        raise ImportError(f"PyCeler's compiled package is missing or incomplete at {Package}. Run python -B Compile.py from {Source.parent}. For a custom build, set PYCELER_LIBRARY_DIR to its library directory.")
    return Package

_Built_Path = _Built_Package_Path()
if _Built_Path is not None:
    __path__[:] = [str(_Built_Path)]
del _Built_Path

from .Loop_Detector import Loop_Finding
from .Engine import Analyze, Convert, Compile

__version__ = "0.1.0"
__all__ = ["Analyze", "Convert", "Compile", "Loop_Finding"]
