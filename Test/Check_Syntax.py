import ast
import importlib.util
import json
import platform
import sys
import tempfile
from pathlib import Path

def _Run():
    import Cython
    from Cython.Compiler.Main import CompilationOptions, compile as Translate, default_options
    Root = Path(__file__).resolve().parents[1]
    Files = [*Root.glob("*.py"), *(Root / "PyCeler").glob("*.py"), *(Root / "Test").glob("*.py")]
    for File in Files:
        ast.parse(File.read_text(encoding="utf-8-sig"), filename=str(File))
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Folder = Path(tempfile.mkdtemp(prefix="Cython_Review_", dir=Runs))
    Spec = importlib.util.spec_from_file_location("Compile_Review", Root / "Compile.py")
    Builder = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Builder)
    Paths = Builder._Stage_Package(Root, Folder)
    Backend = Builder._Backend(Root)
    Results = []
    for Relative in Paths:
        Source = Folder / "Sources" / Relative
        Output = Folder / "Generated" / Relative.with_suffix(".c")
        Output.parent.mkdir(parents=True, exist_ok=True)
        Options = CompilationOptions(default_options, output_file=str(Output), compiler_directives=dict(language_level=3, annotation_typing=False, infer_types=False, binding=True),
                                     include_path=[str(Source.parent), str(Folder / "Sources")])
        with Backend._Cython_Compatibility():
            Result = Translate(str(Source), options=Options, full_module_name="PyCeler." + Relative.stem)
        Results.append(dict(Source=str(Relative), Errors=Result.num_errors))
        print(f"{Relative}: {Result.num_errors} translation errors", flush=True)
    Report = dict(Verification="Python AST and Cython-to-C translation only; no native compiler, tests or benchmark execution",
                  Platform=platform.platform(), Python=sys.version, Cython=Cython.__version__, Python_Files=len(Files), Results=Results)
    Target = Folder / "Results.json"
    Target.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(f"Report: {Target}", flush=True)
    return 1 if any(Item["Errors"] for Item in Results) else 0

if __name__ == "__main__":
    raise SystemExit(_Run())
