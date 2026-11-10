import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import Compile

class Wheel_Metadata(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Build_Interpreter_ABI_Distinguishes_Free_Threaded_And_Debug(self):
        Backend = Compile._Backend(self._Root)
        Python_Tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
        for Free, Debug, Suffix in ((0, 0, ""), (1, 0, "t"), (0, 1, "d"), (1, 1, "td")):
            Values = dict(Py_GIL_DISABLED=Free, Py_DEBUG=Debug)
            with patch.object(Backend.sysconfig, "get_config_var", side_effect=Values.get), patch.object(Backend, "hasattr", return_value=False, create=True):
                self.assertEqual(Backend._Interpreter_ABI(), Python_Tag + Suffix)

    def test_Custom_Library_And_Recorded_ABI_Control_Wheel_Tag(self):
        with tempfile.TemporaryDirectory(prefix="Wheel_Metadata_", dir=self._Root / "Test_Run") as Folder:
            Work = Path(Folder)
            Package = Work / "Custom" / "PyCeler"
            Package.mkdir(parents=True)
            (Package / "__init__.py").write_text("__version__ = '0.2.0'\n", encoding="utf-8")
            Report = dict(Target=Compile._Target("native"), Mode="regular", Python_Version="3.14", Files={"PyCeler/__init__.py": "mock"},
                          Build_Environment=dict(Mode="regular", Python="3.14.1 free-threading build", ABI_Tag="cp314t", GIL_Disabled=True))
            Verify = Mock(return_value=Report)
            with patch("Compile._Identity", return_value=SimpleNamespace(_Verify_Development=Verify)):
                First = Compile.Build_Wheel(Work / "Wheels", Library_Directory=Package.parent)
                Second = Compile.Build_Wheel(Work / "Again", Library_Directory=Package)
            self.assertIn("-cp314-cp314t-", First.name)
            self.assertEqual(First.read_bytes(), Second.read_bytes())
            self.assertEqual(Verify.call_count, 2)
            self.assertEqual(Verify.call_args.args[1], Package)
            with zipfile.ZipFile(First) as Archive:
                Text = Archive.read("pyceler-0.2.0.dist-info/WHEEL").decode("utf-8")
                self.assertIn("Tag: cp314-cp314t-", Text)
            del Report["Build_Environment"]["ABI_Tag"]
            with patch("Compile._Identity", return_value=SimpleNamespace(_Verify_Development=Verify)):
                with self.assertRaisesRegex(ValueError, "exact interpreter ABI"):
                    Compile.Build_Wheel(Work / "Rejected", Library_Directory=Package)
