import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile
from Test.Workspace import Temporary_Directory

class Observable_Semantics(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, {"PYCELER_BUILD_DIR": str(self._Folder / "Build")})
        Environment.start()
        self.addCleanup(Environment.stop)

    def _Probe(self, Program, *Arguments):
        Process = subprocess.run([sys.executable, "-I", "-B", "-c", Program, *map(str, Arguments)], text=True, capture_output=True, timeout=90)
        self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
        return Process.stdout

    def test_Modulo_Identity_And_Original_Python_Fallback(self):
        Source = self._Folder / "Identity.py"
        Source.write_text("def Identity(Count, Value, Mod):\n    Result = 0\n    for Index in range(Count):\n        Result = Value % Mod\n    return Result\n\ndef Same(Count, Mod):\n    Result = 0\n    Index = 0\n    for Index in range(Count):\n        Result = Index % Mod\n    return Result is Index\n\ndef Copy(Count, Value, Mod):\n    Result = 0\n    for Index in range(Count):\n        Result = Value % Mod\n    Copied = Result\n    return Copied\n\ndef Missing(Count):\n    for Index in range(Count):\n        Value = str(Index)\n    return Value\n\ndef Safe(Count, Mod):\n    Total = 0\n    for Index in range(Count):\n        Total += Index % Mod\n    return Total\n", encoding="utf-8")
        Findings = Analyze(Source)
        self.assertTrue(all(Item.Change == "Keep original loop" for Item in Findings if Item.Function != "Safe"), Findings)
        Binary = Compile(Source, self._Folder / "Native", OpenMP=False)
        Program = "import importlib.util, sys, types\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nimport Identity as Native\nSpec = importlib.util.spec_from_file_location('Reference', sys.argv[2])\nReference = importlib.util.module_from_spec(Spec)\nSpec.loader.exec_module(Reference)\nfor Module in (Reference, Native):\n    Value = int('1000')\n    assert Module.Identity(1, Value, 2**50) is Value\n    assert Module.Copy(1, Value, 2**50) is Value\n    assert Module.Same(100000, 2**50) is True\n    assert isinstance(Module.Missing, types.FunctionType)\nErrors = []\nfor Module in (Reference, Native):\n    try:\n        Module.Missing(0)\n    except Exception as Error:\n        Errors.append((type(Error), str(Error), Error.args))\nassert len(Errors) == 2 and Errors[0] == Errors[1], Errors\nassert Native.Safe(100000, 999983) == Reference.Safe(100000, 999983)\n"
        self._Probe(Program, Binary.parent, Source)
        Report = json.loads(Binary.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertTrue(all(Item["Function"] == "Safe" for Item in Report["Items"]))

    def test_Signal_Handlers_And_Cancellation_Preserve_Module_State(self):
        Source = self._Folder / "Signal_State.py"
        Source.write_text("import time\nTotal = 0\nIndex = -1\nDone = False\nStart = time.perf_counter()\nfor Index in range(1000000):\n    Total += (Index * Index + Index * 7) % 999983\nDone = True\n", encoding="utf-8")
        Finding = Analyze(Source)[0]
        self.assertEqual(Finding.Classification, "Module_Scalar_Region")
        self.assertIn("signal", Finding.Reason)
        Binary = Compile(Source, self._Folder / "Native", Select=False, OpenMP=False)
        Program = (self._Root / "Test" / "Signal_State_Probe.py").read_text(encoding="utf-8")
        for File, Name in ((Source, "Reference"), (Binary, "Signal_State")):
            for Mode in ("mutate", "cancel"):
                with self.subTest(Native=File == Binary, Mode=Mode):
                    self._Probe(Program, File, Name, Mode)

    def test_Large_Unsupported_Module_Preserves_Python_Definitions(self):
        Source = self._Folder / "Python_Definitions.py"
        Text = "from __future__ import annotations\nEvents = []\nShared = int('1000')\ndef Decorate(Function):\n    Events.append(Function.__name__)\n    return Function\n@Decorate\ndef Fancy(Count: Missing_Annotation = Shared):\n    return [Index * Index for Index in range(Count)]\nclass Container:\n    Value = Shared\n    def Read(self):\n        return self.Value\nLeft = 1000001\nRight = 1000001\n"
        Text += "\n".join(f"def Function_{Number}(Count):\n    Description = {('preserved Python constant ' * 25)!r}\n    return sum(Index * Index for Index in range(Count)), Description\n" for Number in range(400))
        Source.write_text(Text, encoding="utf-8")
        Binary = Compile(Source, self._Folder / "Native", Select=False, OpenMP=False)
        Program = "import sys, types\nsys.path.insert(0, sys.argv[1])\nimport Python_Definitions as M\nassert M.Events == ['Fancy']\nassert M.Fancy.__defaults__[0] is M.Shared\nassert M.Fancy.__annotations__ == {'Count': 'Missing_Annotation'}\nassert M.Container().Read() is M.Shared\nassert M.Left is M.Right\nassert isinstance(M.Fancy, types.FunctionType)\nfor Index in range(400):\n    Function = getattr(M, 'Function_' + str(Index))\n    assert isinstance(Function, types.FunctionType)\n    assert Function(8) == (140, 'preserved Python constant ' * 25)\n"
        self._Probe(Program, Binary.parent)
