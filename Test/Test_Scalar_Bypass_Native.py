import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Compile, Convert
from Test.Generated_Source import _Python_Source
from Test import Test_Scalar_Bypass as Bypass_Source
from Test.Workspace import Temporary_Directory

class Scalar_Bypass_Native(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Compiled_Captured_Range_Bypass_And_Real_Native_Spans(self):
        with Temporary_Directory(dir=self._Root / 'Test_Run') as Folder:
            Work = Path(Folder)
            Source = Work / 'Bypass_Native.py'
            Text = "Collision = '_Pyceler_'\n" + Bypass_Source.Scalar_Bypass._Source.replace('Index % 6', 'Index % 4096')
            Source.write_text(Text, encoding='utf-8')
            Line = next(Node.lineno for Node in ast.walk(ast.parse(Text)) if isinstance(Node, ast.For))
            Table = {'int': [(4096, 1), (256, 1), (4, 0)]}
            Cached = ({Line: Table}, None, dict(Format='PyCeler selection 1', Items=[], Controlled_Policy_Test=True))
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Work / 'Build')), patch('PyCeler.Engine._Cache_Read', return_value=Cached) as Read:
                Converted = Convert(Source, Work / 'Converted', OpenMP=False, Cache=False)
                Binary = Compile(Converted, Work / 'Native', Convert=False, OpenMP=False)
            Read.assert_called_once()
            Generated = _Python_Source(Converted.read_text(encoding='utf-8'))
            self.assertIn('_Pyceler_XRegion_Count', Generated)
            self.assertIn(' < 256:', Generated)
            Program = (self._Root / 'Test/Scalar_Bypass_Probe.py').read_text(encoding='utf-8')
            Process = subprocess.run([sys.executable, '-I', '-B', '-c', Program, str(Source), str(Binary)], text=True, capture_output=True)
            self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
            Report = json.loads(Process.stdout.splitlines()[-1])
            self.assertEqual(Report['Comparisons'], 59)
            self.assertGreater(Report['Native_Calls'], 0)
            self.assertGreater(Report['Bypass_Calls'], 0)

if __name__ == '__main__':
    unittest.main()
