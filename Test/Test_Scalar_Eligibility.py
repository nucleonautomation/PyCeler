import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile
from Test.Scalar_Eligibility_Corpus import Corpus
from Test.Workspace import Temporary_Directory
# Regression checks for integer operators, freshness and native admission.
class Scalar_Eligibility(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Every_Positive_Family_Has_A_Native_Plan(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:  # Keep generated sources and binaries outside the maintained fixture tree.
            Source = Path(Directory) / "Eligibility.py"
            Text, Names = Corpus()
            Source.write_text(Text, encoding="utf-8")
            Findings = Analyze(Source, OpenMP=True)
            Eligible = [Item for Item in Findings if Item.Change != "Keep original loop"]
            self.assertEqual(len(Eligible), 160)
            self.assertEqual(sorted(Item.Function for Item in Eligible if Item.Function), sorted(Names))

    def test_Compiled_Matrix_Preserves_Values_Types_Identity_And_Errors(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Eligibility.py"
            Source.write_text(Corpus()[0], encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2"):
                for Parallel in (False, True):
                    Binary = Compile(Source, Folder / str(Parallel), Select=False, OpenMP=Parallel)  # Build a real extension; a static finding alone does not prove native execution.
                    Report = Folder / (str(Parallel) + ".json")
                    Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test/Scalar_Eligibility_Probe.py"), str(Source), str(Binary), str(Report)], capture_output=True, text=True, timeout=120)
                    self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
                    Data = json.loads(Report.read_text(encoding="utf-8"))
                    self.assertEqual(Data["Comparisons"], 1320)
                    self.assertEqual(Data["Positive_Native_Cases"], 240)

    def test_Alias_And_Folded_Constant_Results_Stay_Observable(self):
        Expressions = ["+Initial", "Initial % Operand", "Initial >> Operand", "Initial >> 0", "(1 << 40) ^ 3", "-(1 << 40)", "~(1 << 40)", "(1 << 40) << 0", "(1 << 40) ** 1"]
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Text = ""
            for Position, Expression in enumerate(Expressions):
                Text += f"def Identity_{Position}(Count, Initial, Operand):\n    Value = Initial\n    for Index in range(Count):\n        Value = {Expression}\n    return Value, Value is Initial\n\n"
            Source = Folder / "Identity.py"
            Source.write_text(Text, encoding="utf-8")
            self.assertTrue(all(Item.Change == "Keep original loop" for Item in Analyze(Source)))
            Binary = Compile(Source, Folder / "Native", Select=False, OpenMP=True)
            Program = "import sys\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nfrom Test.Scalar_Eligibility_Probe import _Load,_Observe\nOriginal=_Load(Path(sys.argv[2]),'Original')\nNative=_Load(Path(sys.argv[3]),'Identity')\nfor Name in [Name for Name in vars(Original) if Name.startswith('Identity_')]:\n    for Initial in (int('-1099511627777'),int('1099511627777'),-1,0,256):\n        Args=(3,Initial,0)\n        assert _Observe(getattr(Original,Name),Args)==_Observe(getattr(Native,Name),Args),Name\n"
            Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(self._Root), str(Source), str(Binary)], capture_output=True, text=True, timeout=120)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
