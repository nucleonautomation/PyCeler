import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PyCeler import Analyze, Compile
from Test.Generated_Scalar_Programs import _Programs
from Test.Generated_Scalar_Probe import _Observe, _Positive_Cases
from Test.Workspace import Temporary_Directory

class Generated_Scalar_Programs(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Positive_Witnesses_Are_Bounded_And_Independent_Of_Findings(self):
        Cases = _Positive_Cases(_Programs())
        Expected = {Family + "_" + str(Number) for Family, Count in (("Sum", 24), ("Ordered", 12), ("Callback", 6)) for Number in range(Count)}
        self.assertEqual(set(Cases), Expected)
        self.assertEqual(set(Cases.values()), {(2, 1, 7)})
        with self.assertRaises(ZeroDivisionError):
            _Positive_Cases(_Programs().replace("Total +=", "Total += 1 // (Count - 2) +", 1))

    def test_Native_Evidence_Rejects_Stale_Counters_And_Declined_Attempts(self):
        State = dict(Region=[7, 3], Reduction=dict(Serial_Calls=11, Parallel_Calls=13), Execution=dict(Reason="native_parallel", Native_Entry=True, Actual_Team=2))
        def Dispatch(Enabled=None, Reset=False):
            if Reset:
                State.pop("Execution", None)
            return dict(Execution=dict(State["Execution"])) if "Execution" in State else {}
        Module = SimpleNamespace(_Pyceler_Dispatch_Stats=Dispatch, _Pyceler_Region_Stats=lambda: tuple(State["Region"]),
                                 _Pyceler_Reduction_Stats=lambda: dict(State["Reduction"]), Sum_0=lambda *Inputs: 7)
        Outcome, Observation = _Observe(Module, "Sum_0", (2, 1, 7))
        self.assertFalse(Observation["Native_Entry"])
        self.assertEqual(Observation["Execution"], {})
        def Declined(*Inputs):
            State["Region"][0] += 1
            State["Region"][1] += 1
            return 7
        Module.Sum_0 = Declined
        Outcome, Observation = _Observe(Module, "Sum_0", (2, 1, 7))
        self.assertFalse(Observation["Native_Entry"])
        self.assertTrue(Observation["Python_Fallback"])

    def test_Generated_AST_Combinations_Preserve_Observable_Behavior(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Generated_Programs.py"
            Text = _Programs()
            Tree = ast.parse(Text)
            self.assertEqual(len(Tree.body), 54)
            Expressions = {ast.dump(Node) for Node in ast.walk(Tree) if isinstance(Node, ast.BinOp)}
            self.assertGreater(len(Expressions), 70)
            Source.write_text(Text, encoding="utf-8")
            Findings = Analyze(Source, OpenMP=True)
            self.assertGreaterEqual(sum(Item.Change != "Keep original loop" for Item in Findings), 24)
            with patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(Folder / "Build"), "OMP_NUM_THREADS": "2", "OMP_DYNAMIC": "FALSE"}):
                for Parallel in (False, True):
                    with self.subTest(OpenMP=Parallel):
                        Binary = Compile(Source, Folder / ("Parallel" if Parallel else "Serial"), Select=False, OpenMP=Parallel)
                        Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test" / "Generated_Scalar_Probe.py"), str(Source), str(Binary)],
                                                capture_output=True, text=True, timeout=180)
                        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
                        Report = json.loads(Result.stdout)
                        self.assertEqual(Report["Generated_Programs"], 54)
                        self.assertEqual(Report["Differential_Cases"], 10422)
                        self.assertTrue(Report["Exact_Values_Types_Aliases_Exceptions_And_Callbacks"])
                        Expected = {Family + "_" + str(Number) for Family, Count in (("Sum", 24), ("Ordered", 12), ("Callback", 6)) for Number in range(Count)}
                        self.assertEqual(set(Report["Native_Programs"]), Expected)
                        self.assertEqual(Report["Native_Witness_Comparisons"], len(Expected))
                        self.assertEqual(Report["Native_Families"], dict(Sum=24, Ordered=12, Callback=6))
                        self.assertEqual(set(Report["Behavior_Only_Programs"]), {"Aliases_" + str(Number) for Number in range(12)})
                        for Name, Observation in Report["Native_Programs"].items():
                            self.assertTrue(Observation["Native_Entry"], (Name, Observation))
                            self.assertFalse(Observation["Python_Fallback"], (Name, Observation))
