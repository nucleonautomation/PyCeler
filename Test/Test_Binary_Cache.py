import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from Test.Workspace import Temporary_Directory
from PyCeler import Compile

class Binary_Cache(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        self._Sources = self._Folder / "Sources"
        self._Sources.mkdir()
        (self._Sources / "A.pyx").write_text('include "Value.pxi"\ndef Read():\n    return Value()\n', encoding="utf-8")
        (self._Sources / "Value.pxi").write_text('cdef int Value():\n    return 4\n', encoding="utf-8")
        (self._Sources / "B.py").write_text('def Read():\n    return 8\n', encoding="utf-8")
        self._Options = dict(Convert=False, Cache=self._Folder / "Cache")
        Environment = patch.dict(os.environ, PYCELER_BUILD_DIR=str(self._Folder / "Build"))
        Environment.start()
        self.addCleanup(Environment.stop)

    def _Probe(self, Output, Value):
        Program = "import sys; sys.path.insert(0, sys.argv[1]); import A, B; assert A.Read() == int(sys.argv[2]); assert B.Read() == 8"
        Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Output), str(Value)], capture_output=True, text=True)
        self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)

    def _Summary(self):
        Logs = sorted((self._Folder / "Build" / "Logs").glob("*.log"), key=lambda File: File.stat().st_mtime_ns)
        Text = Logs[-1].read_text(encoding="utf-8")
        return Text, json.loads(Text.split("Binary cache: ")[-1])

    def _Without_Worker(self):
        Original = subprocess.run
        def _Run(Command, *Arguments, **Keywords):
            if isinstance(Command, list) and any("_Run(Path(sys.argv[2]))" in str(Value) for Value in Command):
                raise AssertionError("Cache hit launched a compiler worker")
            return Original(Command, *Arguments, **Keywords)
        return patch("PyCeler.Native_Build.subprocess.run", side_effect=_Run)

    def test_Repeat_Build_Skips_Compiler_And_Include_Change_Is_Incremental(self):
        First = Compile(self._Sources, self._Folder / "First", **self._Options)
        self._Probe(First[0].parent, 4)
        Text, Summary = self._Summary()
        self.assertEqual([Item["Status"] for Item in Summary["Modules"]], ["miss", "miss"], Summary)
        with self._Without_Worker():
            Second = Compile(self._Sources, self._Folder / "Second", **self._Options)
        self.assertEqual([Item.name for Item in First], [Item.name for Item in Second])
        self._Probe(Second[0].parent, 4)
        self.assertEqual([Item["Status"] for Item in self._Summary()[1]["Modules"]], ["hit", "hit"])
        (self._Sources / "Value.pxi").write_text('cdef int Value():\n    return 6\n', encoding="utf-8")
        Third = Compile(self._Sources, self._Folder / "Third", **self._Options)
        Text, Summary = self._Summary()
        self.assertEqual([Item["Status"] for Item in Summary["Modules"]], ["miss", "hit"], Summary)
        self.assertIn("Cython A", Text)
        self.assertNotIn("Cython B", Text)
        self.assertEqual([Item.name for Item in Third], [Item.name for Item in First])
        self._Probe(Third[0].parent, 6)

    def test_Corrupt_Binary_Is_Rebuilt_And_OpenMP_Option_Invalidates(self):
        Compile(self._Sources, self._Folder / "First", **self._Options)
        for Manifest in (self._Folder / "Cache" / "Native").glob("*/Manifest.json"):
            Record = json.loads(Manifest.read_text(encoding="utf-8"))
            if Record["Build"]["Members"] == ["A.pyx"]:
                Binary = Manifest.parent / "Products" / next(iter(Record["Products"]))
                Binary.write_bytes(b"corrupt cached extension")
        Result = Compile(self._Sources, self._Folder / "Repaired", **self._Options)
        self.assertEqual([Item["Status"] for Item in self._Summary()[1]["Modules"]], ["miss", "hit"])
        self._Probe(Result[0].parent, 4)
        with self._Without_Worker():
            Compile(self._Sources, self._Folder / "Reused_Repair", **self._Options)
        self.assertEqual([Item["Status"] for Item in self._Summary()[1]["Modules"]], ["hit", "hit"])
        Compile(self._Sources, self._Folder / "Flags", OpenMP=False, **self._Options)
        self.assertEqual([Item["Status"] for Item in self._Summary()[1]["Modules"]], ["miss", "miss"])

    def test_Grouped_Products_And_Loaders_Are_Restored(self):
        First = Compile(self._Sources, self._Folder / "First", Link=True, **self._Options)
        with self._Without_Worker():
            Second = Compile(self._Sources, self._Folder / "Second", Link=True, **self._Options)
        self.assertEqual(len(First), 1)
        self.assertEqual(len(Second), 1)
        self._Probe(Second[0].parent, 4)
        self.assertTrue((Second[0].parent / "B.py").is_file())

    def test_Compiler_Header_Change_Invalidates_And_Repairs_Cache(self):
        Headers = self._Folder / "Headers"
        Headers.mkdir()
        Header = Headers / "Constant.h"
        Header.write_text("static int Cache_Value(void) { return 4; }\n", encoding="utf-8")
        Source = self._Folder / "Header.pyx"
        Source.write_text('cdef extern from "Constant.h":\n    int Cache_Value()\ndef Read():\n    return Cache_Value()\n', encoding="utf-8")
        Settings = {"INCLUDE": str(Headers) + ";" + os.environ.get("INCLUDE", "")} if os.name == "nt" else {"CFLAGS": os.environ.get("CFLAGS", "") + ' -I"' + str(Headers) + '"'}
        with patch.dict(os.environ, Settings):
            Compile(Source, self._Folder / "First_Header", **self._Options)
            with self._Without_Worker():
                Compile(Source, self._Folder / "Cached_Header", **self._Options)
            Header.write_text("static int Cache_Value(void) { return 9; }\n", encoding="utf-8")
            Binary = Compile(Source, self._Folder / "Updated_Header", **self._Options)
            self.assertEqual(self._Summary()[1]["Modules"][0]["Status"], "miss")
            Program = "import sys; sys.path.insert(0,sys.argv[1]); import Header; assert Header.Read()==9"
            Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent)], capture_output=True, text=True)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
            with self._Without_Worker():
                Compile(Source, self._Folder / "Reused_Header", **self._Options)
