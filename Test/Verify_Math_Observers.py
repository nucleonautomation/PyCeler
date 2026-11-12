import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

def _Digest(File):
    return hashlib.sha256(File.read_bytes()).hexdigest()

def _Run():
    Parser = argparse.ArgumentParser(description="Retain one compiled math corpus and repeat its real thread/signal checks in fresh processes.")
    Parser.add_argument("--repeats", type=int, default=12)
    Parser.add_argument("--reuse", type=Path)
    Options = Parser.parse_args()
    if not 1 <= Options.repeats <= 100:
        Parser.error("Use 1..100 repeats")
    Root = Path(__file__).resolve().parents[1]
    Probe = Root / "Test" / "Math_Maps_Probe.py"
    if Options.reuse is None:
        sys.path.insert(0, str(Root))
        import PyCeler
        from Test.Math_Map_Corpus import _Math_Map_Corpus
        Runs = Root / "Test_Run"
        Runs.mkdir(exist_ok=True)
        Folder = Path(tempfile.mkdtemp(prefix="Math_Observers_", dir=Runs))
        Source = Folder / "Math_Coverage.py"
        Recipe_File = Folder / "Recipes.json"
        Text, Recipes = _Math_Map_Corpus()
        Source.write_text(Text, encoding="utf-8")
        Recipe_File.write_text(json.dumps(Recipes, indent=2), encoding="utf-8")
        os.environ["PYCELER_BUILD_DIR"] = str(Folder / "Build")
        print("Building retained corpus: " + str(Folder), flush=True)
        Binary = PyCeler.Compile(Source, Folder / "Native", Select=False, OpenMP=False)
        Manifest = dict(Binary=str(Binary), Source=str(Source), Recipes=str(Recipe_File), Build_Id=getattr(PyCeler, "__build_id__", None),
                        Build_Python=sys.version, Binary_SHA256=_Digest(Binary), Source_SHA256=_Digest(Source), Recipes_SHA256=_Digest(Recipe_File))
        (Folder / "Corpus.json").write_text(json.dumps(Manifest, indent=2), encoding="utf-8")
    else:
        Folder = Options.reuse.resolve()
        Manifest = json.loads((Folder / "Corpus.json").read_text(encoding="utf-8"))
        Binary, Source, Recipe_File = (Path(Manifest[Key]) for Key in ("Binary", "Source", "Recipes"))
        for Key, File in (("Binary", Binary), ("Source", Source), ("Recipes", Recipe_File)):
            if _Digest(File) != Manifest[Key + "_SHA256"]:
                raise ValueError("Retained corpus content changed: " + str(File))
    Results = Path(tempfile.mkdtemp(prefix="Verification_", dir=Folder))
    Report_File = Results / "Results.json"
    Report = dict(Python=sys.version, Executable=sys.executable, Platform=platform.platform(), Corpus=Manifest,
                  Probe_SHA256=_Digest(Probe), Requested_Repeats=Options.repeats, Runs=[])
    Command = [sys.executable, "-I", "-B", str(Probe), str(Binary), str(Source), str(Recipe_File)]
    print("Report: " + str(Report_File), flush=True)
    for Repeat in range(Options.repeats):
        Started = time.perf_counter()
        try:
            Process = subprocess.run(Command, capture_output=True, text=True, timeout=120)
            Row = dict(Repeat=Repeat + 1, Returncode=Process.returncode, Stdout=Process.stdout, Stderr=Process.stderr)
        except subprocess.TimeoutExpired as Error:
            Row = dict(Repeat=Repeat + 1, Returncode=None, Stdout=str(Error.stdout or ""), Stderr=str(Error.stderr or ""), Error="Probe exceeded 120 seconds")
        Row["Seconds"] = time.perf_counter() - Started
        if Row["Returncode"] == 0:
            Row["Observation"] = json.loads(Row["Stdout"])
        Report["Runs"].append(Row)
        Report["Passed"] = sum(Item["Returncode"] == 0 for Item in Report["Runs"])
        Report["Failed"] = len(Report["Runs"]) - Report["Passed"]
        Report_File.write_text(json.dumps(Report, indent=2), encoding="utf-8")
        print(f"Repeat {Repeat + 1}/{Options.repeats}: " + ("passed" if Row["Returncode"] == 0 else "FAILED"), flush=True)
    return 0 if Report["Failed"] == 0 else 1

if __name__ == "__main__":
    sys.exit(_Run())
