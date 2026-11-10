import json
import os
from Test.Workspace import Temporary_Directory
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch
from PyCeler.Selection_Cache import _Cache_Context, _Cache_Read, _Cache_Write, _Normalize_Workloads
from PyCeler.Selection_Policy import _Selection_Table
from PyCeler.Selection_Worker import _Copy, _Observe, _Representative_Cases, _Value, _Winner

class Optimization_Selection(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Folder = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Folder.cleanup)
        self._Folder = Path(Folder.name)

    def test_Input_Isolation_Preserves_Overlapping_Views_And_Identity(self):
        import numpy as Numpy
        Storage = Numpy.arange(24, dtype=Numpy.int32)
        Left = Storage[1:13:2]
        Right = Storage[3:15:2]
        Reverse = Storage[12:0:-2]
        Left_Copy, Right_Copy, Again, Reverse_Copy = _Copy((Left, Right, Left, Reverse))
        self.assertIs(Left_Copy, Again)
        self.assertTrue(Numpy.shares_memory(Left_Copy, Right_Copy))
        self.assertFalse(Numpy.shares_memory(Left_Copy, Left))
        self.assertEqual(Reverse_Copy.strides, Reverse.strides)
        Numpy.testing.assert_array_equal(Reverse_Copy, Reverse)
        Left_Copy[1] = 99
        self.assertEqual(Right_Copy[0], 99)
        self.assertEqual(Storage[3], 3)

    def test_Readonly_And_Fortran_Views_Are_Preserved(self):
        import numpy as Numpy
        Storage = Numpy.asfortranarray(Numpy.arange(24).reshape(4, 6))
        View = Storage[:, 1:4]
        View.setflags(write=False)
        Copy, Other = _Copy((Storage, View))
        self.assertTrue(Copy.flags.f_contiguous)
        self.assertFalse(Other.flags.writeable)
        self.assertTrue(Numpy.shares_memory(Copy, Other))
        Numpy.testing.assert_array_equal(Other, View)

    def test_Validation_Observes_Warnings_And_Floating_Bits(self):
        def _Warn(Value):
            warnings.warn("numeric boundary", RuntimeWarning)
            return Value
        def _Quiet(Value):
            return Value
        self.assertNotEqual(_Observe(_Warn, (2,))[0], _Observe(_Quiet, (2,))[0])
        self.assertNotEqual(_Value(0.0), _Value(-0.0))
        self.assertEqual(_Value(float("nan")), _Value(float("nan")))

    def test_Representative_Cases_Preserve_Shared_Storage(self):
        import numpy as Numpy
        Item = dict(Arguments=2, Kind="array", Destination=1,
                    Representative_Workload=dict(File=str(self._Root / "Test" / "Representative_Workloads.py"), Factory="Build_Aliased_Cases"))
        Cases = _Representative_Cases(Item)
        Key, Size, Shape, Args, Metadata = Cases[0]
        self.assertEqual((Key, Size, Shape), (Numpy.dtype("int32").str, 15, (15,)))
        self.assertTrue(Metadata["Holdout"])
        self.assertTrue(Numpy.shares_memory(*Args))
        self.assertTrue(Numpy.shares_memory(*_Copy(Args)))

    def test_Holdout_And_Shape_Evidence_Can_Reject_A_Band(self):
        def _Case(Size, Serial, Holdout=False):
            return dict(Key="int", Size=Size, Holdout=Holdout, Validation={"Python": "valid", "Serial": "valid"},
                        Timings={Name: dict(Samples_Ns=[Value] * 5) for Name, Value in (("Python", 100), ("Serial", Serial))})
        Cases = [_Case(16, 50), _Case(32, 110, True), _Case(64, 40), _Case(64, 45), _Case(96, 40, True)]
        Table = _Selection_Table(Cases, 1.1, True)
        self.assertEqual(Table["int"], [(97, 0), (64, 1), (16, 0)])

    def test_Structural_Candidates_Require_Incremental_Gains(self):
        Timings = {Name: dict(Samples_Ns=[Value] * 5) for Name, Value in (("Python", 100), ("Serial", 50), ("Optimized", 30), ("Tiled", 29), ("OpenMP", 28))}
        self.assertEqual(_Winner(Timings, 1.1), "Optimized")
        Case = dict(Key="int", Size=10, Validation={Name: "valid" for Name in Timings}, Timings=Timings)
        self.assertEqual(_Selection_Table([Case], 1.1)["int"], [(10, 3)])

    def test_Holdout_Only_And_Empty_Evidence_Never_Promote(self):
        self.assertEqual(_Selection_Table([], 1.1, True), {})
        Case = dict(Key="int", Size=128, Holdout=True, Validation={"Python": "valid", "Serial": "valid"},
                    Timings={"Python": dict(Samples_Ns=[100] * 5), "Serial": dict(Samples_Ns=[1] * 5)})
        self.assertEqual(_Selection_Table([Case], 1.1, True), {"int": [(129, 0)]})

    def test_Cache_Roundtrip_And_Corruption_Rejection(self):
        Root = self._Folder / "Cache"
        Root.mkdir()
        Artifacts = self._Folder / "Probe"
        Artifacts.mkdir()
        (Artifacts / "Reference.py").write_text("def Item():\n    return 1\n", encoding="utf-8")
        Context = (Root, "example", {"Source": "content-key"})
        Choices = {2: {"int": [(4, 1)]}, 10: {"int": [(8, 3)]}}
        Report = dict(Format="PyCeler selection 1", Items=[], Builds={})
        _Cache_Write(Context, Choices, {"Host": []}, Report, Artifacts)
        Cached = _Cache_Read(Context)
        self.assertEqual(Cached[0], Choices)
        self.assertEqual(Cached[2]["Cache"]["Status"], "hit")
        File = Root / "example" / "Result.json"
        Record = json.loads(File.read_text(encoding="utf-8"))
        Record["Result"]["Choices"]["2"]["int"][0][1] = 2
        File.write_text(json.dumps(Record), encoding="utf-8")
        self.assertIsNone(_Cache_Read(Context))

    def test_Cache_Key_Tracks_Source_And_Declared_Workload_Dependencies(self):
        Source = self._Folder / "Input.py"
        Factory = self._Folder / "Factory.py"
        Dependency = self._Folder / "Data.txt"
        Source.write_text("def F():\n    return 1\n", encoding="utf-8")
        Factory.write_text("def Cases():\n    return []\n", encoding="utf-8")
        Dependency.write_text("first", encoding="utf-8")
        Workloads = _Normalize_Workloads({"F": dict(File=Factory, Factory="Cases", Dependencies=[Dependency])})
        def _Key():
            return _Cache_Context(Source, "abi", "3.11", False, 1.1, Workloads, self._Folder / "Cache")[1]
        with patch("PyCeler.Selection_Cache._Toolchain", return_value=[["compiler", "digest"]]):
            First = _Key()
            Dependency.write_text("second", encoding="utf-8")
            Second = _Key()
            Source.write_text("def F():\n    return 2\n", encoding="utf-8")
            Third = _Key()
        self.assertEqual(len({First, Second, Third}), 3)

    def test_Cache_Repairs_Corruption_And_Reuses_Valid_Entries(self):
        Root = self._Folder / "Cache"
        Root.mkdir()
        Artifacts = self._Folder / "Probe"
        Artifacts.mkdir()
        (Artifacts / "Reference.py").write_text("def Item():\n    return 1\n", encoding="utf-8")
        Context = (Root, "example", {"Source": "content-key"})
        Choices = {2: {"int": [(4, 1)]}}
        Report = dict(Format="PyCeler selection 1", Items=[], Builds={})
        _Cache_Write(Context, Choices, {"Host": []}, Report, Artifacts)
        File = Root / "example" / "Result.json"
        File.write_text("incomplete", encoding="utf-8")
        self.assertIsNone(_Cache_Read(Context))
        _Cache_Write(Context, Choices, {"Host": []}, Report, Artifacts)
        self.assertEqual(_Cache_Read(Context)[0], Choices)
        self.assertEqual((Root / "example" / "Artifacts" / "Reference.py").read_bytes(), (Artifacts / "Reference.py").read_bytes())
        Valid = File.read_bytes()
        with patch("PyCeler.Selection_Cache.os.replace", side_effect=AssertionError("A valid cache entry must remain unchanged")):
            _Cache_Write(Context, Choices, {"Host": []}, Report, Artifacts)
        self.assertEqual(File.read_bytes(), Valid)
        self.assertFalse((Root / "example.lock").exists())

    def test_Cache_Repair_Restores_Previous_Entry_On_Publication_Failure(self):
        Root = self._Folder / "Cache"
        Root.mkdir()
        Directory = Root / "example"
        Directory.mkdir()
        File = Directory / "Result.json"
        File.write_text("recoverable previous data", encoding="utf-8")
        Artifacts = self._Folder / "Probe"
        Artifacts.mkdir()
        Context = (Root, "example", {"Source": "content-key"})
        Report = dict(Format="PyCeler selection 1", Items=[], Builds={})
        Replace = os.replace
        def _Replace(Source, Destination):
            if Path(Source).name == "example" and Path(Source).parent.name.startswith("Pending_"):
                raise OSError("simulated publication failure")
            return Replace(Source, Destination)
        with patch("PyCeler.Selection_Cache.os.replace", side_effect=_Replace):
            with self.assertRaisesRegex(OSError, "simulated publication failure"):
                _Cache_Write(Context, {}, {"Host": []}, Report, Artifacts)
        self.assertEqual(File.read_text(encoding="utf-8"), "recoverable previous data")
        self.assertFalse((Root / "example.lock").exists())

    def test_Cache_Rejects_Entries_Outside_Its_Root(self):
        Root = self._Folder / "Cache"
        Root.mkdir()
        Artifacts = self._Folder / "Probe"
        Artifacts.mkdir()
        Context = (Root, "../Outside", {"Source": "content-key"})
        Report = dict(Format="PyCeler selection 1", Items=[], Builds={})
        self.assertIsNone(_Cache_Read(Context))
        with self.assertRaisesRegex(OSError, "direct local child"):
            _Cache_Write(Context, {}, {"Host": []}, Report, Artifacts)
        self.assertFalse((self._Folder / "Outside").exists())

    def test_Cache_Rejects_A_Source_Changed_After_Planning(self):
        Source = self._Folder / "Input.py"
        Source.write_text("def F():\n    return 2\n", encoding="utf-8")
        with patch("PyCeler.Selection_Cache._Toolchain", return_value=[["compiler", "digest"]]):
            Context = _Cache_Context(Source, "abi", "3.11", False, 1.1, {}, self._Folder / "Cache", Source_Text="def F():\n    return 1\n")
        self.assertIsNone(Context)

    def test_Factory_Configuration_Rejects_Callables_And_Unknown_Options(self):
        with self.assertRaises(ValueError):
            _Normalize_Workloads({"F": lambda: ()})
        with self.assertRaises(ValueError):
            _Normalize_Workloads({"F": dict(File=__file__, Factory="Cases", Execute=True)})

    def test_Representative_Workloads_And_Cache_Through_Public_Conversion(self):
        from PyCeler import Convert
        Source = self._Folder / "User_Map.py"
        Source.write_text("def Scale(Input, Output):\n    for Index in range(len(Input)):\n        Output[Index] = Input[Index] * 2\n    return Output\n", encoding="utf-8")
        Workloads = {"Scale": dict(File=self._Root / "Test" / "Representative_Workloads.py", Factory="Build_Map_Cases")}
        Options = dict(OpenMP=False, Cache=self._Folder / "Cache", Workloads=Workloads)
        with patch.dict(os.environ, PYCELER_BUILD_DIR=str(self._Folder / "Build")):
            First = Convert(Source, self._Folder / "First", **Options)
            Report = json.loads(First.with_suffix(".selection.json").read_text(encoding="utf-8"))
            self.assertEqual(Report["Cache"]["Status"], "miss", Report.get("Cache"))
            Cases = Report["Items"][0]["Cases"]
            self.assertEqual(sum(Case.get("Holdout", False) for Case in Cases), 2)
            self.assertTrue(any("Serial" in Case["Timings"] for Case in Cases))
            with patch("PyCeler.Engine._Build", side_effect=AssertionError("A cache hit must not rebuild selection probes")):
                Second = Convert(Source, self._Folder / "Second", **Options)
            Cached = json.loads(Second.with_suffix(".selection.json").read_text(encoding="utf-8"))
            self.assertEqual(Cached["Cache"]["Status"], "hit")
            self.assertEqual(First.read_bytes(), Second.read_bytes())
