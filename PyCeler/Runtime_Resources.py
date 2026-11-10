from pathlib import Path

def _Resource(Name):
    if Path(Name).name != Name or not (Name.endswith(".pxi.in") or Name == "Selection_Environment.py"):
        raise ValueError(f"Unknown PyCeler runtime resource: {Name}")
    return Path(__file__).with_name(Name).read_text(encoding="utf-8")
