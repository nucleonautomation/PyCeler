from Test.Workspace import Temporary_Directory
import unittest
from pathlib import Path
from Survey_Source import Write_Survey
from Survey_Verification import _Check_Constant_Survey, _Check_Filters, _Load

class Survey_Fixture(unittest.TestCase):
    def test_Generated_Survey_Against_Independent_Expectations(self):
        Runs = Path(__file__).resolve().parents[1] / "Test_Run"
        Runs.mkdir(exist_ok=True)
        with Temporary_Directory(dir=Runs) as Folder:
            Source = Write_Survey(Path(Folder) / "Survey_Workload.py")
            Modules = {"Python": _Load(Source.stem, Source)}
            _Check_Constant_Survey(Modules)
            self.assertEqual(_Check_Filters(Modules), 44)
