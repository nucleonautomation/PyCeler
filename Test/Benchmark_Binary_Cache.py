import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from time import perf_counter

def _Main():
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    import PyCeler
    Run = Path(tempfile.mkdtemp(prefix="Binary_Cache_Benchmark_", dir=Root / "Test_Run"))
    os.environ["PYCELER_BUILD_DIR"] = str(Run / "Build")
    Source = Run / "Large_Module.py"
    Source.write_text("\n".join(f"def Function_{Index}(Value):\n    return Value + {Index}\n" for Index in range(500)), encoding="utf-8")
    Times = []
    Outputs = []
    for Label in ("Cold", "Cached"):
        Start = perf_counter()
        Binary = PyCeler.Compile(Source, Run / Label, Convert=False, Cache=Run / "Cache")
        Times.append(perf_counter() - Start)
        Outputs.append(Binary)
        Program = "import sys; sys.path.insert(0,sys.argv[1]); import Large_Module as M; assert all(getattr(M,'Function_'+str(I))(3)==I+3 for I in range(500))"
        subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent)], check=True)
    Logs = sorted((Run / "Build" / "Logs").glob("*.log"), key=lambda File: File.stat().st_mtime_ns)
    assert "All native products restored" in Logs[-1].read_text(encoding="utf-8")
    assert Outputs[0].read_bytes() == Outputs[1].read_bytes()
    Report = dict(Status="passed", Platform=platform.platform(), Python=sys.version, Functions=500,
                  Cold_Seconds=Times[0], Cached_Seconds=Times[1], Repeat_Build_Speedup=Times[0] / Times[1], Compiler_Skipped=True)
    File = Run / "Results.json"
    File.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(json.dumps(Report, indent=2))
    print(File)

if __name__ == "__main__":
    _Main()
