import hashlib
import json
import os
from Test.Workspace import Temporary_Directory
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import Compile
from PyCeler.Native_Build import _Cleanup_Workspace, _Publication, _Replace_Outputs

class Native_Distribution(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Runs = self._Root / "Test_Run"
        Runs.mkdir(exist_ok=True)
        Folder = Temporary_Directory(dir=Runs)
        self.addCleanup(Folder.cleanup)
        self._Folder = Path(Folder.name)

    def test_Embedded_Resources_Cover_Runtime_Templates(self):
        Package = self._Root / "PyCeler"
        Text = Compile._Embedded_Resources(Package)
        for File in [*Package.glob("*.pxi.in"), Package / "Selection_Environment.py"]:
            self.assertIn(repr(File.name), Text)
            self.assertIn(repr(File.read_text(encoding="utf-8")), Text)
        self.assertNotIn("read_text", Text)
        self.assertNotIn("from pathlib", Text)

    def test_Target_Uses_Interpreter_Architecture(self):
        with patch("Compile.platform.system", return_value="Windows"), patch("Compile.platform.machine", return_value="ARM64"), patch("Compile.sysconfig.get_platform", return_value="win-amd64"):
            self.assertEqual(Compile._Target("native"), "windows-x64")
        for Tag, Target in (("linux-x86_64", "linux-x64"), ("linux-aarch64", "linux-arm64")):
            with patch("Compile.platform.system", return_value="Linux"), patch("Compile.sysconfig.get_platform", return_value=Tag):
                self.assertEqual(Compile._Target("native"), Target)

    def test_Temporary_Native_File_Locks_Are_Retried(self):
        from unittest.mock import Mock
        Workspace = Mock()
        Workspace.cleanup.side_effect = [PermissionError("Native image is still closing"), None]
        with patch("PyCeler.Native_Build.os.name", "nt"), patch("PyCeler.Native_Build.time.sleep"):
            _Cleanup_Workspace(Workspace)
        self.assertEqual(Workspace.cleanup.call_count, 2)
        Workspace.cleanup.side_effect = PermissionError("Persistent file lock")
        with patch("PyCeler.Native_Build.os.name", "nt"), patch("PyCeler.Native_Build.time.sleep"):
            with self.assertRaisesRegex(PermissionError, "Persistent"):
                _Cleanup_Workspace(Workspace)

    def test_Package_Publishes_Only_Binaries_And_Init(self):
        from contextlib import contextmanager
        Captured = {}
        @contextmanager
        def _Workspace():
            with Temporary_Directory(dir=self._Folder) as Folder:
                yield Path(Folder)
        def _Build(Stage, Paths, Output, *Options):
            Captured["Paths"] = list(Paths)
            Captured["Resource"] = (Stage / "Sources" / "PyCeler" / "Runtime_Resources.pyx").read_text(encoding="utf-8")
            Suffix = ".pyd" if os.name == "nt" else ".so"
            for Relative in Paths:
                Target = Output / Relative.with_suffix(Suffix)
                Target.parent.mkdir(parents=True, exist_ok=True)
                Target.write_bytes(b"mock native artifact")
        Backend = SimpleNamespace(_Workspace=_Workspace, _Build=_Build, _Publication=_Publication, _Replace_Outputs=_Replace_Outputs)
        with patch("Compile._Backend", return_value=Backend):
            Output = Compile.Build_Package(self._Folder / "Distribution")
        Files = list(Output.iterdir())
        self.assertEqual(Output.name, "PyCeler")
        self.assertTrue(all(Relative.parts[0] == "PyCeler" for Relative in Captured["Paths"]))
        Manifest = json.loads((Output.parent / "PyCeler.manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(all(Name.startswith("PyCeler/") for Name in Manifest["Files"]))
        self.assertEqual([File.name for File in Files if File.suffix == ".py"], ["__init__.py"])
        self.assertTrue(all(File.suffix in (".pyd", ".so") or File.name == "__init__.py" for File in Files))
        self.assertEqual(len(Files), len(Captured["Paths"]) + 1)
        self.assertIn("Selection_Worker", {File.stem for File in Files})
        self.assertIn("Native_Build", {File.stem for File in Files})
        self.assertIn("Runtime_Resources", {File.stem for File in Files})
        self.assertIn("Map_Runtime.pxi.in", Captured["Resource"])
        self.assertNotIn("Structural_Runtime.pxi.in", Captured["Resource"])
        self.assertEqual((Output / "__init__.py").read_text(encoding="utf-8"), Compile._Package_Init(self._Root / "PyCeler", Manifest["Build_Id"], Manifest["Source_Fingerprint"]))
        self.assertEqual(Manifest["Source_Fingerprint"], Compile._Identity(self._Root)._Source_State(self._Root)["Source_Fingerprint"])
        self.assertIn("PyCeler/Scalar_Parallel_Runtime.pxi.in", Manifest["Sources"])
        self.assertEqual(len(Manifest["Build_Id"]), 64)
        self.assertNotIn("Build", (Output / "__init__.py").read_text(encoding="utf-8"))

    def test_Source_And_Foreign_Output_Are_Protected(self):
        with self.assertRaisesRegex(ValueError, "separate"):
            Compile.Build_Package(self._Root)
        Output = self._Folder / "Existing" / "PyCeler"
        Output.mkdir(parents=True)
        File = Output / "Keep.py"
        File.write_text("Value = 1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "non-distribution"):
            Compile.Build_Package(Output.parent)
        self.assertEqual(File.read_text(encoding="utf-8"), "Value = 1\n")

    def test_Updates_Retire_Only_Owned_Binaries_And_Caches(self):
        Output = self._Folder / "Published"
        Package = Output / "PyCeler"
        Package.mkdir(parents=True)
        Old = Package / "Removed.pyd"
        Old.write_bytes(b"old native binary")
        Manifest = dict(Format="PyCeler native package 1", Files={"PyCeler/Removed.pyd": hashlib.sha256(Old.read_bytes()).hexdigest()})
        (Output / "PyCeler.manifest.json").write_text(json.dumps(Manifest), encoding="utf-8")
        Cache = Package / "__pycache__"
        Cache.mkdir()
        (Cache / "__init__.cpython-311.pyc").write_bytes(b"bytecode")
        Built = self._Folder / "Built"
        (Built / "PyCeler").mkdir(parents=True)
        Relative = Path("PyCeler/Current.pyd")
        (Built / Relative).write_bytes(b"new native binary")
        Report = dict(Format="PyCeler native package 1", Files={Relative.as_posix(): hashlib.sha256((Built / Relative).read_bytes()).hexdigest()})
        Backend = SimpleNamespace(_Publication=_Publication, _Replace_Outputs=_Replace_Outputs)
        Compile._Publish_Package(Backend, Built, Output, [Relative], Report)
        self.assertFalse(Old.exists())
        self.assertFalse(Cache.exists())
        self.assertEqual((Output / Relative).read_bytes(), b"new native binary")
        Foreign = Package / "Foreign.pyd"
        Foreign.write_bytes(b"user binary")
        with self.assertRaisesRegex(ValueError, "unowned"):
            Compile._Publish_Package(Backend, Built, Output, [Relative], Report)
        self.assertEqual(Foreign.read_bytes(), b"user binary")

    def test_Inventory_Failure_Rolls_Back_Publication(self):
        Output = self._Folder / "Published"
        Built = self._Folder / "Built"
        Relative = Path("PyCeler/Current.pyd")
        for Folder, Content in ((Output, b"previous"), (Built, b"replacement")):
            (Folder / "PyCeler").mkdir(parents=True)
            (Folder / Relative).write_bytes(Content)
        Backend = SimpleNamespace(_Publication=_Publication, _Replace_Outputs=_Replace_Outputs)
        Report = dict(Format="PyCeler native package 1", Files={Relative.as_posix(): "unused"})
        with patch("Compile._Existing_Files", side_effect=[[Relative], [Relative, Path("PyCeler/Unexpected.pyd")]]):
            with self.assertRaisesRegex(RuntimeError, "inventory"):
                Compile._Publish_Package(Backend, Built, Output, [Relative], Report)
        self.assertEqual((Output / Relative).read_bytes(), b"previous")
        self.assertFalse((Output / "PyCeler.manifest.json").exists())
