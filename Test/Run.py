import platform
import sys
import unittest
from pathlib import Path
from tempfile import mkdtemp

def _Run():
    sys.dont_write_bytecode = True
    Test_Directory = Path(__file__).resolve().parent
    Project_Directory = Test_Directory.parent
    Result_Directory = Project_Directory / "Test_Run"
    Result_Directory.mkdir(exist_ok=True)
    Run_Directory = Path(mkdtemp(prefix="Run_", dir=Result_Directory))
    Report = Run_Directory / "Results.txt"
    print(f"Report: {Report}", flush=True)
    sys.path.insert(0, str(Project_Directory))
    with Report.open("w", encoding="utf-8") as Stream:
        print(f"{platform.platform()} | Python {platform.python_version()}", file=Stream)
        Suite = unittest.defaultTestLoader.discover(str(Test_Directory), pattern="Test_*.py")
        Result = unittest.TextTestRunner(stream=Stream, verbosity=2).run(Suite)
        if Result.testsRun == 0:
            print("No tests discovered.", file=Stream)
    print(Report.read_text(encoding="utf-8"), end="")
    return 0 if Result.testsRun and Result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(_Run())
