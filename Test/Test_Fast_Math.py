import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PyCeler import Analyze, Compile, Convert
from PyCeler.Selection_Worker import _Observe
from Test.Workspace import Temporary_Directory

class Unboxed_Math(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]
    _Fixture = _Root / "Test" / "Fast_Math_Loops.py"
    _Rounding_Probe = '''
cdef extern from "fenv.h":
    int _Test_Nearest "FE_TONEAREST"
    int _Test_Down "FE_DOWNWARD"
    int _Test_Get_Rounding "fegetround"() noexcept nogil
    int _Test_Set_Rounding "fesetround"(int) noexcept nogil
    int _Test_All_Exceptions "FE_ALL_EXCEPT"
    int _Test_Exception_Flags "fetestexcept"(int) noexcept nogil
    int _Test_Clear_Exceptions "feclearexcept"(int) noexcept nogil

cdef bint _Test_Allocation_Failure = False

def _Test_Allocation(bint Fail):
    global _Test_Allocation_Failure
    _Test_Allocation_Failure = Fail

def _Test_Floating_Status(bint Clear=False):
    cdef int Previous = _Test_Exception_Flags(_Test_All_Exceptions)
    if Clear:
        _Test_Clear_Exceptions(_Test_All_Exceptions)
    return Previous

def _Test_Rounding(bint Down):
    cdef int Previous = _Test_Get_Rounding()
    _Test_Set_Rounding(_Test_Down if Down else _Test_Nearest)
    return Previous

def _Test_Restore_Rounding(int Previous):
    _Test_Set_Rounding(Previous)
'''
    _Worker_Probe = '''
from cython.parallel cimport prange as _Test_Threads
from openmp cimport omp_set_num_threads as _Test_Set_Threads, omp_get_max_threads as _Test_Max_Threads, omp_set_dynamic as _Test_Set_Dynamic, omp_get_dynamic as _Test_Dynamic
cdef extern from *:
    """
    #if defined(_M_X64) || defined(__x86_64__)
    #include <xmmintrin.h>
    static int _Pyceler_Test_Control_Available(void) { return 1; }
    static unsigned int _Pyceler_Test_Control_Read(void) { return _mm_getcsr(); }
    static void _Pyceler_Test_Control_Write(unsigned int Value) { _mm_setcsr(Value); }
    #else
    static int _Pyceler_Test_Control_Available(void) { return 0; }
    static unsigned int _Pyceler_Test_Control_Read(void) { return 0; }
    static void _Pyceler_Test_Control_Write(unsigned int Value) { (void)Value; }
    #endif
    """
    int _Pyceler_Test_Control_Available() noexcept nogil
    unsigned int _Pyceler_Test_Control_Read() noexcept nogil
    void _Pyceler_Test_Control_Write(unsigned int) noexcept nogil

def _Test_Worker_Rounding(bint Down):
    cdef int Position
    for Position in _Test_Threads(2, nogil=True, num_threads=2, schedule='static'):
        _Test_Set_Rounding(_Test_Down if Down else _Test_Nearest)

def _Test_Worker_Modes():
    cdef int Position, Modes[2]
    for Position in _Test_Threads(2, nogil=True, num_threads=2, schedule='static'):
        Modes[Position] = _Test_Get_Rounding()
    return Modes[0], Modes[1]

def _Test_Worker_Controls():
    cdef int Position
    cdef unsigned int Values[2]
    if not _Pyceler_Test_Control_Available():
        return None
    for Position in _Test_Threads(2, nogil=True, num_threads=2, schedule='static'):
        Values[Position] = _Pyceler_Test_Control_Read()
    return Values[0], Values[1]

def _Test_Worker_Flush():
    cdef int Position
    for Position in _Test_Threads(2, nogil=True, num_threads=2, schedule='static'):
        if Position == 1:
            _Pyceler_Test_Control_Write(_Pyceler_Test_Control_Read() | 0x8040)

def _Test_Worker_Restore_Controls(unsigned int First, unsigned int Second):
    cdef int Position
    for Position in _Test_Threads(2, nogil=True, num_threads=2, schedule='static'):
        _Pyceler_Test_Control_Write(First if Position == 0 else Second)

def _Test_Thread_Settings(int Threads, int Dynamic):
    Previous = (_Test_Max_Threads(), _Test_Dynamic())
    _Test_Set_Threads(Threads)
    _Test_Set_Dynamic(Dynamic)
    return Previous
'''

    def setUp(self):
        Workspace = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Workspace.cleanup)
        self._Folder = Path(Workspace.name)
        Environment = patch.dict(os.environ, PYCELER_BUILD_DIR=str(self._Folder / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
        Environment.start()
        self.addCleanup(Environment.stop)

    def test_Unboxed_Math_Source_Contains_Native_Doubles_And_Prange(self):
        Findings = Analyze(self._Fixture, OpenMP=True)
        self.assertEqual(len(Findings), 26)
        Source = Convert(self._Fixture, self._Folder / "Converted", Select=False, OpenMP=True).read_text(encoding="utf-8")
        self.assertIn("cdef volatile double", Source)
        self.assertIn("const double[::1]", Source)
        self.assertIn("Prange", Source)
        self.assertIn("Native_Elements", Source)

    def test_Huge_Integer_Literals_Remain_Ordered_Without_Analysis_Overflow(self):
        Source = self._Folder / "Huge_Math_Literal.py"
        Source.write_text("import math\ndef Map(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = math.sin(Source[Index]) + " + "1" + "0" * 1000 + "\n    return Output\n", encoding="utf-8")
        Findings = Analyze(Source)
        self.assertEqual(len(Findings), 1)
        Converted = Convert(Source, self._Folder / "Huge_Converted", Select=False).read_text(encoding="utf-8")
        self.assertNotIn("cdef Py_ssize_t _Pyceler_Fast_Math_", Converted)

    def test_Observation_Profiles_Uninstrumented_Fallback(self):
        Namespace = {}
        exec(compile("def Original(Value):\n    return Value\ndef Candidate(Value):\n    return Original(Value)\n", "Reference.py", "exec"), Namespace)
        Observation = {}
        Outcome, Fallback = _Observe(Namespace["Candidate"], (7,), "Original", Observation)
        self.assertTrue(Fallback, Observation)
        self.assertTrue(Observation["Python_Fallback"])
        self.assertIsNone(Observation["Native_Entry"])
        self.assertIsNone(sys.getprofile())

    def test_Thin_Libm_Exact_Bits_Exceptions_Continuation_And_Teams(self):
        for Parallel in (False, True):
            with self.subTest(Parallel=Parallel):
                Converted = Convert(self._Fixture, self._Folder / ("Parallel_Source" if Parallel else "Serial_Source"), Select=False, OpenMP=Parallel)
                Text = Converted.read_text(encoding="utf-8").replace("    Scratch = <double*>", "    Scratch = NULL if _Test_Allocation_Failure else <double*>") + self._Rounding_Probe + (self._Worker_Probe if Parallel else "")
                Converted.write_text(Text, encoding="utf-8")
                Binary = Compile(Converted, self._Folder / ("Parallel" if Parallel else "Serial"), Convert=False, OpenMP=Parallel)
                Result = subprocess.run([sys.executable, "-I", "-B", str(self._Root / "Test" / "Fast_Math_Probe.py"), str(Binary), str(self._Fixture),
                                         "parallel" if Parallel else "serial", str(Path(sys.modules["PyCeler"].__file__).resolve().parent.parent)], capture_output=True, text=True, timeout=180)
                self.assertEqual(Result.returncode, 0, Result.stdout + Result.stderr)
                Report = json.loads(Result.stdout)
                self.assertGreaterEqual(Report["Comparisons"], 148)
                self.assertEqual(len(Report["Native_Functions"]), 26)
                self.assertEqual(len(Report["Parallel_Functions"]), 26 if Parallel else 0)

    def test_Measured_Selection_Observes_Unboxed_Team_And_Reuses_Cache(self):
        Source = self._Folder / "Measured_Math.py"
        Source.write_text("import math\ndef Compute(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = math.sin(Source[Index]) + math.cos(Source[Index])\n    return Output\n", encoding="utf-8")
        Factory = self._Folder / "Measured_Math_Cases.py"
        Factory.write_text("import numpy as N\ndef Cases():\n    Source = N.linspace(0.1, 9.0, 4096, dtype=N.float64)\n    return [dict(Args=(Source, N.zeros_like(Source)), Label='Finite float64 math', Holdout=True)]\n", encoding="utf-8")
        Options = dict(OpenMP=True, Tuning=dict(Threads=[2], Budget_Seconds=8), Cache=self._Folder / "Cache", Workloads={"Compute": dict(File=Factory, Factory="Cases")})
        Converted = Convert(Source, self._Folder / "First", **Options)
        Report = json.loads(Converted.with_suffix(".selection.json").read_text(encoding="utf-8"))
        Item = Report["Items"][0]
        self.assertEqual(set(Item["Unboxed_Math"]), {"sin", "cos"})
        for Variant, Team in (("Serial", 1), ("OpenMP_2", 2)):
            Cases = [Case for Case in Item["Cases"] if Case["Validation"].get(Variant) == "valid" and Case["Observations"].get(Variant, {}).get("Actual_Team") == Team]
            self.assertTrue(Cases, (Variant, Item))
            self.assertTrue(any(Case["Observations"][Variant].get("Native_Entry") for Case in Cases), (Variant, Cases))
        self.assertEqual(Report["Cache"]["Status"], "miss", Report.get("Cache"))
        Reused = Convert(Source, self._Folder / "Second", **Options)
        Cached = json.loads(Reused.with_suffix(".selection.json").read_text(encoding="utf-8"))
        self.assertEqual(Cached["Cache"]["Status"], "hit")
        self.assertEqual(Cached["Cache"]["Key"], Report["Cache"]["Key"])
        Manifest = json.loads((Path(Report["Cache"]["Directory"]) / "Result.json").read_text(encoding="utf-8"))["Manifest"]
        self.assertTrue(any(Name.startswith("Math_Registry.") for Name, Digest in Manifest["Engine"]))
        self.assertTrue(any(Name.startswith("Fast_Math.") for Name, Digest in Manifest["Engine"]))
        from PyCeler.Selection_Cache import _Cache_Context, _Normalize_Workloads
        from PyCeler.Selection_Policy import _Normalize_Tuning
        Configuration = dict(Tuning=_Normalize_Tuning(Options["Tuning"]), Profile=False)
        Workloads = _Normalize_Workloads(Options["Workloads"])
        Before = _Cache_Context(Source, "abi", "3.11", True, 1.1, Workloads, Options["Cache"], Configuration=Configuration)
        Source.write_text(Source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        After = _Cache_Context(Source, "abi", "3.11", True, 1.1, Workloads, Options["Cache"], Configuration=Configuration)
        self.assertNotEqual(Before[1], After[1])
