import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory as Temporary_Directory
from unittest.mock import patch
import Compile

class Build_Provenance(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        self._Source = self._Folder / "PyCeler"
        self._Source.mkdir()
        for Name in ("Engine.pyx", "Guard.pxi", "Runtime.pxi.in", "Helper.py"):
            (self._Source / Name).write_text("Value = 1\n", encoding="utf-8")
        (self._Folder / "Compile.py").write_text("Value = 1\n", encoding="utf-8")
        self._Identity = Compile._Identity(self._Root)
        self._Package = self._Folder / "Build" / "Lib" / "PyCeler"
        self._Package.mkdir(parents=True)
        (self._Package / "Engine.pyd").write_bytes(b"native engine")
        self._Report = dict(Format="PyCeler native package 1", Build_Id="a" * 64, **self._Identity._Source_State(self._Folder),
                            Files={"PyCeler/Engine.pyd": hashlib.sha256(b"native engine").hexdigest()})
        self._Manifest = self._Package.parent / "PyCeler.manifest.json"
        self._Manifest.write_text(json.dumps(self._Report), encoding="utf-8")

    def test_Sources_Templates_And_Build_Entry_Invalidate_Artifacts(self):
        self.assertEqual(self._Identity._Verify_Development(self._Folder, self._Package)["Build_Id"], "a" * 64)
        for File in [*self._Source.iterdir(), self._Folder / "Compile.py"]:
            Original = File.read_bytes()
            File.write_bytes(Original + b"Value = 2\n")
            with self.assertRaisesRegex(ImportError, "stale.*" + File.name.replace(".", "\\.")):
                self._Identity._Verify_Development(self._Folder, self._Package)
            File.write_bytes(Original)

    def test_Dependency_Changes_And_Missing_Provenance_Are_Rejected(self):
        with patch.object(self._Identity.importlib.metadata, "version", return_value="changed"):
            with self.assertRaisesRegex(ImportError, "stale.*build dependencies"):
                self._Identity._Verify_Development(self._Folder, self._Package)
        self._Manifest.unlink()
        with self.assertRaisesRegex(ImportError, "provenance.*missing"):
            self._Identity._Verify_Development(self._Folder, self._Package)

    def test_Modified_Binaries_And_Escaping_Manifest_Paths_Are_Rejected(self):
        (self._Package / "Engine.pyd").write_bytes(b"modified")
        with self.assertRaisesRegex(ImportError, "inventory|modified artifact"):
            self._Identity._Verify_Development(self._Folder, self._Package)
        self._Report["Files"] = {"../../Compile.py": hashlib.sha256((self._Folder / "Compile.py").read_bytes()).hexdigest()}
        self._Manifest.write_text(json.dumps(self._Report), encoding="utf-8")
        with self.assertRaisesRegex(ImportError, "inventory|modified artifact"):
            self._Identity._Verify_Development(self._Folder, self._Package)
