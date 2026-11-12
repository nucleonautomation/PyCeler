import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from Test.Workspace import Temporary_Directory

class Module_Scalar(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test" / "Module_Scalar_Loops.py"

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build"), "OMP_NUM_THREADS": "2"})
        Environment.start()
        self.addCleanup(Environment.stop)

    def _Probe(self, File, Fields):
        Name = File.name.split(".")[0]
        Command = [sys.executable, "-I", "-B", str(self._Root / "Test" / "Module_Scalar_Probe.py"), str(File), Name, json.dumps(Fields)]
        Result = subprocess.run(Command, text=True, capture_output=True, timeout=120)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
        Line = next(Line for Line in Result.stdout.splitlines() if Line.startswith("PYCELER_MODULE_RESULT="))
        return json.loads(Line.split("=", 1)[1])

    def _Compare(self, Source, Fields, Parallel=False):
        Original = Source.read_bytes()
        Binary = Compile(Source, self._Folder / ("Parallel" if Parallel else "Serial"), Select=False, OpenMP=Parallel)
        Reference = self._Probe(Source, Fields)
        Native = self._Probe(Binary, Fields)
        self.assertEqual(Native["Values"], Reference["Values"])
        self.assertEqual(Native["Error"], Reference["Error"])
        self.assertEqual(Source.read_bytes(), Original)
        return Native

    def test_Module_Numeric_Regions_Are_Recognized_Read_Only(self):
        Original = self._Fixture.read_bytes()
        Findings = Analyze(self._Fixture)
        Eligible = [Item for Item in Findings if Item.Classification == "Module_Scalar_Region"]
        self.assertTrue(Eligible, Findings)
        self.assertTrue(all(Item.Function is None and "native module arithmetic" in Item.Change for Item in Eligible))
        self.assertEqual(self._Fixture.read_bytes(), Original)
        Output = Convert(self._Fixture, self._Folder / "Converted", Select=False)
        self.assertIn("Module_", Output.read_text(encoding="utf-8"))
        self.assertEqual(self._Fixture.read_bytes(), Original)

    def test_Progress_Callback_Mutations_Bigints_And_Empty_Ranges(self):
        Native = self._Compare(self._Fixture, ["Results", "Events", "Total", "Index", "Iterations"])
        self.assertIsNone(Native["Error"])
        self.assertGreater(Native["Native"].get("Native", 0), 0, Native)
        self.assertEqual(Native["Values"]["Results"]["Empty"], [42, -23])
        self.assertEqual(Native["Values"]["Results"]["Mutation"][1:3], [31, 1])

    def test_Zero_Division_Preserves_Partial_Globals(self):
        Source = self._Folder / "Partial_Module.py"
        Source.write_text("Total = 0\nIndex = -23\nEvents = []\nfor Index in range(10):\n    Total += 10 // (3 - Index)\n    if Index % 2 == 0:\n        Events.append((Index, Total))\n", encoding="utf-8")
        Native = self._Compare(Source, ["Total", "Index", "Events"])
        self.assertEqual(Native["Error"]["Type"], "ZeroDivisionError")
        self.assertEqual(Native["Values"], {"Total": 18, "Index": 3, "Events": [[0, 3], [2, 18]]})

    def test_Shadowed_Range_And_Builtins_Retain_Python_Behavior(self):
        Source = self._Folder / "Shadowed_Module.py"
        Source.write_text("type = 'shadowed'\nint = 'shadowed'\nfloat = 'shadowed'\ndef range(Count):\n    return [9, 3, 14]\nTotal = 0\nEvents = []\nfor Index in range(100):\n    Total += (Index * Index + Index * 7) % 999983\n    if Index % 7 == 0 and Index != 0:\n        Events.append((Index, Total))\n", encoding="utf-8")
        Native = self._Compare(Source, ["Total", "Index", "Events"])
        self.assertIsNone(Native["Error"])
        self.assertEqual(Native["Values"]["Index"], 14)

    def test_Independent_Module_Reduction_Enters_Requested_Parallel_Path(self):
        Source = self._Folder / "Parallel_Module.py"
        Source.write_text("Total = 0\nfor Index in range(1000000):\n    Total += (Index * Index + Index * 7) % 999983\n", encoding="utf-8")
        Native = self._Compare(Source, ["Total", "Index"], Parallel=True)
        self.assertIsNone(Native["Error"])
        self.assertGreater(Native["Native"].get("Native", 0), 0, Native)
        self.assertGreater(Native["Native"].get("Parallel", 0), 0, Native)
        self.assertEqual(Native["Native"].get("Team"), 2, Native)

    def test_Progress_Boundaries_Ignore_Unrelated_Gcd_And_Pow_Rebinding(self):
        Source = self._Folder / "Rebound_Boundaries.py"
        Prelude = "import builtins as B\nimport math as M\nSaved_Gcd, Saved_Pow = M.gcd, B.pow\ndef Forbidden(*Args):\n    raise AssertionError('Unrelated binding was called')\nM.gcd = Forbidden\nB.pow = Forbidden\nResults = []\ntry:\n"
        Loops = []
        for Begin, Stop, Step in ((-29, 31, 3), (29, -31, -3), (2, 50, 6), (22, -32, -6)):
            Loops.append(f"    Total = 0\n    Events = []\n    for Index in range({Begin}, {Stop}, {Step}):\n        Total += Index * Index\n        if Index % 8 == 0:\n            Events.append((Index, Total))\n    Results.append((Total, Index, tuple(Events)))\n")
        Source.write_text(Prelude + "".join(Loops) + "finally:\n    M.gcd = Saved_Gcd\n    B.pow = Saved_Pow\n", encoding="utf-8")
        Native = self._Compare(Source, ["Results", "Total", "Index", "Events"], Parallel=True)
        self.assertIsNone(Native["Error"])
        self.assertGreater(Native["Native"].get("Native", 0), 0, Native)

    def test_Nested_Control_Exceptions_Finally_And_Contexts_Preserve_Event_Order(self):
        Source = self._Root / "Test" / "Module_Nested_Loops.py"
        Findings = Analyze(Source)
        Module = [Item for Item in Findings if Item.Classification == "Module_Scalar_Region"]
        self.assertGreaterEqual(len(Module), 8, Findings)
        self.assertTrue(any(Item.Function == "Global_Region" for Item in Module), Findings)
        Local = next(Item for Item in Findings if Item.Function == "Local_Reporting")
        self.assertEqual(Local.Change, "Keep original loop")
        Native = self._Compare(Source, ["Results", "Events", "Total", "Index", "Final_Index", "Remaining"])
        self.assertIsNone(Native["Error"])
        self.assertGreater(Native["Native"].get("Native", 0), 0, Native)
        self.assertIn(["missing", 0, "NameError"], Native["Values"]["Events"])
        self.assertEqual([Item[0] if isinstance(Item, list) else Item for Item in Native["Values"]["Events"][:5]],
                         ["if", "division", "finally", "enter", "with"])

    def test_Main_Guard_Enters_Native_Code_When_Run_As_Main(self):
        Source = self._Folder / "__main__.py"
        Source.write_text("Events = []\nif __name__ == '__main__':\n    Total = 0\n    for Index in range(32):\n        Total += (Index * Index + Index * 7) % 999983\n        if Index % 8 == 0 and Index != 0:\n            Events.append((Index, Total))\n    Result = (Total, Index, Events)\n", encoding="utf-8")
        self.assertEqual(Analyze(Source)[0].Classification, "Module_Scalar_Region")
        Native = self._Compare(Source, ["Result", "Total", "Index", "Events"])
        self.assertIsNone(Native["Error"])
        self.assertIn("Result", Native["Values"])
        self.assertGreater(Native["Native"].get("Native", 0), 0, Native)

    def test_Ordered_Floating_And_Nonreduction_Spans_Preserve_Bits_And_Overflow(self):
        Source = self._Folder / "Ordered_Module.py"
        Source.write_text("Results = {}\nEvents = []\nTotal = 0\nfor Index in range(128):\n    Total += (Index * Index + Index * 7) / 999983\n    if Index % 8 == 0 and Index != 0:\n        Events.append((Index, Total.hex()))\nResults['Float'] = (Total.hex(), Index, tuple(Events))\nTotal = 1\nEvents = []\nfor Index in range(1, 26):\n    Total *= Index\n    if Index % 5 == 0:\n        Events.append((Index, Total))\nResults['Product'] = (Total, Index, tuple(Events))\nTotal = 0\nEvents = []\ntry:\n    for Index in range(6):\n        Total += 1 / (3 - Index)\n        if Index % 1 == 0:\n            Events.append((Index, Total.hex()))\nexcept ZeroDivisionError:\n    Results['Partial'] = (Total.hex(), Index, tuple(Events))\n", encoding="utf-8")
        Findings = Analyze(Source)
        self.assertTrue(all(Item.Classification == "Module_Scalar_Region" for Item in Findings), Findings)
        Native = self._Compare(Source, ["Results", "Total", "Index", "Events"], Parallel=True)
        self.assertIsNone(Native["Error"])
        self.assertGreater(Native["Native"].get("Native", 0), 0, Native)
        self.assertEqual(Native["Values"]["Results"]["Product"][0], 15511210043330985984000000)
        self.assertEqual(Native["Values"]["Results"]["Partial"][1], 3)

    def test_Same_Line_Loops_And_Nested_Scopes_Remain_Python(self):
        Source = self._Folder / "Ambiguous_Module.py"
        Source.write_text("Total = 0\nfor Index in range(4): Total += Index\nif True:\n    def Inner():\n        global Total, Index\n        for Index in range(4):\n            Total += Index\nInner()\n", encoding="utf-8")
        Findings = Analyze(Source)
        self.assertTrue(all(Item.Change == "Keep original loop" for Item in Findings), Findings)
        Native = self._Compare(Source, ["Total", "Index"])
        self.assertEqual(Native["Values"], {"Total": 12, "Index": 3})

    def test_Loop_Else_Runs_Once_After_Native_Empty_And_Fallback_Completion(self):
        Source = self._Folder / "Module_Else.py"
        Source.write_text("Results = []\nEvents = []\nTotal = 0\nfor Index in range(32):\n    Total += Index * Index\n    if Index % 8 == 0:\n        Events.append((Index, Total))\nelse:\n    Results.append(('native', Total, Index))\nfor Index in range(0):\n    Total += Index * Index\nelse:\n    Results.append(('empty', Total, Index))\nTotal = 2 ** 70\nfor Index in range(9, -2, -2):\n    Total += Index * Index\nelse:\n    Results.append(('big', Total, Index))\ntry:\n    for Index in range(5):\n        Total += 1 // (2 - Index)\n    else:\n        Results.append('incorrect else')\nexcept ZeroDivisionError:\n    Results.append(('error', Total, Index))\ndef range(Count):\n    return [4, 7]\nfor Index in range(100):\n    Total += Index * Index\nelse:\n    Results.append(('iterator', Total, Index))\n", encoding="utf-8")
        Findings = Analyze(Source)
        self.assertEqual(sum(Item.Classification == "Module_Scalar_Region" for Item in Findings), 5, Findings)
        Native = self._Compare(Source, ["Results", "Events", "Total", "Index"], Parallel=True)
        self.assertIsNone(Native["Error"])
        self.assertGreater(Native["Native"]["Native"], 0)
        self.assertEqual([Item[0] for Item in Native["Values"]["Results"]], ["native", "empty", "big", "error", "iterator"])
