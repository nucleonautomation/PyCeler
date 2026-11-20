import json
import os
import subprocess
import sys
import types
import random
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler.Selection_Inputs import _Copy, _Storage_Bytes, _Probe_Resource
from PyCeler.Selection_Worker import _Observe, _Check, _Time, _Probe_Timeout, _Range_Span
from PyCeler.Selection_Policy import _Selection_Table
from Test.Workspace import Temporary_Directory
# Regression checks for validation, timing budgets and conservative dispatch.
class Selection_Safety(unittest.TestCase):
    def test_Expected_Exceptions_Validate_Without_Vetoing_Timings(self):
        def Successful(Size, Holdout=False):
            return dict(Key='int', Size=Size, Holdout=Holdout, Reference_Outcome='return', Validation={'Python': 'valid', 'Serial': 'valid'}, Timings={'Python': {'Samples_Ns': [100, 100, 100]}, 'Serial': {'Samples_Ns': [10, 10, 10]}})
        Failure = dict(Key='int', Size=128, Reference_Outcome='raise', Validation={'Python': 'valid', 'Serial': 'unsupported: runtime guard selected Python'}, Timings={})
        Cases = [Successful(128), Successful(512, True), Failure]
        self.assertEqual(_Selection_Table(Cases, 1.1, True)['int'], [(513, 0), (128, 1)])
        Failure['Validation']['Serial'] = 'invalid: exception differs'
        self.assertTrue(all(Mode == 0 for Bound, Mode in _Selection_Table(Cases, 1.1, True)['int']))
        Failure['Validation']['Serial'] = 'unsupported: runtime guard selected Python'
        self.assertEqual(_Selection_Table([Failure], 1.1, True)['int'], [])

    _Root = Path(__file__).resolve().parents[1]

    def test_Range_Sizing_Preserves_Random_State_And_Helper_Bindings(self):
        Item = dict(Range='range(Scale(Count) + int(Rng.random() * 100.0))', Math_Imports=('import random as Rng',), Helper_Sources=(('Scale', 'def Scale(Value):\n    return Value * 2'),))
        Before = random.getstate()
        Copy = random.Random()
        Copy.setstate(Before)
        Expected = 6 + int(Copy.random() * 100.0)
        self.assertEqual(len(_Range_Span(Item, dict(Count=3))), Expected)
        self.assertEqual(random.getstate(), Before)
        with self.assertRaises(ValueError):
            _Range_Span(Item, dict(Count=3), 'range(0, int(Rng.random() * 100.0), 0)')
        self.assertEqual(random.getstate(), Before)

    def test_Validation_Records_Nested_Return_And_Input_Aliases(self):
        Value = int("1234567")
        def _Original(Argument):
            return {"nested": [Argument, Argument]}
        def _Changed(Argument):
            return {"nested": [int(str(Argument)), int(str(Argument))]}
        self.assertNotEqual(_Observe(_Original, (Value,))[0], _Observe(_Changed, (Value,))[0])
        self.assertEqual(_Observe(_Original, (Value,))[0], _Observe(_Original, (Value,))[0])

    def test_Validation_Records_Exception_Aliases_And_Cycles(self):
        Value = int("1234567")
        def _Original(Argument):
            raise ValueError(Argument)
        def _Changed(Argument):
            raise ValueError(int(str(Argument)))
        self.assertNotEqual(_Observe(_Original, (Value,))[0], _Observe(_Changed, (Value,))[0])
        Cycle = []
        Cycle.append(Cycle)
        Clone, Again = _Copy((Cycle, Cycle))
        self.assertIs(Clone, Again)
        self.assertIs(Clone[0], Clone)
        self.assertEqual(_Observe(lambda Item: Item, (Cycle,))[0], _Observe(lambda Item: Item, (Cycle,))[0])

    def test_Validation_Records_Array_View_Storage_And_Writeability(self):
        import numpy as Numpy
        Values = Numpy.arange(20, dtype=Numpy.int64)
        self.assertNotEqual(_Observe(lambda Item: Item[::2], (Values,))[0], _Observe(lambda Item: Item[::2].copy(), (Values,))[0])
        def _Readonly(Item):
            View = Item[::2]
            View.setflags(write=False)
            return View
        self.assertNotEqual(_Observe(_Readonly, (Values,))[0], _Observe(lambda Item: Item[::2], (Values,))[0])

    def test_Isolation_Budget_Counts_Unique_Backing_Storage(self):
        import numpy as Numpy
        Storage = Numpy.arange(1024, dtype=Numpy.int64)
        Views = (Storage[:1], Storage[-1:], Storage[:1])
        self.assertLess(_Storage_Bytes(Views), Storage.nbytes + 1024)
        with self.assertRaisesRegex(_Probe_Resource, "backing storage"):
            _Copy(Views, Limit=4096)
        Copies = _Copy(Views, Limit=16384)
        self.assertTrue(Numpy.shares_memory(Copies[0], Copies[2]))
        self.assertFalse(Numpy.shares_memory(Copies[0], Storage))

    def test_Isolation_Preserves_Owner_Base_And_Existing_Writeable_Views(self):
        import numpy as Numpy
        Owner = Numpy.arange(20, dtype=Numpy.int64)
        View = Owner[::2]
        Owner.setflags(write=False)
        Copy_View, Copy_Owner, Again = _Copy((View, Owner, View))
        self.assertIs(Copy_View, Again)
        self.assertIsNone(Copy_Owner.base)
        self.assertIs(Copy_View.base, Copy_Owner)
        self.assertTrue(Copy_View.flags.writeable)
        self.assertFalse(Copy_Owner.flags.writeable)
        Copy_View[0] = 99
        self.assertEqual(Copy_Owner[0], 99)
        self.assertEqual(Owner[0], 0)
        Singleton = Numpy.ndarray((1, 3), dtype=Numpy.int64, strides=(900, 8))
        Singleton[:] = 7
        Clone, = _Copy((Singleton,))
        self.assertEqual(Clone.strides, Singleton.strides)
        self.assertIsNone(Clone.base)
        Numpy.testing.assert_array_equal(Clone, Singleton)

    def test_Timing_Batches_Respect_Bytes_And_Discard_Partial_Rounds(self):
        import numpy as Numpy
        from PyCeler.Selection_Inputs import _Isolation_Limit
        Values = Numpy.zeros(2 * 1024 * 1024, dtype=Numpy.int64)
        Calls = []
        def _Measure(Function, Args, Count, Deadline=None):
            Calls.append(Count)
            return 1
        with patch("PyCeler.Selection_Worker._Measure", side_effect=_Measure):
            _Time({"Python": lambda Item: Item}, (Values[:1],), 1, 1.1)
        self.assertLessEqual(max(Calls) * _Storage_Bytes((Values[:1],)), _Isolation_Limit)
        with patch("PyCeler.Selection_Worker._Measure", side_effect=[1] * 7 + [_Probe_Timeout()]):
            self.assertEqual(_Time({"Python": lambda: 0, "Serial": lambda: 0}, (), 1, 1.1), {})

    def test_Representative_Holdouts_Precede_Synthetic_Cases_And_Remain_Pending(self):
        Item = dict(Probe="Run", Kind="scalar", Arguments=1, Size_Arguments=[0], Eligible=["Python", "Serial"], Tuning=dict(Budget_Seconds=20))
        Representative = [("int", 100, (), (100,), dict(Label="production", Representative=True, Holdout=False)),
                          ("int", 120, (), (120,), dict(Label="holdout", Representative=True, Holdout=True))]
        Visited = []
        Checkpoints = []
        def _Case(Item, Modules, Threads, Gain, Teams, Input, Deadline, Invalid):
            Visited.append(Input[1])
            raise _Probe_Timeout("controlled deadline")
        def _Checkpoint(Cases):
            Checkpoints.append(json.loads(json.dumps(Cases)))
        with patch("PyCeler.Selection_Worker._Representative_Cases", return_value=Representative), patch("PyCeler.Selection_Worker._Cases", return_value=[("int", 4, (), (4,))]), patch("PyCeler.Selection_Worker._Check_Case", side_effect=_Case):
            Cases = _Check(Item, {"Python": types.SimpleNamespace(Run=lambda Count: Count)}, 0, 1.1, Checkpoint=_Checkpoint)
        self.assertEqual(Visited, [120, 100, 4])
        self.assertEqual(len(Checkpoints[0]), 3)
        self.assertTrue(Checkpoints[0][0]["Holdout"])
        self.assertTrue(all(Case["Validation"]["Python"].startswith("inconclusive") for Case in Cases))
        self.assertTrue(all(Mode == 0 for Bound, Mode in _Selection_Table(Cases, 1.1, True)["int"]))

    def test_Live_OpenMP_Settings_And_Opt_In_Dispatch_Observation(self):
        from PyCeler import Compile
        with Temporary_Directory(dir=self._Root / "Test_Run") as Folder:  # Keep generated sources and binaries outside the maintained fixture tree.
            Work = Path(Folder)
            Runtime = (self._Root / "PyCeler" / "Dispatch_Runtime.pxi.in").read_text(encoding="utf-8")
            Runtime += (self._Root / "PyCeler" / "Selection_Runtime.pxi.in").read_text(encoding="utf-8")
            Runtime = Runtime.replace("ENVIRONMENT_MATCH", "True").replace("THREAD_BASELINE", "None")
            Runtime = Runtime.replace("THREAD_CURRENT", "[_Maximum(), _Dynamic()]").replace("NUMPY_CHECK", "")
            Source = Work / "Dispatch_Check.pyx"
            Source.write_text("from openmp cimport omp_get_max_threads as _Maximum, omp_get_dynamic as _Dynamic, omp_set_num_threads as _Set\n" + Runtime +
                              "\ndef Choose(Count):\n    return _Pyceler_Choose((Count,), True, {'int': [(16, 2), (0, 0)]})\n" +
                              "\ndef Set_Threads(Count):\n    _Set(Count)\n", encoding="utf-8")
            with patch.dict(os.environ, PYCELER_BUILD_DIR=str(Work / "Build")):
                Binary = Compile(Source, Work / "Native", Convert=False, OpenMP=True)  # Build a real extension; a static finding alone does not prove native execution.
            Program = "\n".join(("import sys", "sys.path.insert(0, sys.argv[1])", "import Dispatch_Check as M",
                                 "assert M.Choose(100) == 2", "assert M._Pyceler_Dispatch_Stats() == {}",
                                 "M._Pyceler_Dispatch_Stats(True)", "assert M.Choose(4) == 0",
                                 "assert M._Pyceler_Dispatch_Stats()['Selection']['Reason'] == 'measured_python_band'",
                                 "M.Set_Threads(3)", "assert M.Choose(100) == 0",
                                 "assert M._Pyceler_Dispatch_Stats()['Selection']['Reason'] == 'thread_settings_changed'",
                                 "M.Set_Threads(2)", "assert M.Choose(100) == 2"))
            Result = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary.parent)], capture_output=True, text=True,
                                    env=dict(os.environ, OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE"), timeout=30)
            self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
