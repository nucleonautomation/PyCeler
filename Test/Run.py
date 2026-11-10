import argparse
import platform
import sys
import unittest
from pathlib import Path
from tempfile import mkdtemp

def _Cases(Suite):
    for Item in Suite:
        if isinstance(Item, unittest.TestSuite):
            yield from _Cases(Item)
        else:
            yield Item

def _Run():
    sys.dont_write_bytecode = True
    Parser = argparse.ArgumentParser(description="Run the unattended PyCeler regression suite.")
    Parser.add_argument("--no-wheels", action="store_true", help="Exclude the two tests that create wheel archives")
    Options = Parser.parse_args()
    Test_Directory = Path(__file__).resolve().parent
    Project_Directory = Test_Directory.parent
    Result_Directory = Project_Directory / "Test_Run"
    Result_Directory.mkdir(exist_ok=True)
    Run_Directory = Path(mkdtemp(prefix="Run_", dir=Result_Directory))
    Report = Run_Directory / "Results.txt"
    print(f"Report: {Report}", flush=True)
    sys.path.insert(0, str(Project_Directory))
    import Compile
    import PyCeler
    import PyCeler.Engine
    Package = Path(PyCeler.Engine.__file__).resolve().parent
    Provenance = Compile._Identity(Project_Directory)._Verify_Development(Project_Directory, Package)
    print(f"Engine: {PyCeler.Engine.__file__}\nBuild ID: {Provenance['Build_Id']}", flush=True)
    with Report.open("w", encoding="utf-8") as Stream:
        print(f"{platform.platform()} | Python {platform.python_version()}", file=Stream)
        print(f"Engine: {PyCeler.Engine.__file__}\nBuild ID: {Provenance['Build_Id']}\nSource fingerprint: {Provenance['Source_Fingerprint']}", file=Stream)
        Suite = unittest.defaultTestLoader.discover(str(Test_Directory), pattern="Test_*.py")
        if Options.no_wheels:
            Wheel_Tests = ("Native_Wheel.test_Deterministic_Metadata_And_Installed_Pipeline", "Wheel_Metadata.test_Custom_Library_And_Recorded_ABI_Control_Wheel_Tag")
            Cases = list(_Cases(Suite))
            Excluded = [Case for Case in Cases if Case.id().endswith(Wheel_Tests)]
            for Case in Excluded:
                print(f"Excluded by --no-wheels: {Case.id()}", file=Stream)
            Suite = unittest.TestSuite(Case for Case in Cases if not Case.id().endswith(Wheel_Tests))
        Result = unittest.TextTestRunner(stream=Stream, verbosity=2).run(Suite)
        if Result.testsRun == 0:
            print("No tests discovered.", file=Stream)
    print(Report.read_text(encoding="utf-8"), end="")
    return 0 if Result.testsRun and Result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(_Run())
