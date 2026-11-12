import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Convert
from PyCeler.Selection_Worker import _Observe
from Test.Workspace import Temporary_Directory

class Selection_Observation(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def _Candidate(self, Action, Dispatch=True):
        State = dict(Module=dict(Native=11, Parallel=7, Team=8, Fallbacks=3), Region=[9, 4],
                     Reduction=dict(Serial_Calls=13, Parallel_Calls=17, Last_Team=8, Last_Mode="python", Fallback_Reason="stale_reason"))
        def Statistics(Enabled=None, Reset=False):
            if Reset:
                State.pop("Execution", None)
            return dict(Execution=dict(State["Execution"])) if "Execution" in State else {}
        Namespace = dict(Action=lambda: Action(State), _Pyceler_Module_Stats=lambda: dict(State["Module"]),
                         _Pyceler_Reduction_Stats=lambda: dict(State["Reduction"]), _Pyceler_Region_Stats=lambda: tuple(State["Region"]))
        if Dispatch:
            Namespace["_Pyceler_Dispatch_Stats"] = Statistics
        exec("def Candidate(Value):\n    Action()\n    return Value\n", Namespace)
        return Namespace["Candidate"]

    def _Observation(self, Action, Dispatch=True, Proof=True):
        Observation = dict(Proof_Reduction=Proof)
        Outcome, Fallback = _Observe(self._Candidate(Action, Dispatch), (7,), "Original", Observation)
        self.assertEqual(Observation["Python_Fallback"], Fallback)
        return Observation, Fallback

    def test_Dispatch_Execution_Survives_Unchanged_Reduction_Metadata(self):
        for Mode, Team in (("native_serial", 1), ("native_parallel", 8)):
            with self.subTest(Mode=Mode):
                def Action(State):
                    State["Execution"] = dict(Reason=Mode, Native_Entry=True, Actual_Team=Team)
                Observation, Fallback = self._Observation(Action)
                self.assertFalse(Fallback)
                self.assertTrue(Observation["Native_Entry"])
                self.assertEqual(Observation["Actual_Team"], Team)
                self.assertEqual(Observation["Actual_Mode"], Mode)
                self.assertIsNone(Observation["Fallback_Reason"])

    def test_Module_Counter_Deltas_Supply_Missing_Dispatch_Execution(self):
        for Team in (1, 2):
            with self.subTest(Team=Team):
                def Action(State):
                    State["Module"]["Native"] += 1
                    State["Module"]["Parallel"] += int(Team > 1)
                    State["Module"]["Team"] = Team
                Observation, Fallback = self._Observation(Action)
                self.assertFalse(Fallback)
                self.assertTrue(Observation["Native_Entry"])
                self.assertEqual(Observation["Actual_Team"], Team)
                self.assertEqual(Observation["Actual_Mode"], "native_parallel" if Team > 1 else "native_serial")

    def test_Module_Mixed_Spans_Preserve_Native_And_Fallback_Evidence(self):
        for Last in ("native_parallel", "python_fallback"):
            with self.subTest(Last=Last):
                def Action(State):
                    State["Module"]["Native"] += 1
                    State["Module"]["Parallel"] += 1
                    State["Module"]["Fallbacks"] += 1
                    State["Module"]["Team"] = 2
                    State["Execution"] = dict(Reason=Last, Native_Entry=Last == "native_parallel", Actual_Team=2 if Last == "native_parallel" else 0)
                Observation, Fallback = self._Observation(Action)
                self.assertTrue(Fallback)
                self.assertTrue(Observation["Native_Entry"])
                self.assertEqual(Observation["Actual_Team"], 2)
                self.assertEqual(Observation["Actual_Mode"], Last)
                self.assertEqual(Observation["Fallback_Reason"], "runtime_guard")

    def test_Stale_Counters_Cannot_Claim_Execution_Or_Hide_Fallback(self):
        for Event in (False, True):
            with self.subTest(Event=Event):
                def Action(State):
                    if Event:
                        State["Execution"] = dict(Reason="python_fallback", Native_Entry=False, Actual_Team=0)
                Observation, Fallback = self._Observation(Action)
                self.assertTrue(Fallback)
                self.assertFalse(Observation["Native_Entry"])
                self.assertEqual(Observation["Actual_Team"], 0 if Event else None)
                self.assertEqual(Observation["Actual_Mode"], "python_fallback")
                self.assertEqual(Observation["Fallback_Reason"], "runtime_guard")
        def Decline(State):
            State["Module"]["Fallbacks"] += 1
        Observation, Fallback = self._Observation(Decline)
        self.assertTrue(Fallback)
        self.assertFalse(Observation["Native_Entry"])
        self.assertEqual(Observation["Actual_Mode"], "python_fallback")

    def test_Legacy_Reduction_And_Region_Deltas_Remain_Observable(self):
        def Reduction(State):
            State["Reduction"]["Parallel_Calls"] += 1
            State["Reduction"].update(Last_Team=2, Last_Mode="parallel", Fallback_Reason=None)
        Observation, Fallback = self._Observation(Reduction, Dispatch=False)
        self.assertFalse(Fallback)
        self.assertTrue(Observation["Native_Entry"])
        self.assertEqual(Observation["Actual_Team"], 2)
        def Region(State):
            State["Region"][0] += 1
        Observation, Fallback = self._Observation(Region, Proof=False)
        self.assertFalse(Fallback)
        self.assertTrue(Observation["Native_Entry"])
        self.assertEqual(Observation["Actual_Mode"], "serial")

    def test_Measured_Module_Candidates_Report_Actual_Native_Teams(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Observed_Module.py"
            Source.write_text("Total = 0\nfor Index in range(100000):\n    Total += (Index * Index + Index * 7) % 999983\n", encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"):
                Converted = Convert(Source, Folder / "Converted", OpenMP=True, Tuning=dict(Threads=[2], Budget_Seconds=8))
            Report = json.loads(Converted.with_suffix(".selection.json").read_text(encoding="utf-8"))
            Item, = Report["Items"]
            self.assertTrue(Item["Extracted"])
            self.assertIn("Serial_Contract", Item)
            for Variant, Team in (("Serial", 1), ("OpenMP_2", 2)):
                Cases = [Case for Case in Item["Cases"] if Case["Validation"].get(Variant) == "valid"]
                self.assertTrue(Cases, (Variant, Item))
                for Case in Cases:
                    Observation = Case["Observations"][Variant]
                    self.assertTrue(Observation["Native_Entry"], (Variant, Case))
                    self.assertFalse(Observation["Python_Fallback"], (Variant, Case))
                    self.assertEqual(Observation["Actual_Team"], Team, (Variant, Case))
