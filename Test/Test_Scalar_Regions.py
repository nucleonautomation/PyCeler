import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from Test.Workspace import Temporary_Directory

class Scalar_Regions(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test" / "Scalar_Regions.py"

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build")})
        Environment.start()
        self.addCleanup(Environment.stop)

    def _Probe(self, Binary, Program, Source=None):
        Prefix = "import sys\nsys.path.insert(0, sys.argv[1])\nReference_Path = " + repr(str(Source or self._Fixture)) + "\n"
        Process = subprocess.run([sys.executable, "-I", "-B", "-c", Prefix + Program, str(Binary.parent)], text=True, capture_output=True)
        self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)

    def test_Module_And_Mixed_Function_Regions_Are_Recognized(self):
        Findings = Analyze(self._Fixture)
        self.assertEqual(len(Findings), 15)
        Identity_Cases = {"Conditional_Identity", "Literal_Identity", "Constant_Identity"}
        Eligible = [Item for Item in Findings if Item.Function is not None and Item.Function not in Identity_Cases]
        self.assertTrue(all(Item.Classification == "Scalar_Numeric_Region" for Item in Eligible), Findings)
        self.assertTrue(all(Item.Change == "Keep original loop" for Item in Findings if Item.Function in Identity_Cases), Findings)
        Module_Findings = [Item for Item in Findings if Item.Function is None]
        self.assertEqual([Item.Classification for Item in Module_Findings], ["Module_Scalar_Region", "Module_Scalar_Region"])
        self.assertEqual(sum(Item.Function is None for Item in Findings), 2)
        self.assertTrue(all("Scalar region extraction" in Item.Transformations for Item in Eligible))
        Original = self._Fixture.read_bytes()
        Output = Convert(self._Fixture, self._Folder / "Converted", Select=False)
        self.assertIn("Region_Spans", Output.read_text(encoding="utf-8"))
        self.assertEqual(self._Fixture.read_bytes(), Original)

    def test_Native_Regions_Preserve_Progress_And_Fallbacks(self):
        Binary = Compile(self._Fixture, self._Folder / "Native", Select=False, OpenMP=False)
        Program = (self._Root / "Test" / "Scalar_Regions_Probe.py").read_text(encoding="utf-8")
        self._Probe(Binary, Program)

    def test_Measured_Module_Regions_Do_Not_Execute_Module_Or_Callbacks(self):
        Source = self._Folder / "Isolated_Module.py"
        Source.write_text("raise RuntimeError('module executed during selection')\nTotal = 0\nfor Index in range(4096):\n    Total += (Index * Index + 7 * Index) % 999983\n    if Index % 128 == 0 and Index != 0:\n        raise RuntimeError('callback executed during selection')\n", encoding="utf-8")
        self.assertEqual(Analyze(Source)[0].Classification, "Module_Scalar_Region")
        Output = Convert(Source, self._Folder / "Measured", OpenMP=False, Minimum_Speedup=1e12)
        Report = json.loads(Output.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertTrue(Report["Items"], Report)
        self.assertTrue(all(Item.get("Extracted") for Item in Report["Items"]), Report)

    def test_Module_Builtin_Shadowing_Preserves_Behavior(self):
        Body = "Events = []\nTotal = 0\nIndex = -23\nfor Index in range(25):\n    Total += (Index * Index + 7 * Index) / 999983\n    if Index % 7 == 0 and Index != 0:\n        Events.append((Index, Total))\nResult = (Total, Index, Events)\n"
        Prelude = "type = 'shadowed type'\nint = 'shadowed int'\nfloat = 'shadowed float'\n"
        for Name, Extra in (("Builtin_Shadows", ""), ("Range_Shadow", "def range(Count):\n    return [9, 3, 14]\n")):
            with self.subTest(Name=Name):
                Source = self._Folder / (Name + ".py")
                Source.write_text(Prelude + Extra + Body, encoding="utf-8")
                Binary = Compile(Source, self._Folder / Name, Select=False, OpenMP=False)
                Program = "import importlib.util\nSpec = importlib.util.spec_from_file_location('Original', Reference_Path)\nOriginal = importlib.util.module_from_spec(Spec)\nSpec.loader.exec_module(Original)\n" + f"import {Name} as Native\nassert Native.Result == Original.Result, (Native.Result, Original.Result)\n"
                self._Probe(Binary, Program, Source)

    def test_Module_Exception_Preserves_Partial_Globals(self):
        Source = self._Folder / "Partial_Module.py"
        Source.write_text("ZeroDivisionError = 'shadowed exception'\nEvents = []\nTotal = 0\nCount = 0\nIndex = -23\nfor Index in range(10):\n    Count += 1\n    Total += 10 // (3 - Index)\n    if Index % 4 == 0:\n        Events.append((Index, Total, Count))\n", encoding="utf-8")
        self.assertEqual(Analyze(Source)[0].Classification, "Module_Scalar_Region")
        Binary = Compile(Source, self._Folder / "Native", Select=False, OpenMP=False)
        Program = "import importlib.util\nfrom pathlib import Path\nResults = []\nfor Name, File in [('Original', Reference_Path), ('Partial_Module', str(Path(sys.argv[1]) / " + repr(Binary.name) + "))]:\n    Spec = importlib.util.spec_from_file_location(Name, File)\n    Module = importlib.util.module_from_spec(Spec)\n    try:\n        Spec.loader.exec_module(Module)\n    except Exception as Error:\n        Results.append((type(Error), Module.Total, Module.Count, Module.Index, Module.Events))\n    else:\n        raise AssertionError('expected ZeroDivisionError')\nassert Results[0] == Results[1], Results\nassert Results[0] == (ZeroDivisionError, 18, 4, 3, [(0, 3, 1)]), Results\n"
        self._Probe(Binary, Program, Source)

    def test_Extracted_Else_Preserves_Callbacks_Empty_And_Exception_Exits(self):
        Source = self._Folder / "Region_Else.py"
        Source.write_text("def Compute(Count, Initial, Callback):\n    Total = Initial\n    Index = -23\n    for Index in range(Count):\n        Total += Index * Index\n        if Index % 7 == 0:\n            Callback(Index, Total)\n    else:\n        Callback('else', (Total, Index))\n    return Total, Index\n", encoding="utf-8")
        self.assertEqual(Analyze(Source)[0].Classification, "Scalar_Numeric_Region")
        Binary = Compile(Source, self._Folder / "Native", Select=False, OpenMP=False)
        Program = "import importlib.util\nSpec = importlib.util.spec_from_file_location('Original', Reference_Path)\nOriginal = importlib.util.module_from_spec(Spec)\nSpec.loader.exec_module(Original)\nimport Region_Else as Native\nfor Count, Initial in [(32, 0), (0, 9), (32, 2 ** 70)]:\n    Expected, Actual = [], []\n    Left = Original.Compute(Count, Initial, lambda *Args: Expected.append(Args))\n    Right = Native.Compute(Count, Initial, lambda *Args: Actual.append(Args))\n    assert (Left, Expected) == (Right, Actual), (Left, Right, Expected, Actual)\n    assert sum(Event[0] == 'else' for Event in Actual) == 1\nfor Module in (Original, Native):\n    Events = []\n    def Callback(Index, Total):\n        Events.append(Index)\n        if Index == 7:\n            raise ValueError('stop')\n    try:\n        Module.Compute(32, 0, Callback)\n    except ValueError:\n        pass\n    else:\n        raise AssertionError('missing callback exception')\n    assert Events == [0, 7], Events\nassert Native._Pyceler_Region_Stats()[0] > 0\n"
        self._Probe(Binary, Program, Source)
