import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from Test.Workspace import Temporary_Directory
import PyCeler

class Installed_Distribution(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Binaries_And_Init_Run_The_Public_Pipeline(self):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Folder:
            Work = Path(Folder)
            Distribution = Work / "Distribution"
            Package = Distribution / "PyCeler"
            Package.mkdir(parents=True)
            Built = Path(PyCeler.__path__[0])
            for File in Built.iterdir():
                if File.suffix in (".pyd", ".so") or File.name == "__init__.py":
                    shutil.copy2(File, Package / File.name)
            self.assertTrue(all(File.suffix in (".pyd", ".so") or File.name == "__init__.py" for File in Package.iterdir()))
            Source = Work / "Kernel.py"
            Source.write_text("def Clear(Values):\n    for Index in range(len(Values)):\n        Values[Index] = 0\n    return Values\n", encoding="utf-8")
            Program = "\n".join((
                "import json, sys", "from pathlib import Path", "sys.path.insert(0, sys.argv[1])", "import PyCeler",
                "assert PyCeler.__name__ == 'PyCeler' and PyCeler.__version__ == '0.3.0'",
                "assert PyCeler.Analyze.__module__ == 'PyCeler.Engine'",
                "assert PyCeler.Loop_Finding.__module__ == 'PyCeler.Loop_Detector'",
                "Work = Path(sys.argv[2])", "Source = Work / 'Kernel.py'", "assert len(PyCeler.Analyze(Source)) == 1",
                "Converted = PyCeler.Convert(Source, Work / 'Converted', Select=False)", "assert Converted.is_file()",
                "Binary = PyCeler.Compile(Source, Work / 'Native', OpenMP=False)",
                "Report = json.loads(Binary.with_suffix('.selection.json').read_text(encoding='utf-8'))",
                "assert Report['Builds']['Serial']['Status'] == 'built', Report['Builds']",
                "assert Report['Items'][0]['Cases'], Report['Items']",
                "sys.path.insert(0, str(Binary.parent))", "from Kernel import Clear", "import numpy as Numpy",
                "Values = Numpy.ones(8192, dtype=Numpy.int32)", "assert Clear(Values) is Values and not Values.any()",
                "assert Clear([1, 2, 3]) == [0, 0, 0]",
                "assert not any(Name == 'Pyceler' or Name.startswith('Pyceler.') for Name in sys.modules)",
                "for Name, Module in list(sys.modules.items()):",
                "    if Name.startswith('PyCeler.') and getattr(Module, '__file__', None):",
                "        assert Module.__name__ == Name, (Name, Module.__name__)",
                "        assert Path(Module.__file__).parent == Path(sys.argv[1]) / 'PyCeler', (Name, Module.__file__)",
                "        assert Path(Module.__file__).suffix in ('.pyd', '.so'), (Name, Module.__file__)"))
            Environment = dict(os.environ, PYCELER_BUILD_DIR=str(Work / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
            Process = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Distribution), str(Work)],
                                     cwd=Work, env=Environment, capture_output=True, text=True, timeout=180)
            self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
