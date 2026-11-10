import os
import sys
from Test.Workspace import Temporary_Directory
import types
import unittest
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path
from unittest.mock import patch

class Source_Bootstrap(unittest.TestCase):
    _Root = Path(__file__).resolve().parent.parent
    _Run_Root = _Root / "Test_Run"

    def _Execute(self, Root, Built):
        Source = Root / "PyCeler"
        Source.mkdir(parents=True)
        (Source / "Engine.pyx").write_text("", encoding="utf-8")
        Name = "_Pyceler_Bootstrap_Check"
        Package = types.ModuleType(Name)
        Package.__file__ = str(Source / "__init__.py")
        Package.__package__ = Name
        Package.__path__ = [str(Source)]
        Engine = types.ModuleType(Name + ".Engine")
        Engine.Analyze, Engine.Convert, Engine.Compile = object(), object(), object()
        Findings = types.ModuleType(Name + ".Loop_Detector")
        Findings.Loop_Finding = object()
        if Built is not None:
            Built.mkdir(parents=True)
            (Built / "__init__.py").write_text("", encoding="utf-8")
            for Module in ("Engine", "Loop_Detector"):
                (Built / (Module + EXTENSION_SUFFIXES[0])).write_bytes(b"")
        Text = (self._Root / "PyCeler" / "__init__.py").read_text(encoding="utf-8")
        with patch.dict(sys.modules, {Name: Package, Engine.__name__: Engine, Findings.__name__: Findings}):
            exec(compile(Text, Package.__file__, "exec"), Package.__dict__)
        return Package

    def test_Checkout_Requires_A_Complete_Built_Package(self):
        self._Run_Root.mkdir(exist_ok=True)
        with Temporary_Directory(prefix="Bootstrap_Missing_", dir=self._Run_Root) as Folder, patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ImportError, "python -B Compile.py"):
                self._Execute(Path(Folder), None)

    def test_Checkout_Prefers_Build_Lib_Over_Source(self):
        self._Run_Root.mkdir(exist_ok=True)
        with Temporary_Directory(prefix="Bootstrap_Default_", dir=self._Run_Root) as Folder, patch.dict(os.environ, {}, clear=True):
            Root = Path(Folder)
            Built = Root / "Build" / "Lib" / "PyCeler"
            Package = self._Execute(Root, Built)
            self.assertEqual(Package.__path__, [str(Built)])
            self.assertEqual(Package.__version__, "0.1.0")
            self.assertEqual(Package.__all__, ["Analyze", "Convert", "Compile", "Loop_Finding"])

    def test_Custom_Library_Directory_Is_Explicit(self):
        self._Run_Root.mkdir(exist_ok=True)
        with Temporary_Directory(prefix="Bootstrap_Custom_", dir=self._Run_Root) as Folder:
            Root = Path(Folder)
            Built = Root / "Custom" / "PyCeler"
            with patch.dict(os.environ, {"PYCELER_LIBRARY_DIR": str(Built.parent)}):
                Package = self._Execute(Root, Built)
            self.assertEqual(Package.__path__, [str(Built)])
