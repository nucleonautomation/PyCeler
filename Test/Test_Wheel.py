import base64
import csv
import hashlib
import io
import json
import unittest
import zipfile
from pathlib import Path
import Compile
import PyCeler
from Test.Verify_Wheel import _Verify
from Test.Workspace import Temporary_Directory

class Native_Wheel(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Deterministic_Metadata_And_Installed_Pipeline(self):
        with Temporary_Directory(prefix="Wheel_Regression_", dir=self._Root / "Test_Run") as Folder:
            Work = Path(Folder)
            Library = Path(PyCeler.__path__[0])
            Wheel = Compile.Build_Wheel(Work / "First", Library_Directory=Library)
            Second = Compile.Build_Wheel(Work / "Second", Library_Directory=Library)
            self.assertEqual(Wheel.name, Second.name)
            self.assertEqual(Wheel.read_bytes(), Second.read_bytes())
            Provenance = json.loads((Library.parent / "PyCeler.manifest.json").read_text(encoding="utf-8"))
            if Provenance["Build_Environment"].get("Mode", Provenance["Mode"]) == "abi":
                Floor = Provenance["Build_Environment"].get("ABI_Floor") or Provenance["Python_Version"]
                self.assertIn("-cp" + Floor.replace(".", "") + "-abi3-", Wheel.name)
            else:
                self.assertIn("-" + Provenance["Build_Environment"]["ABI_Tag"] + "-", Wheel.name)
            with zipfile.ZipFile(Wheel) as Archive:
                Names = Archive.namelist()
                Record_Name = next(Name for Name in Names if Name.endswith("/RECORD"))
                Rows = list(csv.reader(io.StringIO(Archive.read(Record_Name).decode("utf-8"))))
                self.assertEqual({Row[0] for Row in Rows}, set(Names))
                for Name, Digest, Size in Rows:
                    if Name != Record_Name:
                        Content = Archive.read(Name)
                        self.assertEqual(Digest, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(Content).digest()).rstrip(b"=").decode("ascii"))
                        self.assertEqual(int(Size), len(Content))
                Metadata = Archive.read(next(Name for Name in Names if Name.endswith("/METADATA"))).decode("utf-8")
                self.assertIn("Requires-Python: >=3.11", Metadata)
                self.assertIn(f"Version: {PyCeler.__version__}", Metadata)
                self.assertTrue(all(Name.endswith((".pyd", ".so", "/__init__.py")) for Name in Names if Name.startswith("PyCeler/")))
            Result = json.loads(_Verify(Wheel, Output=Work / "Verified").read_text(encoding="utf-8"))
            self.assertEqual(Result["Status"], "passed")
            self.assertEqual(Result["Actual_OpenMP_Team"], 2)
            self.assertEqual(Result["Build_Id"], Provenance["Build_Id"])
