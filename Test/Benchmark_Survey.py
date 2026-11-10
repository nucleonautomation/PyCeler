import ast
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from Survey_Source import Write_Survey

def _Timed(Label, Action, Durations):
    print(Label, flush=True)
    Start = perf_counter()
    Result = Action()
    Durations[Label] = perf_counter() - Start
    return Result

def _Digest(File):
    return hashlib.sha256(File.read_bytes()).hexdigest()

def _Selection(File, Findings):
    Selection = json.loads(File.read_text(encoding="utf-8"))
    Items = Selection["Items"]
    Covered = [Line for Item in Items for Line in Item["Loop_Lines"]]
    Skipped = [Item["Line"] for Item in Selection["Skipped"]]
    if sorted(Covered + Skipped) != sorted(Item.Line for Item in Findings):
        raise AssertionError("Selection report does not account for every analyzed loop")
    Wins = Counter(Case["Winner"] for Item in Items for Case in Item["Cases"])
    return dict(Items=len(Items), Covered_Loops=len(Covered), Skipped_Loops=len(Skipped), Case_Winners=dict(Wins),
                Candidates={Name: Build["Status"] for Name, Build in Selection["Builds"].items()},
                Native_Winners=[Item["Function"] for Item in Items if any(Case["Winner"] != "Python" for Case in Item["Cases"])],
                Inconclusive=[Item["Function"] for Item in Items if not Item["Cases"] or any(not Case["Timings"] for Case in Item["Cases"])])

def _Plain_Cython(Source, Output):
    from PyCeler.Native_Build import _Build, _Workspace
    with _Workspace() as Stage:
        Sources = Stage / "Sources"
        Sources.mkdir()
        Relative = Path("Survey_Unoptimized.pyx")
        shutil.copyfile(Source, Sources / Relative)
        return _Build(Stage, [Relative], Output, "abi", "3.11", False, False)[0]

def _Build_Survey():
    os.environ.update(OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
    import Cython
    import numpy
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    import PyCeler
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Run = Path(tempfile.mkdtemp(prefix="Survey_", dir=Runs))
    print(Run, flush=True)
    os.environ["PYCELER_BUILD_DIR"] = str(Run / "Build")
    Source = Write_Survey(Run / "Survey_Workload.py")
    Text = Source.read_text(encoding="utf-8")
    Tree = ast.parse(Text)
    Report = dict(Platform=platform.platform(), CPU=platform.processor(), Logical_CPUs=os.cpu_count(), Python=sys.version,
                  Cython=Cython.__version__, NumPy=numpy.__version__, PyCeler=PyCeler.__version__, ABI="3.11", OpenMP_Threads=2,
                  Source=Source.name, SHA256=_Digest(Source), Lines=len(Text.splitlines()), Loop_Count=sum(isinstance(Node, (ast.For, ast.While)) for Node in ast.walk(Tree)),
                  Function_Count=sum(isinstance(Node, ast.FunctionDef) for Node in ast.walk(Tree)), Seconds={})
    Path_Report = Run / "Results.json"
    Path_Report.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    Before = set(Run.iterdir())
    Findings = _Timed("Analyze", lambda: PyCeler.Analyze(Source, OpenMP=True), Report["Seconds"])
    if set(Run.iterdir()) != Before or _Digest(Source) != Report["SHA256"] or len(Findings) != Report["Loop_Count"]:
        raise AssertionError("Read-only analysis or loop coverage failed")
    (Run / "Analysis.json").write_text(json.dumps([asdict(Item) for Item in Findings], indent=2), encoding="utf-8")
    Generated = _Timed("Convert", lambda: PyCeler.Convert(Source, Run / "Converted"), Report["Seconds"])
    Report["Convert_Selection"] = _Selection(Generated.with_suffix(".selection.json"), Findings)
    Binary = _Timed("Compile", lambda: PyCeler.Compile(Source, Run / "Native"), Report["Seconds"])
    Report["Compile_Selection"] = _Selection(Binary.with_suffix(".selection.json"), Findings)
    Plain = _Timed("Plain_Cython_Compile", lambda: _Plain_Cython(Source, Run / "Plain"), Report["Seconds"])
    if _Digest(Source) != Report["SHA256"]:
        raise AssertionError("Conversion or compilation modified the input")
    Report.update(Generated=str(Generated.relative_to(Run)), Binary=str(Binary.relative_to(Run)), Binary_Bytes=Binary.stat().st_size,
                  Plain_Binary=str(Plain.relative_to(Run)))
    Path_Report.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    return Run

def _Main():
    Run = _Build_Survey()
    subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("Survey_Verification.py")), str(Run)], check=True)
    print(Run / "Results.json", flush=True)

if __name__ == "__main__":
    _Main()
