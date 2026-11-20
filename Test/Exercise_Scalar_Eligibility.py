import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
# Test support/workload for exercise scalar eligibility.
def Main():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--output", required=True)
    Options = Parser.parse_args()
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    import PyCeler
    from Test.Scalar_Eligibility_Corpus import Corpus
    Folder = Path(Options.output).resolve()
    Folder.mkdir(parents=True, exist_ok=True)
    Source = Folder / "Eligibility.py"
    Source.write_text(Corpus()[0], encoding="utf-8")
    Findings = [dict(Function=Item.Function, Line=Item.Line, Change=Item.Change, Classification=Item.Classification) for Item in PyCeler.Analyze(Source, OpenMP=True)]
    assert sum(Item["Change"] != "Keep original loop" for Item in Findings) == 160
    os.environ.update(PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2")
    Reports = {}
    for Parallel in (False, True):
        Variant = "Parallel" if Parallel else "Serial"
        Binary = PyCeler.Compile(Source, Folder / Variant, Select=False, OpenMP=Parallel)
        Destination = Folder / (Variant + ".json")
        Result = subprocess.run([sys.executable, "-I", "-B", str(Root / "Test/Scalar_Eligibility_Probe.py"), str(Source), str(Binary), str(Destination)], capture_output=True, text=True, timeout=120)
        if Result.returncode:
            raise RuntimeError(Result.stdout + Result.stderr)
        Reports[Variant] = json.loads(Destination.read_text(encoding="utf-8"))
        print(Variant + ": " + Result.stdout, flush=True)
    Report = dict(Build_Id=PyCeler.__build_id__, Python=sys.version, Platform=platform.platform(), Machine=platform.machine(), Findings=Findings, Reports=Reports)
    (Folder / "Summary.json").write_text(json.dumps(Report, indent=2), encoding="utf-8")

if __name__ == "__main__":
    Main()
