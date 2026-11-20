import argparse
import ast
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
# Test support/workload for exercise hard optimization.
def _Run():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--stage", type=int, choices=(1, 2, 3), default=3)
    Parser.add_argument("--output", required=True)
    Parser.add_argument("--benchmark", action="store_true")
    Options = Parser.parse_args()
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    import PyCeler
    Folder = Path(Options.output).resolve()
    Folder.mkdir(parents=True, exist_ok=True)
    os.environ.update(PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
    Tree = ast.parse((Root / "Test/Hard_Optimization_Loops.py").read_text(encoding="utf-8"))
    Names = {"Math_Chain", "Math_Ordered"}
    if Options.stage >= 2:
        Names.update(("Math_Branch", "Math_Conditional", "Math_Branch_Output", "Math_Logical"))
    if Options.stage >= 3:
        Names.update(("Math_Nested", "Math_Nested_Branch", "Array_Nested", "Array_Volume", "Math_Volume"))
    Tree.body = [Node for Node in Tree.body if not isinstance(Node, ast.FunctionDef) or Node.name in Names]
    Source = Folder / "Hard_Cases.py"
    Source.write_text(ast.unparse(Tree) + "\n", encoding="utf-8")
    Findings = [dict(Function=Item.Function, Line=Item.Line, Classification=Item.Classification, Change=Item.Change) for Item in PyCeler.Analyze(Source, OpenMP=True)]
    for Parallel in (False, True):
        Variant = "Parallel" if Parallel else "Serial"
        Binary = PyCeler.Compile(Source, Folder / Variant, Select=False, OpenMP=Parallel)
        Result = subprocess.run([sys.executable, "-I", "-B", str(Root / "Test/Hard_Optimization_Probe.py"), str(Source), str(Binary), str(Folder / (Variant + ".json")), "parallel" if Parallel else "serial", "benchmark" if Options.benchmark else "validate"], capture_output=True, text=True, timeout=240)
        print(Variant + ": " + Result.stdout, flush=True)
        if Result.returncode:
            raise RuntimeError(Result.stderr)
    Report = dict(Build_Id=PyCeler.__build_id__, Python=sys.version, Platform=platform.platform(), Machine=platform.machine(), Stage=Options.stage, Findings=Findings)
    (Folder / "Summary.json").write_text(json.dumps(Report, indent=2), encoding="utf-8")

if __name__ == "__main__":
    _Run()
