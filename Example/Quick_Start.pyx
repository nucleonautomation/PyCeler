import builtins as _Pyceler_Python_Builtins
cdef void _Pyceler_Direct_Unbound(object Error):
    Text = _Pyceler_Python_Builtins.str(Error)
    if Text.startswith("local variable ") and Text.endswith(" referenced before assignment"):
        Name = Text[_Pyceler_Python_Builtins.len("local variable "):-_Pyceler_Python_Builtins.len(" referenced before assignment")]
        Error.args = ("cannot access local variable " + Name + " where it is not associated with a value",)
cdef object _Pyceler_Direct_Value(dict Namespace, str Name):
    if Name in Namespace:
        return Namespace[Name]
    Builtins = Namespace.get("__builtins__", _Pyceler_Python_Builtins)
    if not _Pyceler_Python_Builtins.isinstance(Builtins, _Pyceler_Python_Builtins.dict):
        Builtins = _Pyceler_Python_Builtins.vars(Builtins)
    if Name in Builtins:
        return Builtins[Name]
    raise _Pyceler_Python_Builtins.NameError("name " + _Pyceler_Python_Builtins.repr(Name) + " is not defined", name=Name)
from cpython.exc cimport PyErr_CheckSignals as _Pyceler_Direct_Signals
cdef unsigned int _Pyceler_Direct_Ticks = 0
cdef void _Pyceler_Direct_Checkpoint() except *:
    global _Pyceler_Direct_Ticks
    _Pyceler_Direct_Ticks += 1
    if _Pyceler_Direct_Ticks & 1023 == 0:
        _Pyceler_Direct_Signals()
        with nogil:
            pass
cdef dict _Pyceler_Direct_Globals():
    return globals()
cdef object _Pyceler_Direct_Set_Global(str Name, object Value):
    globals()[Name] = Value
    return Value
cdef object _Pyceler_Direct_Empty = _Pyceler_Python_Builtins.object()
cdef bint _Pyceler_Direct_Unreachable():
    return False
cdef object _Pyceler_Direct_Cell_Value(object Value, str Name, bint Free):
    if Value is not _Pyceler_Direct_Empty:
        return Value
    if Free:
        raise _Pyceler_Python_Builtins.NameError("cannot access free variable " + _Pyceler_Python_Builtins.repr(Name) + " where it is not associated with a value in enclosing scope", name=Name)
    raise _Pyceler_Python_Builtins.UnboundLocalError("cannot access local variable " + _Pyceler_Python_Builtins.repr(Name) + " where it is not associated with a value")
cdef bint _Pyceler_Dispatch_Enabled = False
cdef dict _Pyceler_Dispatch_Info = {}
cdef dict _Pyceler_Guard_Info = {}
# Expose opt-in dispatch and guard counters without changing ordinary numerical results.
def _Pyceler_Dispatch_Stats(Enabled=None, Reset=False):
    import builtins as B
    global _Pyceler_Dispatch_Enabled
    if Enabled is not None:
        if B.type(Enabled) is not B.bool:
            raise B.TypeError("Enabled must be a boolean or None")
        _Pyceler_Dispatch_Enabled = Enabled
    if Reset:
        _Pyceler_Dispatch_Info.clear()
        _Pyceler_Guard_Info.clear()
    return {Stage: B.dict(Details) for Stage, Details in _Pyceler_Dispatch_Info.items()}

def _Pyceler_Guard_Stats():
    return {Region: dict(Counts) for Region, Counts in _Pyceler_Guard_Info.items()}

cdef void _Pyceler_Guard_Event(object Region, object Reason) except *:
    if _Pyceler_Dispatch_Enabled:
        Counts = _Pyceler_Guard_Info.setdefault(Region, {})
        Counts[Reason] = Counts.get(Reason, 0) + 1
        _Pyceler_Dispatch_Info['Guard'] = dict(Region=Region, Reason=Reason)

cdef void _Pyceler_Dispatch_Event(object Stage, object Reason, object Team=None) except *:
    if _Pyceler_Dispatch_Enabled:
        Details = {"Reason": Reason, "Actual_Team": Team}
        if Stage == "Execution":
            Details["Native_Entry"] = Reason in ("native_serial", "native_parallel")
            if Details['Native_Entry']:
                Totals = _Pyceler_Dispatch_Info.setdefault('Totals', dict(Native_Entries=0, Parallel_Entries=0, Maximum_Team=0))
                Totals['Native_Entries'] += 1
                Totals['Parallel_Entries'] += Reason == 'native_parallel'
                Totals['Maximum_Team'] = max(Totals['Maximum_Team'], Team or 1)
        _Pyceler_Dispatch_Info[Stage] = Details


from libc.string cimport memset as _Pyceler_Memset
from cython cimport boundscheck as _Pyceler_Bounds, wraparound as _Pyceler_Wrap
from cython.parallel cimport prange as _Pyceler_Prange
from openmp cimport omp_in_parallel as _Pyceler_In_Parallel, omp_get_max_threads as _Pyceler_Max_Threads, omp_get_num_threads as _Pyceler_Reduction_Team, omp_get_dynamic as _Pyceler_Dynamic
cdef extern from "Python.h":
    char _Pyceler_Range_Type "PyRange_Type"
    char _Pyceler_Int_Type "PyLong_Type"
    bint _Pyceler_Is_C_Function "PyCFunction_Check"(object)
# Shared runtime binding, storage and observer guards used before entering specialized kernels.
def _Pyceler_Scheduler_Yield():
    with nogil:
        pass

cdef bint _Pyceler_Bindings(object Baseline):
    import builtins as _Pyceler_Builtins
    Namespace = Baseline.__globals__
    Builtins = Baseline.__builtins__
    Range = Namespace.get("range", Builtins.get("range"))
    Length_Function = Namespace.get("len", Builtins.get("len"))
    return (<void*>Range == <void*>&_Pyceler_Range_Type and _Pyceler_Is_C_Function(Length_Function)
            and Length_Function.__self__ is _Pyceler_Builtins and Length_Function.__name__ == "len")

cdef bint _Pyceler_Array(object Values, object Numpy, int Dimensions, bint Pixels=False):
    import builtins as _Pyceler_Builtins
    return (Numpy is not None and _Pyceler_Builtins.type(Values) is _Pyceler_Builtins.getattr(Numpy, "ndarray", None)
            and Values.ndim == Dimensions and Values.flags.c_contiguous and Values.flags.aligned
            and Values.dtype.isnative and Values.dtype.metadata is None
            and ((Values.dtype.kind in ("i", "f") and Values.dtype.itemsize in (4, 8)) or
                 (Pixels and Values.dtype.kind in ("i", "u") and Values.dtype.itemsize in (1, 2))))

cdef bint _Pyceler_Byte_Source(object Source, object Output):
    import builtins as B
    if B.type(Source) is B.bytes or B.type(Source) is B.bytearray:
        return True
    if B.type(Source) is B.memoryview:
        try:
            return (Source.ndim == 1 and Source.format == "B" and Source.c_contiguous and
                    B.type(Source.obj) in (B.bytes, B.bytearray) and Source.obj is not Output)
        except ValueError:
            return False
    return False

cdef bint _Pyceler_Extent(object Output, int Axis, object Size):
    import sys as S
    import builtins as B
    N = S.modules.get("numpy")
    return N is not None and B.type(Output) is N.ndarray and Axis < Output.ndim and B.type(Size) is B.int and Output.shape[Axis] == Size



from cpython.object cimport PyObject as _Pyceler_Numeric_8_Object
cdef extern from "Python.h":
    _Pyceler_Numeric_8_Object* _Pyceler_Numeric_8_Name_Error_Type "PyExc_NameError"
_Pyceler_Numeric_8_Name_Error = <object>_Pyceler_Numeric_8_Name_Error_Type

cdef extern from "fenv.h":
    int _Pyceler_Numeric_8_Clear_Exceptions "feclearexcept"(int) noexcept nogil
    int _Pyceler_Numeric_8_Invalid "FE_INVALID"
    int _Pyceler_Numeric_8_Divide "FE_DIVBYZERO"
    int _Pyceler_Numeric_8_Overflow "FE_OVERFLOW"
    int _Pyceler_Numeric_8_Underflow "FE_UNDERFLOW"
from libc.stdint cimport uint64_t as _Pyceler_Module_Constants_8_UInt64
from libc.string cimport memcpy as _Pyceler_Module_Constants_8_Copy_Bits
cdef _Pyceler_Module_Constants_8_UInt64 _Pyceler_Module_Constants_8_Bits(object Value) except *:
    cdef double Number = Value
    cdef _Pyceler_Module_Constants_8_UInt64 Pattern
    if sizeof(Number) != sizeof(Pattern):
        raise TypeError('Unsupported native floating representation')
    _Pyceler_Module_Constants_8_Copy_Bits(&Pattern, &Number, sizeof(Pattern))
    return Pattern
cdef object _Pyceler_Module_Constants_8_Key(object Value):
    import builtins as B
    cdef object Kind = B.type(Value)
    if Value is None or Value is Ellipsis or Kind in (B.bool, B.int, B.str, B.bytes):
        return Kind, Value
    if Kind is B.float:
        return Kind, _Pyceler_Module_Constants_8_Bits(Value)
    if Kind is B.complex:
        return Kind, _Pyceler_Module_Constants_8_Bits(Value.real), _Pyceler_Module_Constants_8_Bits(Value.imag)
    if Kind is B.tuple:
        return Kind, B.tuple(_Pyceler_Module_Constants_8_Key(Item) for Item in Value)
    if Kind is B.frozenset:
        return Kind, B.frozenset(_Pyceler_Module_Constants_8_Key(Item) for Item in Value)
    return None
cdef dict _Pyceler_Module_Constants_8_Pool(object Code):
    import builtins as B
    cdef object Code_Type = B.type(Code)
    cdef list Pending = [Code]
    cdef dict Pool = {}
    cdef object Value, Key
    while Pending:
        Value = Pending.pop()
        if B.type(Value) is Code_Type:
            Pending.extend(Value.co_consts)
            continue
        Key = _Pyceler_Module_Constants_8_Key(Value)
        if Key is not None and Key not in Pool:
            Pool[Key] = Value
        if B.type(Value) in (B.tuple, B.frozenset):
            Pending.extend(Value)
    return Pool
cdef object _Pyceler_Module_Constants_8_Value(object Value, dict Pool, object Code_Type):
    import builtins as B
    cdef object Key, Kind = B.type(Value)
    if Kind is Code_Type:
        return _Pyceler_Module_Constants_8_Code(Value, Pool)
    Key = _Pyceler_Module_Constants_8_Key(Value)
    if Key is not None and Key in Pool:
        return Pool[Key]
    if Kind is B.tuple:
        return B.tuple(_Pyceler_Module_Constants_8_Value(Item, Pool, Code_Type) for Item in Value)
    if Kind is B.frozenset:
        return B.frozenset(_Pyceler_Module_Constants_8_Value(Item, Pool, Code_Type) for Item in Value)
    return Value
cdef object _Pyceler_Module_Constants_8_Code(object Code, dict Pool):
    if callable(Code):
        return Code
    import builtins as B
    cdef object Code_Type = B.type(Code)
    return Code.replace(co_consts=B.tuple(_Pyceler_Module_Constants_8_Value(Value, Pool, Code_Type) for Value in Code.co_consts))

from libc.math cimport fabs as _Pyceler_Fast_8_fabs, isfinite as _Pyceler_Fast_8_isfinite, isinf as _Pyceler_Fast_8_isinf, isnan as _Pyceler_Fast_8_isnan, signbit as _Pyceler_Fast_8_signbit, sin as _Pyceler_Fast_8_sin, sqrt as _Pyceler_Fast_8_sqrt
from libc.stdlib cimport malloc as _Pyceler_Fast_8_Allocate, free as _Pyceler_Fast_8_Free
from libc.stdint cimport uintptr_t as _Pyceler_Fast_8_Address
from cython cimport boundscheck as _Pyceler_Fast_8_Bounds, wraparound as _Pyceler_Fast_8_Wrap, cdivision as _Pyceler_Fast_8_Division
from libc.errno cimport ERANGE as _Pyceler_Fast_8_ERANGE
cdef extern from "Python.h":
    int _Pyceler_Fast_8_Signals "PyErr_CheckSignals"() except -1
cdef extern from "fenv.h":
    int _Pyceler_Fast_8_Nearest "FE_TONEAREST"
    int _Pyceler_Fast_8_Rounding "fegetround"() noexcept nogil
    ctypedef struct _Pyceler_Fast_8_Environment "fenv_t":
        pass
    int _Pyceler_Fast_8_Get_Environment "fegetenv"(_Pyceler_Fast_8_Environment*) noexcept nogil
    int _Pyceler_Fast_8_Set_Environment "fesetenv"(const _Pyceler_Fast_8_Environment*) noexcept nogil
    ctypedef struct _Pyceler_Fast_8_Exception_State "fexcept_t":
        pass
    int _Pyceler_Fast_8_All_Exceptions "FE_ALL_EXCEPT"
    int _Pyceler_Fast_8_Test_Exceptions "fetestexcept"(int) noexcept nogil
    int _Pyceler_Fast_8_Set_Exceptions "fesetexceptflag"(const _Pyceler_Fast_8_Exception_State*, int) noexcept nogil
cdef extern from *:
    """
    #include <errno.h>
    #include <stdint.h>
    #include <string.h>
    static inline int* _Pyceler_Fast_8_Error_Address(void) { return &errno; }
    static inline int _Pyceler_Fast_8_Finite(double Value) {
        uint64_t Bits;
        memcpy(&Bits, &Value, sizeof(Bits));
        return (Bits & UINT64_C(0x7ff0000000000000)) != UINT64_C(0x7ff0000000000000);
    }
    static int _Pyceler_Fast_8_Prepare_Exceptions(int Flags, fexcept_t* Prepared) {
        fenv_t Saved;
        int Result;
        if (feholdexcept(&Saved) != 0) return -1;
        Result = feraiseexcept(Flags);
        if (Result == 0) Result = fegetexceptflag(Prepared, Flags);
        if (fesetenv(&Saved) != 0) return -1;
        return Result;
    }
    """
    int* _Pyceler_Fast_8_Error_Address() noexcept nogil
    bint _Pyceler_Fast_8_Finite(double) noexcept nogil
    int _Pyceler_Fast_8_Prepare_Exceptions(int, _Pyceler_Fast_8_Exception_State*) noexcept nogil
from cython.parallel cimport prange as _Pyceler_Fast_8_Prange
from openmp cimport omp_get_num_threads as _Pyceler_Fast_8_Team_Size, omp_get_max_threads as _Pyceler_Fast_8_Max_Threads, omp_in_parallel as _Pyceler_Fast_8_In_Parallel
import math as _Pyceler_Fast_8_Math
import types as _Pyceler_Fast_8_Types
import builtins as _Pyceler_Fast_8_Builtins
import sys as _Pyceler_Fast_8_System
import signal as _Pyceler_Fast_8_Signal
import threading as _Pyceler_Fast_8_Threading
cdef tuple _Pyceler_Fast_8_Functions = tuple(getattr(_Pyceler_Fast_8_Math, Name, None) for Name in ('sin', 'sqrt'))
cdef unsigned long long _Pyceler_Fast_8_Native_Elements = 0, _Pyceler_Fast_8_Parallel_Elements = 0
cdef int _Pyceler_Fast_8_Last_Team = 0
def _Pyceler_Fast_8_Stats():
    return dict(Native_Elements=_Pyceler_Fast_8_Native_Elements, Parallel_Elements=_Pyceler_Fast_8_Parallel_Elements, Team=_Pyceler_Fast_8_Last_Team)
cdef bint _Pyceler_Fast_8_Exclusive():
    S = _Pyceler_Fast_8_System
    G = _Pyceler_Fast_8_Signal
    T = _Pyceler_Fast_8_Threading
    if _Pyceler_Fast_8_Rounding() != _Pyceler_Fast_8_Nearest or T.current_thread() is not T.main_thread() or len(S._current_frames()) != 1 or S.gettrace() is not None or S.getprofile() is not None or not _Pyceler_Fast_8_Monitoring_Code():
        return False
    for Number in G.valid_signals():
        Handler = G.getsignal(Number)
        if Handler is not None and Handler is not G.SIG_DFL and Handler is not G.SIG_IGN and Handler is not G.default_int_handler:
            return False
    return True
cdef bint _Pyceler_Fast_8_Bindings(dict Namespace):
    cdef object Function, Module
    Function = _Pyceler_Fast_8_Functions[0]
    if _Pyceler_Fast_8_Builtins.type(Function) is not _Pyceler_Fast_8_Types.BuiltinFunctionType or Function.__self__ is not _Pyceler_Fast_8_Math or Function.__name__ != 'sin':
        return False
    if _Pyceler_Fast_8_Builtins.getattr(_Pyceler_Fast_8_Math, 'sin', None) is not Function:
        return False
    Function = _Pyceler_Fast_8_Functions[1]
    if _Pyceler_Fast_8_Builtins.type(Function) is not _Pyceler_Fast_8_Types.BuiltinFunctionType or Function.__self__ is not _Pyceler_Fast_8_Math or Function.__name__ != 'sqrt':
        return False
    if _Pyceler_Fast_8_Builtins.getattr(_Pyceler_Fast_8_Math, 'sqrt', None) is not Function:
        return False
    if Namespace.get('math') is not _Pyceler_Fast_8_Math:
        return False
    if Namespace.get('math') is not _Pyceler_Fast_8_Math:
        return False
    return True
from cpython.module cimport PyModule_CheckExact as _Pyceler_Fast_8_Monitoring_Module
cdef extern from "Python.h":
    int _Pyceler_Fast_8_Monitoring_Function "PyCFunction_Check"(object Value)
    const char* _Pyceler_Fast_8_Monitoring_Version "Py_GetVersion"()
cdef str _Pyceler_Fast_8_Monitoring_Runtime = (<bytes>_Pyceler_Fast_8_Monitoring_Version()).decode("ascii")
cdef int _Pyceler_Fast_8_Monitoring_Mode = 0 if _Pyceler_Fast_8_Monitoring_Runtime.startswith("3.11.") else 1 if _Pyceler_Fast_8_Monitoring_Runtime.startswith(("3.12.", "3.13.", "3.14.")) else 2
cdef object _Pyceler_Fast_8_Monitoring = _Pyceler_Fast_8_System.__dict__.get("monitoring")
cdef bint _Pyceler_Fast_8_Monitoring_Code(object Code=None):
    cdef object Monitor, Events, Local, Frame
    if _Pyceler_Fast_8_Monitoring_Mode == 0:
        return True
    Monitor = _Pyceler_Fast_8_Monitoring
    if _Pyceler_Fast_8_Monitoring_Mode != 1 or not _Pyceler_Fast_8_Monitoring_Module(Monitor) or _Pyceler_Fast_8_System.__dict__.get("monitoring") is not Monitor:
        return False
    Events, Local = Monitor.__dict__.get("get_events"), Monitor.__dict__.get("get_local_events")
    for Name, Function in (("get_events", Events), ("get_local_events", Local)):
        if not _Pyceler_Fast_8_Monitoring_Function(Function) or Function.__self__ is not Monitor or Function.__name__ != Name:
            return False
    if Code is None:
        Frame = _Pyceler_Fast_8_System.__dict__.get("_getframe")
        if not _Pyceler_Fast_8_Monitoring_Function(Frame) or Frame.__self__ is not _Pyceler_Fast_8_System or Frame.__name__ != "_getframe":
            return False
        Code = Frame().f_code
    for Tool in range(6):
        if Events(Tool) or Local(Tool, Code):
            return False
    return True

def _Pyceler_Numeric_8_Body(Namespace):
    for Namespace['row'] in _Pyceler_Direct_Value(Namespace, 'range')(_Pyceler_Direct_Value(Namespace, 'row'), _Pyceler_Direct_Value(Namespace, 'row') + 1):
        _Pyceler_Direct_Checkpoint()
        for Namespace['column'] in _Pyceler_Direct_Value(Namespace, 'range')(_Pyceler_Direct_Value(Namespace, 'len')(_Pyceler_Direct_Value(Namespace, 'values')[0])):
            _Pyceler_Direct_Checkpoint()
            Namespace['value'] = _Pyceler_Direct_Value(Namespace, 'values')[_Pyceler_Direct_Value(Namespace, 'row'), _Pyceler_Direct_Value(Namespace, 'column')]
            _Pyceler_Direct_Value(Namespace, 'output')[_Pyceler_Direct_Value(Namespace, 'row'), _Pyceler_Direct_Value(Namespace, 'column')] = _Pyceler_Direct_Value(Namespace, 'math').sin(_Pyceler_Direct_Value(Namespace, 'value')) + _Pyceler_Direct_Value(Namespace, 'math').sqrt(_Pyceler_Direct_Value(Namespace, 'value') + 1.0)

cdef bint _Pyceler_Fast_8_Integer_Copy(void* Source, double* Target, Py_ssize_t Count, int Kind) noexcept nogil:
    cdef Py_ssize_t Position
    cdef long long Signed
    cdef unsigned long long Unsigned
    if Kind == 11:
        for Position in range(Count):
            Signed = (<signed char*>Source)[Position]
            if Signed < -1125899906842624LL or Signed > 1125899906842624LL:
                return False
            Target[Position] = <double>Signed
        return True
    if Kind == 12:
        for Position in range(Count):
            Signed = (<short*>Source)[Position]
            if Signed < -1125899906842624LL or Signed > 1125899906842624LL:
                return False
            Target[Position] = <double>Signed
        return True
    if Kind == 14:
        for Position in range(Count):
            Signed = (<int*>Source)[Position]
            if Signed < -1125899906842624LL or Signed > 1125899906842624LL:
                return False
            Target[Position] = <double>Signed
        return True
    if Kind == 18:
        for Position in range(Count):
            Signed = (<long long*>Source)[Position]
            if Signed < -1125899906842624LL or Signed > 1125899906842624LL:
                return False
            Target[Position] = <double>Signed
        return True
    if Kind == 21:
        for Position in range(Count):
            Unsigned = (<unsigned char*>Source)[Position]
            if Unsigned > 1125899906842624ULL:
                return False
            Target[Position] = <double>Unsigned
        return True
    if Kind == 22:
        for Position in range(Count):
            Unsigned = (<unsigned short*>Source)[Position]
            if Unsigned > 1125899906842624ULL:
                return False
            Target[Position] = <double>Unsigned
        return True
    if Kind == 24:
        for Position in range(Count):
            Unsigned = (<unsigned int*>Source)[Position]
            if Unsigned > 1125899906842624ULL:
                return False
            Target[Position] = <double>Unsigned
        return True
    if Kind == 28:
        for Position in range(Count):
            Unsigned = (<unsigned long long*>Source)[Position]
            if Unsigned > 1125899906842624ULL:
                return False
            Target[Position] = <double>Unsigned
        return True
    return False
cdef inline bint _Pyceler_Fast_8_Scalar_Integer_Valid(double Value, int Kind) noexcept nogil:
    if Value < -1125899906842624.0 or Value > 1125899906842624.0:
        return False
    if Kind == 3 or Kind == 5:
        return Value == 0.0 or Value == 1.0
    if Kind == 11:
        return -128.0 <= Value <= 127.0
    if Kind == 12:
        return -32768.0 <= Value <= 32767.0
    if Kind == 14:
        return -2147483648.0 <= Value <= 2147483647.0
    if Kind == 21:
        return 0.0 <= Value <= 255.0
    if Kind == 22:
        return 0.0 <= Value <= 65535.0
    if Kind == 24:
        return 0.0 <= Value <= 4294967295.0
    if Kind == 28:
        return 0.0 <= Value <= 1125899906842624.0
    return True
cdef inline int _Pyceler_Fast_8_Scalar_Promote(int Left, int Right, bint Divide) noexcept nogil:
    cdef int Kind, Signed, Unsigned
    if Left == 2 or Right == 2:
        return 2
    if Left == 1 or Right == 1:
        Kind = Right if Left == 1 else Left
        return 2 if Kind >= 10 and Kind % 10 >= 4 else 1
    if Left == 0 or Right == 0:
        return 2 if Left >= 10 or Right >= 10 or Left == 3 or Right == 3 else 0
    if Divide:
        return 2 if Left >= 10 or Right >= 10 or Left == 3 or Right == 3 else 0
    if Left == 3:
        if Right == 3 or Right == 5:
            return 255
        return 18 if Right == 4 else Right
    if Right == 3:
        if Left == 5:
            return 255
        return 18 if Left == 4 else Left
    if Left < 10:
        return Right if Right >= 10 else 4
    if Right < 10:
        return Left
    if (Left < 20) == (Right < 20):
        return max(Left, Right)
    Signed = Left if Left < 20 else Right
    Unsigned = Right if Right >= 20 else Left
    if Signed % 10 > Unsigned % 10:
        return Signed
    return 2 if Unsigned == 28 else 10 + (Unsigned % 10) * 2
cdef int _Pyceler_Fast_8_Scalar_Kind(object Value, object N):
    import builtins as B
    Kind = B.type(Value)
    if Kind is int:
        return 4
    if Kind is float:
        return 0
    if Kind is bool:
        return 5
    if Kind is N.float32:
        return 1
    if Kind is N.float64:
        return 2
    if Kind is N.bool_:
        return 3
    if Kind is N.int8:
        return 11
    if Kind is N.int16:
        return 12
    if Kind is N.int32:
        return 14
    if Kind is N.int64:
        return 18
    if Kind is N.uint8:
        return 21
    if Kind is N.uint16:
        return 22
    if Kind is N.uint32:
        return 24
    if Kind is N.uint64:
        return 28
    return 255
cdef object _Pyceler_Fast_8_Scalar_Box(double Value, int Kind, object N):
    if Kind == 4:
        return int(Value)
    if Kind == 5:
        return bool(Value)
    if Kind == 1:
        return N.float32(Value)
    if Kind == 2:
        return N.float64(Value)
    if Kind == 3:
        return N.bool_(Value)
    if Kind == 11:
        return N.int8(Value)
    if Kind == 12:
        return N.int16(Value)
    if Kind == 14:
        return N.int32(Value)
    if Kind == 18:
        return N.int64(Value)
    if Kind == 21:
        return N.uint8(Value)
    if Kind == 22:
        return N.uint16(Value)
    if Kind == 24:
        return N.uint32(Value)
    if Kind == 28:
        return N.uint64(Value)
    return Value

from libc.math cimport pow as _Pyceler_Fast_8_Array_Power_Double, powf as _Pyceler_Fast_8_Array_Power_Float
cdef inline void _Pyceler_Fast_8_Array_Store(double* Output, Py_ssize_t Position, double Value, int Kind, bint Raw) noexcept nogil:
    if not Raw:
        Output[Position] = Value
        return
    if Kind == 1:
        (<float*>Output)[Position] = <float>Value
        return
    if Kind == 2:
        (<double*>Output)[Position] = <double>Value
        return
    if Kind == 3:
        (<unsigned char*>Output)[Position] = <unsigned char>Value
        return
    if Kind == 11:
        (<signed char*>Output)[Position] = <signed char>Value
        return
    if Kind == 12:
        (<short*>Output)[Position] = <short>Value
        return
    if Kind == 14:
        (<int*>Output)[Position] = <int>Value
        return
    if Kind == 18:
        (<long long*>Output)[Position] = <long long>Value
        return
    if Kind == 21:
        (<unsigned char*>Output)[Position] = <unsigned char>Value
        return
    if Kind == 22:
        (<unsigned short*>Output)[Position] = <unsigned short>Value
        return
    if Kind == 24:
        (<unsigned int*>Output)[Position] = <unsigned int>Value
        return
    if Kind == 28:
        (<unsigned long long*>Output)[Position] = <unsigned long long>Value
        return
cdef double _Pyceler_Fast_8_Array_Cast(double Value, int Kind, bint* Valid) noexcept nogil:
    if Kind == 1:
        Value = <float>Value
    elif Kind == 3:
        Value = 1.0 if Value != 0.0 else 0.0
    elif Kind >= 10:
        if Value < -1125899906842624.0 or Value > 1125899906842624.0:
            Valid[0] = False
            return 0.0
        Value = <long long>Value
        if (Kind == 11 and (Value < -128 or Value > 127)) or (Kind == 12 and (Value < -32768 or Value > 32767)) or (Kind == 14 and (Value < -2147483648.0 or Value > 2147483647.0)) or (Kind == 21 and (Value < 0 or Value > 255)) or (Kind == 22 and (Value < 0 or Value > 65535)) or (Kind == 24 and (Value < 0 or Value > 4294967295.0)) or (Kind == 28 and Value < 0):
            Valid[0] = False
    if not _Pyceler_Fast_8_Finite(Value):
        Valid[0] = False
    return Value
@_Pyceler_Fast_8_Division(True)
cdef double _Pyceler_Numeric_8_Compute(double** Buffers, unsigned char** Changed, Py_ssize_t** Shapes, Py_ssize_t** Strides, unsigned char* Buffer_Kinds, int* Output_Kinds, double* Inputs, unsigned char* Scalar_Kinds, double* Random_Values, Py_ssize_t Random_Limit, Py_ssize_t Random_Position, Py_ssize_t* Random_Consumed, Py_ssize_t Begin, Py_ssize_t End, Py_ssize_t Step, unsigned char* Assigned, bint* Valid) noexcept nogil:
    cdef Py_ssize_t Outer
    cdef unsigned int Ticks
    cdef int* Error = _Pyceler_Fast_8_Error_Address()
    cdef double L0, L1, L2
    cdef volatile double T3, T4, T5, T7, T8, T9, T10, T12, T13, T14, T15, T16, T17
    cdef unsigned char K5, K10
    cdef Py_ssize_t Cursor0, End0, Step0
    L0 = Inputs[0]
    L1 = Inputs[1]
    L2 = Inputs[2]
    Assigned[0] = 0
    Assigned[1] = 0
    Assigned[2] = 0
    Random_Consumed[0] = Random_Position
    Outer = Begin
    while (Step > 0 and Outer < End) or (Step < 0 and Outer > End):
        Ticks = 0
        L0 = Outer
        Outer += Step
        Assigned[0] = 1
        Scalar_Kinds[0] = 4
        Cursor0 = <Py_ssize_t>(0.0)
        if 0.0 < -Shapes[0][0] or 0.0 >= Shapes[0][0]:
            Valid[0] = False
            return 0.0
        T3 = Shapes[0][1]
        End0 = <Py_ssize_t>(T3)
        Step0 = <Py_ssize_t>(1.0)
        if Step0 == 0:
            Valid[0] = False
            return 0.0
        while (Step0 > 0 and Cursor0 < End0) or (Step0 < 0 and Cursor0 > End0):
            L1 = Cursor0
            Cursor0 += Step0
            Assigned[1] = 1
            Scalar_Kinds[1] = 4
            if L0 < -Shapes[0][0] or L0 >= Shapes[0][0]:
                Valid[0] = False
                return 0.0
            if L1 < -Shapes[0][1] or L1 >= Shapes[0][1]:
                Valid[0] = False
                return 0.0
            T4 = Buffers[0][(<Py_ssize_t>(L0) + (Shapes[0][0] if L0 < 0.0 else 0)) * Strides[0][0] + (<Py_ssize_t>(L1) + (Shapes[0][1] if L1 < 0.0 else 0)) * Strides[0][1]]
            L2 = T4
            Assigned[2] = 1
            Scalar_Kinds[2] = Buffer_Kinds[0]
            T8 = L2
            Error[0] = 0
            T7 = _Pyceler_Fast_8_sin(T8)
            if not _Pyceler_Fast_8_Finite(T7) or (Error[0] != 0 and not (Error[0] == _Pyceler_Fast_8_ERANGE and _Pyceler_Fast_8_fabs(T7) < 1.5)):
                Valid[0] = False
                return 0.0
            T12 = L2
            T13 = 1.0
            K10 = _Pyceler_Fast_8_Scalar_Promote(Scalar_Kinds[2], 0, False)
            if K10 == 255:
                Valid[0] = False
                return 0.0
            if (Scalar_Kinds[2] >= 10 and 0 == 4 and not _Pyceler_Fast_8_Scalar_Integer_Valid(T13, Scalar_Kinds[2])) or (0 >= 10 and Scalar_Kinds[2] == 4 and not _Pyceler_Fast_8_Scalar_Integer_Valid(T12, 0)):
                Valid[0] = False
                return 0.0
            if K10 == 1:
                T10 = <float>(<float>T12 + <float>T13)
            else:
                T10 = T12 + T13
            if not _Pyceler_Fast_8_Finite(T10):
                Valid[0] = False
                return 0.0
            if K10 >= 10 or K10 == 4:
                if not _Pyceler_Fast_8_Scalar_Integer_Valid(T10, K10):
                    Valid[0] = False
                    return 0.0
                if T10 == 0.0:
                    T10 = 0.0
            T14 = T10
            if T14 < 0.0:
                Valid[0] = False
                return 0.0
            Error[0] = 0
            T9 = _Pyceler_Fast_8_sqrt(T14)
            if not _Pyceler_Fast_8_Finite(T9) or (Error[0] != 0 and not (Error[0] == _Pyceler_Fast_8_ERANGE and _Pyceler_Fast_8_fabs(T9) < 1.5)):
                Valid[0] = False
                return 0.0
            T15 = T7
            T16 = T9
            K5 = _Pyceler_Fast_8_Scalar_Promote(0, 0, False)
            if K5 == 255:
                Valid[0] = False
                return 0.0
            if (0 >= 10 and 0 == 4 and not _Pyceler_Fast_8_Scalar_Integer_Valid(T16, 0)) or (0 >= 10 and 0 == 4 and not _Pyceler_Fast_8_Scalar_Integer_Valid(T15, 0)):
                Valid[0] = False
                return 0.0
            if K5 == 1:
                T5 = <float>(<float>T15 + <float>T16)
            else:
                T5 = T15 + T16
            if not _Pyceler_Fast_8_Finite(T5):
                Valid[0] = False
                return 0.0
            if K5 >= 10 or K5 == 4:
                if not _Pyceler_Fast_8_Scalar_Integer_Valid(T5, K5):
                    Valid[0] = False
                    return 0.0
                if T5 == 0.0:
                    T5 = 0.0
            T17 = T5
            if L0 < -Shapes[1][0] or L0 >= Shapes[1][0]:
                Valid[0] = False
                return 0.0
            if L1 < -Shapes[1][1] or L1 >= Shapes[1][1]:
                Valid[0] = False
                return 0.0
            T17 = _Pyceler_Fast_8_Array_Cast(T17, Output_Kinds[1], Valid)
            if not Valid[0]:
                return 0.0
            _Pyceler_Fast_8_Array_Store(Buffers[1], (<Py_ssize_t>(L0) + (Shapes[1][0] if L0 < 0.0 else 0)) * Strides[1][0] + (<Py_ssize_t>(L1) + (Shapes[1][1] if L1 < 0.0 else 0)) * Strides[1][1], T17, Output_Kinds[1], Buffer_Kinds[1] == 0)
            Changed[1][(<Py_ssize_t>(L0) + (Shapes[1][0] if L0 < 0.0 else 0)) * Strides[1][0] + (<Py_ssize_t>(L1) + (Shapes[1][1] if L1 < 0.0 else 0)) * Strides[1][1]] = 1
    Inputs[0] = L0
    Inputs[1] = L1
    Inputs[2] = L2
    return 1.0
cdef bint _Pyceler_Numeric_8_Worker(double** Buffers, unsigned char** Changed, Py_ssize_t** Shapes, Py_ssize_t** Strides, unsigned char* Buffer_Kinds, int* Output_Kinds, double* Inputs, unsigned char* Scalar_Kinds, double* Random_Values, Py_ssize_t Random_Limit, Py_ssize_t Random_Position, Py_ssize_t Begin, Py_ssize_t End, Py_ssize_t Step, const _Pyceler_Fast_8_Environment* Saved, int* Flags) noexcept nogil:
    cdef double Local_Inputs[3]
    cdef unsigned char Local_Kinds[3]
    cdef unsigned char Assigned[3]
    cdef bint Valid = True
    cdef Py_ssize_t Slot, Random_Consumed
    cdef _Pyceler_Fast_8_Environment Previous
    _Pyceler_Fast_8_Get_Environment(&Previous)
    _Pyceler_Fast_8_Set_Environment(Saved)
    _Pyceler_Numeric_8_Clear_Exceptions(_Pyceler_Fast_8_All_Exceptions)
    for Slot in range(3):
        Local_Inputs[Slot] = Inputs[Slot]
        Local_Kinds[Slot] = Scalar_Kinds[Slot]
    _Pyceler_Numeric_8_Compute(Buffers, Changed, Shapes, Strides, Buffer_Kinds, Output_Kinds, Local_Inputs, Local_Kinds, Random_Values, Random_Limit, Random_Position, &Random_Consumed, Begin, End, Step, Assigned, &Valid)
    Flags[0] = _Pyceler_Fast_8_Test_Exceptions(_Pyceler_Fast_8_All_Exceptions)
    _Pyceler_Fast_8_Set_Environment(&Previous)
    return Valid

def _Pyceler_Numeric_8_Blocks(Span, Recovery):
    import builtins as B
    if B.type(Span) is not B.range or not -1125899906842624 <= Span.start <= 1125899906842624 or not -1125899906842624 <= Span.stop <= 1125899906842624 or not -1125899906842624 <= Span.step <= 1125899906842624:
        yield Span
        return
    if B.len(Recovery) > 1:
        Recovery[1] = 2 * B.len(Span).bit_length()
    for Position in B.range(0, B.len(Span), 65536):
        Pending = [(Span[Position:Position + 65536], 0)]
        while Pending:
            Current, Depth = Pending.pop()
            Recovery[0] = 0
            yield Current
            Cut = Recovery[0]
            if 0 < Cut < B.len(Current):
                if Depth:
                    Cut = B.len(Current) // 2
                Pending.append((Current[Cut:], Depth + 1))
                Pending.append((Current[:Cut], Depth + 1))
# Run ndarray transactions on isolated storage; publish only validated work and preserve failure continuation.
cdef object _Pyceler_Numeric_8_Try(dict Namespace, object Span, object Whole, object Binding, object Length_Binding, object Policy, object Source_Code, dict Source_Globals, list Recovery=None):
    cdef bint Published = False
    cdef Py_ssize_t Failure = -1
    try:
        Result = _Pyceler_Numeric_8_Attempt(Namespace, Span, Whole, Binding, Length_Binding, Policy, Source_Code, Source_Globals, &Published, &Failure)
        if Result is None and Failure > 0 and Recovery is not None:  # Recover only a validated unpublished prefix; retries have a bounded budget.
            if len(Recovery) > 1:
                if Recovery[1] <= 0:
                    _Pyceler_Guard_Event('8', 'guard_1: if Recovery[1] <= 0')
                    return None
                Recovery[1] -= 1
            Recovery[0] = Failure
        return Result
    except MemoryError:
        if Published:
            raise
        _Pyceler_Guard_Event('8', 'guard_2: except MemoryError')
        return None

cdef object _Pyceler_Numeric_8_Attempt(dict Namespace, object Span, object Whole, object Binding, object Length_Binding, object Policy, object Source_Code, dict Source_Globals, bint* Published, Py_ssize_t* Failure):
    import builtins as B
    N = _Pyceler_Fast_8_System.modules.get('numpy')
    Core = _Pyceler_Fast_8_System.modules.get('numpy._core.multiarray') or _Pyceler_Fast_8_System.modules.get('numpy.core.multiarray')
    Types = _Pyceler_Fast_8_System.modules.get('numpy._core.numerictypes') or _Pyceler_Fast_8_System.modules.get('numpy.core.numerictypes')
    cdef double* Buffers[2]
    cdef double* Trial[2]
    cdef unsigned char* Changed[2]
    cdef unsigned char* Trial_Changed[2]
    cdef Py_ssize_t* Shapes[2]
    cdef Py_ssize_t* Strides[2]
    cdef Py_ssize_t Shape_Data[2 * 2], Stride_Data[2 * 2], Sizes[2]
    cdef unsigned char Buffer_Kinds[2], Scalar_Kinds[3], Final_Kinds[3]
    cdef int Output_Kinds[2]
    cdef double Inputs[3], Final_Inputs[3]
    cdef double[::1] Values
    cdef double[::1] Random_View
    cdef double* Random_Values = NULL
    cdef Py_ssize_t Random_Per_Outer = 0, Random_Total = 0, Random_Prefix = 0, Random_Final = 0
    cdef unsigned char[::1] Mask
    cdef unsigned char[::1] Raw_View
    cdef Py_ssize_t Slot, Axis, Position, Begin, End, Step, Last, Count, Part, Parts, Native_End, Native_Count
    cdef unsigned char Assigned[3], Prefix_Assigned[3]
    cdef bint Valid = True, Used_Parallel = False, Parallel_OK, Recoverable
    cdef bint Checks[256]
    cdef int Exceptions[256], Team[1], Workers, Flags = 0, Mode
    cdef _Pyceler_Fast_8_Environment Saved
    cdef _Pyceler_Fast_8_Exception_State Prepared
    global _Pyceler_Fast_8_Native_Elements, _Pyceler_Fast_8_Parallel_Elements, _Pyceler_Fast_8_Last_Team
    _Pyceler_Dispatch_Event('Execution', 'python_fallback', 0)
    if Binding is not B.range or Length_Binding is not B.len or B.type(Span) is not B.range:  # Runtime rebinding invalidates a static builtin assumption.
        _Pyceler_Guard_Event('8', 'guard_3: native attempt declined')
        return None
    if B.type(Length_Binding) is not _Pyceler_Fast_8_Types.BuiltinFunctionType or Length_Binding.__self__ is not B or Length_Binding.__name__ != 'len':
        _Pyceler_Guard_Event('8', "guard_4: if B.type(Length_Binding) is not _Pyceler_Fast_8_Types.BuiltinFunctionType or Length_Binding.__self__ is not B or Length_Binding.__name__ != 'len'")
        return None
    if not -1125899906842624 <= Span.start <= 1125899906842624 or not -1125899906842624 <= Span.stop <= 1125899906842624 or not -1125899906842624 <= Span.step <= 1125899906842624 or B.len(Span) < 2:
        _Pyceler_Guard_Event('8', 'guard_5: if not -1125899906842624 <= Span.start <= 1125899906842624 or not -1125899906842624 <= Span.stop <= 1125899906842624 or not -1125899906842624 <= Span.step <= 1125899906842624 or B.len(Span) < 2')
        return None
    Mode = 2
    if not _Pyceler_Fast_8_Exclusive() or not _Pyceler_Fast_8_Bindings(Namespace):
        _Pyceler_Guard_Event('8', 'guard_6: if not _Pyceler_Fast_8_Exclusive() or not _Pyceler_Fast_8_Bindings(Namespace)')
        return None
    if N is None or Core is None or Types is None:
        _Pyceler_Guard_Event('8', 'guard_7: if N is None or Core is None or Types is None')
        return None
    for Name in ('ndarray', 'zeros', 'empty', 'copyto', 'shares_memory'):
        if getattr(N, Name, None) is not getattr(Core, Name, None):
            _Pyceler_Guard_Event('8', 'guard_8: if getattr(N, Name, None) is not getattr(Core, Name, None)')
            return None
    for Name in ('float32', 'float64', 'bool_', 'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64'):
        if getattr(N, Name, None) is not getattr(Types, Name, None):
            _Pyceler_Guard_Event('8', 'guard_9: if getattr(N, Name, None) is not getattr(Types, Name, None)')
            return None
    if 'values' not in Namespace:
        _Pyceler_Guard_Event('8', "guard_10: if 'values' not in Namespace")
        return None
    if 'output' not in Namespace:
        _Pyceler_Guard_Event('8', "guard_11: if 'output' not in Namespace")
        return None
    if 'math' not in Namespace:
        _Pyceler_Guard_Event('8', "guard_12: if 'math' not in Namespace")
        return None
    Previous = Namespace.get('row')
    if B.type(Previous) not in (int, float, bool, N.float32, N.float64, N.int64, N.int32) and Previous is not None:
        _Pyceler_Guard_Event('8', 'guard_13: if B.type(Previous) not in (int, float, bool, N.float32, N.float64, N.int64, N.int32) and Previous is not None')
        return None
    Previous = Namespace.get('column')
    if B.type(Previous) not in (int, float, bool, N.float32, N.float64, N.int64, N.int32) and Previous is not None:
        _Pyceler_Guard_Event('8', 'guard_14: if B.type(Previous) not in (int, float, bool, N.float32, N.float64, N.int64, N.int32) and Previous is not None')
        return None
    Previous = Namespace.get('value')
    if B.type(Previous) not in (int, float, bool, N.float32, N.float64, N.int64, N.int32) and Previous is not None:
        _Pyceler_Guard_Event('8', 'guard_15: if B.type(Previous) not in (int, float, bool, N.float32, N.float64, N.int64, N.int32) and Previous is not None')
        return None
    Inputs[0] = 0.0
    Scalar_Kinds[0] = 0
    Inputs[1] = 0.0
    Scalar_Kinds[1] = 0
    Inputs[2] = 0.0
    Scalar_Kinds[2] = 0
    Begin, End, Step, Last, Count = Span.start, Span.stop, Span.step, Span[-1], B.len(Span)
    Native_End = End if True else Last
    Native_Count = Count if True else Count - 1
    Original_Names = {Name: Namespace[Name] for Name in ('values', 'output', 'row', 'column', 'value') if Name in Namespace}
    Absent_Names = [Name for Name in ('values', 'output', 'row', 'column', 'value') if Name not in Namespace]
    Objects = [Namespace[Name] for Name in ('values', 'output')]
    if False and Count < 128:
        Total_Size = 0
        Integer_Storage = False
        for Array in Objects:
            if B.type(Array) is not N.ndarray:
                _Pyceler_Guard_Event('8', 'guard_16: if B.type(Array) is not N.ndarray')
                return None
            Total_Size += Array.size
            Integer_Storage = Integer_Storage or Array.dtype.kind in ('i', 'u')
        if Integer_Storage and Total_Size > Count * 128:
            _Pyceler_Guard_Event('8', 'guard_17: if Integer_Storage and Total_Size > Count * 128')
            return None
    Snapshots, Working, Trials, Masks, Trial_Masks = [], [], [], [], []  # Separate original storage, speculative values and publication masks.
    Metadata = []
    for Slot in range(2):
        Array = Objects[Slot]
        if B.type(Array) is not N.ndarray:
            _Pyceler_Guard_Event('8', 'guard_18: if B.type(Array) is not N.ndarray')
            return None
        if (False, False)[Slot]:
            if Array.ndim < (2, 2)[Slot]:
                _Pyceler_Guard_Event('8', 'guard_19: if Array.ndim < (2, 2)[Slot]')
                return None
            Shapes[Slot], Strides[Slot] = &Shape_Data[Slot * 2], &Stride_Data[Slot * 2]
            for Axis in range((2, 2)[Slot]):
                Shapes[Slot][Axis], Strides[Slot][Axis] = Array.shape[Axis], 0
            Sizes[Slot], Buffer_Kinds[Slot], Output_Kinds[Slot] = 0, 0, 0
            Buffers[Slot], Trial[Slot], Changed[Slot], Trial_Changed[Slot] = NULL, NULL, NULL, NULL
            Metadata.append((Array.shape, Array.strides, Array.dtype, Array.flags.writeable))
            for Collection in (Snapshots, Working, Trials, Masks, Trial_Masks):
                Collection.append(None)
            continue
        if Array.ndim != (2, 2)[Slot] or Array.dtype.metadata is not None or not Array.dtype.isnative or not Array.flags.aligned:
            _Pyceler_Guard_Event('8', 'guard_20: if Array.ndim != (2, 2)[Slot] or Array.dtype.metadata is not None or not Array.dtype.isnative or not Array.flags.aligned')
            return None
        Kind = Array.dtype.kind
        Width = Array.dtype.itemsize
        if Kind not in ('f', 'i', 'u', 'b') or Width not in (1, 2, 4, 8) or Kind == 'f' and Width not in (4, 8):
            _Pyceler_Guard_Event('8', "guard_21: if Kind not in ('f', 'i', 'u', 'b') or Width not in (1, 2, 4, 8) or Kind == 'f' and Width not in (4, 8)")
            return None
        if (False, True)[Slot]:
            if not Array.flags.writeable:
                _Pyceler_Guard_Event('8', 'guard_22: if not Array.flags.writeable')
                return None
            Extent = Array.itemsize
            for Stride, Dimension in sorted([(abs(Stride), Dimension) for Stride, Dimension in zip(Array.strides, Array.shape) if Dimension > 1]):
                if Stride < Extent:
                    _Pyceler_Guard_Event('8', 'guard_23: if Stride < Extent')
                    return None
                Extent += Stride * (Dimension - 1)
        if Array.size == 0:
            _Pyceler_Guard_Event('8', 'guard_24: if Array.size == 0')
            return None
        for Previous_Slot in range(Slot):
            if not (False, False)[Previous_Slot] and ((False, True)[Slot] or (False, True)[Previous_Slot]) and N.shares_memory(Array, Objects[Previous_Slot]):
                _Pyceler_Guard_Event('8', 'guard_25: if not (False, False)[Previous_Slot] and ((False, True)[Slot] or (False, True)[Previous_Slot]) and N.shares_memory(Array, Objects[Previous_Slot])')
                return None
        Sizes[Slot] = Array.size
        Shapes[Slot], Strides[Slot] = &Shape_Data[Slot * 2], &Stride_Data[Slot * 2]
        Position = 1
        for Axis in range(Array.ndim - 1, -1, -1):
            Shapes[Slot][Axis] = Array.shape[Axis]
            Strides[Slot][Axis] = Position
            Position *= Shapes[Slot][Axis]
        Output_Kinds[Slot] = (1 if Width == 4 else 2) if Kind == 'f' else 3 if Kind == 'b' else (10 if Kind == 'i' else 20) + Width
        Buffer_Kinds[Slot] = Output_Kinds[Slot] if (True, False)[Slot] else 0
        Metadata.append((Array.shape, Array.strides, Array.dtype, Array.flags.writeable))
        Snapshot = Array.copy(order='C')  # User arrays remain unchanged while speculative arithmetic and bounds are checked.
        Snapshots.append(Snapshot)
        if Buffer_Kinds[Slot] >= 10:
            Value = N.empty(Array.size, dtype=N.float64)
            Values = Value
            Raw_View = Snapshot.view(N.uint8).reshape(-1)
            if not _Pyceler_Fast_8_Integer_Copy(<void*>&Raw_View[0], &Values[0], Sizes[Slot], Buffer_Kinds[Slot]):
                _Pyceler_Guard_Event('8', 'guard_26: if not _Pyceler_Fast_8_Integer_Copy(<void*>&Raw_View[0], &Values[0], Sizes[Slot], Buffer_Kinds[Slot])')
                return None
        else:
            Value = Snapshot.astype(N.float64, copy=True).reshape(-1) if (True, False)[Slot] else N.zeros(Array.size, dtype=Array.dtype)
        if (True, False)[Slot] and Buffer_Kinds[Slot] < 10:  # Non-finite data stays on the original path unless its full contract is supported.
            Values = Value
            for Position in range(Sizes[Slot]):
                if not _Pyceler_Fast_8_Finite(Values[Position]):
                    _Pyceler_Guard_Event('8', 'guard_27: if not _Pyceler_Fast_8_Finite(Values[Position])')
                    return None
        Working.append(Value)
        Raw_View = Value.view(N.uint8).reshape(-1)
        Buffers[Slot] = <double*>&Raw_View[0]
        Value = N.zeros(Array.size, dtype=N.uint8)
        Masks.append(Value)
        Mask = Value
        Changed[Slot] = &Mask[0]
        Value = Working[Slot].copy() if (False, True)[Slot] and not True else Working[Slot]
        Trials.append(Value)
        Raw_View = Value.view(N.uint8).reshape(-1)
        Trial[Slot] = <double*>&Raw_View[0]
        Value = Masks[Slot] if True else N.zeros(Array.size, dtype=N.uint8)
        Trial_Masks.append(Value)
        Mask = Value
        Trial_Changed[Slot] = &Mask[0]
    Work_Size = sum([Sizes[Slot] // Shapes[Slot][0] for Slot in range(2) if not (False, False)[Slot]]) * Count
    if 0:
        import random as Random_Module
        import _random as Random_Core
        Random_Binding = Namespace['']
        if Random_Binding is not Random_Module:
            _Pyceler_Guard_Event('8', 'guard_28: if Random_Binding is not Random_Module')
            return None
        Random_Callback = Random_Module.random
        if B.type(Random_Callback) is not _Pyceler_Fast_8_Types.BuiltinFunctionType or Random_Callback.__name__ != 'random' or Random_Callback.__self__ is not Random_Module._inst or B.type(Random_Module._inst) is not Random_Module.Random or Random_Module.Random.random is not Random_Core.Random.random:
            _Pyceler_Guard_Event('8', "guard_29: if B.type(Random_Callback) is not _Pyceler_Fast_8_Types.BuiltinFunctionType or Random_Callback.__name__ != 'random' or Random_Callback.__self__ is not Random_Module._inst or B.type(Random_Module._inst) is not Random_Module.Random or Random_Module.Random.random is not Random_Core.Random.random")
            return None
        Random_Instance = Random_Callback.__self__
        Random_State = Random_Core.Random.getstate(Random_Instance)
        Random_Copy = Random_Core.Random()
        Random_Core.Random.setstate(Random_Copy, Random_State)
        Random_Per_Outer = 0
        try:
            for Expression in ():
                Random_Per_Outer *= B.len(Expression(dict(Namespace, range=B.range, len=B.len)))
                if Random_Per_Outer == 0:
                    _Pyceler_Guard_Event('8', 'guard_30: if Random_Per_Outer == 0')
                    return None
            Random_Total, Random_Prefix = Random_Per_Outer * Count, Random_Per_Outer * (Count - 1)
        except (ArithmeticError, ValueError, TypeError, IndexError):
            _Pyceler_Guard_Event('8', 'guard_31: except (ArithmeticError, ValueError, TypeError, IndexError)')
            return None
        Random_Array = N.empty(Random_Total, dtype=N.float64)
        Random_View = Random_Array
        Random_Values = &Random_View[0]
        Random_Draw = Random_Copy.random
        for Position in range(Random_Total):
            if Position == Random_Prefix:
                Random_Prefix_State = Random_Core.Random.getstate(Random_Copy)
            Random_View[Position] = Random_Draw()
    if _Pyceler_Fast_8_Get_Environment(&Saved) != 0:
        _Pyceler_Guard_Event('8', 'guard_32: if _Pyceler_Fast_8_Get_Environment(&Saved) != 0')
        return None
    try:
        if True and Mode != 1 and B.len(Span) >= 3 and Work_Size >= 4096 and not _Pyceler_Fast_8_In_Parallel():
            Parallel_OK = True
            if min(B.int(Begin) * (1), B.int(Last) * (1)) + (0) < -Shapes[1][0] or max(B.int(Begin) * (1), B.int(Last) * (1)) + (0) >= Shapes[1][0] or (max(B.int(Begin) * (1), B.int(Last) * (1)) + (0)) - (min(B.int(Begin) * (1), B.int(Last) * (1)) + (0)) >= Shapes[1][0]:
                Parallel_OK = False
            if Parallel_OK:
                Workers = min(8, _Pyceler_Fast_8_Max_Threads()) if Mode < 100 else Mode - 100
                Parts = min(Workers, Native_Count, 256)
                Team[0] = 1
                for Part in _Pyceler_Fast_8_Prange(Parts, nogil=True, schedule='static', num_threads=Workers):
                    if Part == 0:
                        Team[0] = _Pyceler_Fast_8_Team_Size()
                    Checks[Part] = _Pyceler_Numeric_8_Worker(Buffers, Changed, Shapes, Strides, Buffer_Kinds, Output_Kinds, Inputs, Scalar_Kinds, Random_Values, Random_Total, Random_Per_Outer * ((Native_Count) * Part // Parts), Begin + Step * ((Native_Count) * Part // Parts), Begin + Step * ((Native_Count) * (Part + 1) // Parts), Step, &Saved, &Exceptions[Part])
                Used_Parallel = True
                for Part in range(Parts):
                    Valid = Valid and Checks[Part]
                    Flags |= Exceptions[Part]
        if not Used_Parallel:
            with nogil:
                _Pyceler_Numeric_8_Clear_Exceptions(_Pyceler_Fast_8_All_Exceptions)
                _Pyceler_Numeric_8_Compute(Buffers, Changed, Shapes, Strides, Buffer_Kinds, Output_Kinds, Inputs, Scalar_Kinds, Random_Values, Random_Total, 0, &Random_Prefix, Begin, Native_End, Step, Prefix_Assigned, &Valid)
            Flags = _Pyceler_Fast_8_Test_Exceptions(_Pyceler_Fast_8_All_Exceptions)
        if not Valid:
            _Pyceler_Guard_Event('8', 'guard_33: if not Valid')
            return None
        if not True:
            for Slot in range(2):
                if (False, True)[Slot]:
                    Trials[Slot][:] = Working[Slot]
            for Slot in range(3):
                Final_Inputs[Slot] = Inputs[Slot]
                Final_Kinds[Slot] = Scalar_Kinds[Slot]
            with nogil:
                _Pyceler_Numeric_8_Clear_Exceptions(_Pyceler_Fast_8_All_Exceptions)
                _Pyceler_Numeric_8_Compute(Trial, Trial_Changed, Shapes, Strides, Buffer_Kinds, Output_Kinds, Final_Inputs, Final_Kinds, Random_Values, Random_Total, Random_Prefix, &Random_Final, Last, End, Step, Assigned, &Valid)
            Flags |= _Pyceler_Fast_8_Test_Exceptions(_Pyceler_Fast_8_All_Exceptions)
    finally:
        _Pyceler_Fast_8_Set_Environment(&Saved)
    if not Valid or Flags & (_Pyceler_Numeric_8_Invalid | _Pyceler_Numeric_8_Divide | _Pyceler_Numeric_8_Overflow | _Pyceler_Numeric_8_Underflow):
        _Pyceler_Guard_Event('8', 'guard_34: if not Valid or Flags & (_Pyceler_Numeric_8_Invalid | _Pyceler_Numeric_8_Divide | _Pyceler_Numeric_8_Overflow | _Pyceler_Numeric_8_Underflow)')
        return None
    for Slot in ():
        Valid = Valid and Assigned[Slot] != 0
    if not Valid:
        Recoverable = True
        if not Used_Parallel:
            for Slot in ():
                if not Assigned[Slot] and not Prefix_Assigned[Slot]:
                    Recoverable = False
        if True and Recoverable:
            Failure[0] = Count - 1
        _Pyceler_Guard_Event('8', 'guard_35: if not Valid')
        return None
    if False:
        Random_Core.Random.setstate(Random_Copy, Random_State)
        for Position in range(Random_Prefix):
            Random_Draw()
        Random_Prefix_State = Random_Core.Random.getstate(Random_Copy)
    Prepared_Outputs = []
    for Slot in range(2):
        if (False, True)[Slot]:
            Prepared_Outputs.append(Working[Slot].reshape(Objects[Slot].shape).astype(Objects[Slot].dtype, copy=False))
        else:
            Prepared_Outputs.append(None)
    Carry_Updates = {}
    pass
    if not True:
        Pool = _Pyceler_Module_Constants_8_Pool(Source_Code)
        Body = _Pyceler_Module_Constants_8_Code(_Pyceler_Numeric_8_Body, Pool)
    if not _Pyceler_Fast_8_Exclusive() or not _Pyceler_Fast_8_Bindings(Namespace):
        _Pyceler_Guard_Event('8', 'guard_36: if not _Pyceler_Fast_8_Exclusive() or not _Pyceler_Fast_8_Bindings(Namespace)')
        return None
    pass
    for Name, Global_Name in (('math', 'math'),):
        if Namespace.get(Name) is not Source_Globals.get(Global_Name):
            _Pyceler_Guard_Event('8', 'guard_37: if Namespace.get(Name) is not Source_Globals.get(Global_Name)')
            return None
    for Name in Absent_Names:
        if Name in Namespace:
            _Pyceler_Guard_Event('8', 'guard_38: if Name in Namespace')
            return None
    for Name, Value in Original_Names.items():
        if Namespace.get(Name) is not Value:
            _Pyceler_Guard_Event('8', 'guard_39: if Namespace.get(Name) is not Value')
            return None
    for Slot in range(2):
        Array = Objects[Slot]
        if (Array.shape, Array.strides, Array.dtype, Array.flags.writeable) != Metadata[Slot]:
            _Pyceler_Guard_Event('8', 'guard_40: if (Array.shape, Array.strides, Array.dtype, Array.flags.writeable) != Metadata[Slot]')
            return None
        if not (False, False)[Slot] and Array.tobytes() != Snapshots[Slot].tobytes():
            _Pyceler_Guard_Event('8', 'guard_41: if not (False, False)[Slot] and Array.tobytes() != Snapshots[Slot].tobytes()')
            return None
    if 0:
        if Namespace.get('') is not Random_Module or Random_Module.random is not Random_Callback or Random_Core.Random.getstate(Random_Instance) != Random_State:
            _Pyceler_Guard_Event('8', "guard_42: if Namespace.get('') is not Random_Module or Random_Module.random is not Random_Callback or Random_Core.Random.getstate(Random_Instance) != Random_State")
            return None
    if Flags and _Pyceler_Fast_8_Prepare_Exceptions(Flags, &Prepared) != 0:
        _Pyceler_Guard_Event('8', 'guard_43: if Flags and _Pyceler_Fast_8_Prepare_Exceptions(Flags, &Prepared) != 0')
        return None
    Published[0] = True
    for Slot in range(2):
        if (False, True)[Slot]:
            N.copyto(Objects[Slot], Prepared_Outputs[Slot], where=Masks[Slot].reshape(Objects[Slot].shape).view(N.bool_))
    if 0:
        Random_Core.Random.setstate(Random_Instance, Random_Prefix_State)
    Namespace.update(Carry_Updates)
    if Flags:
        _Pyceler_Fast_8_Set_Exceptions(&Prepared, Flags)
    if not True:
        Namespace['row'] = Last
        Body(Namespace)
    _Pyceler_Fast_8_Native_Elements += Native_Count
    if Used_Parallel:
        _Pyceler_Fast_8_Parallel_Elements += Native_Count
        _Pyceler_Fast_8_Last_Team = Team[0]
        _Pyceler_Dispatch_Event('Execution', 'native_parallel', Team[0])
    else:
        _Pyceler_Fast_8_Last_Team = 1
        _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)
    return tuple([Namespace[Name] for Name in ()])
_Pyceler_Direct_Application_Begin = None
import math
import time
import numpy as np

def transform(values, output):
    if _Pyceler_Direct_Unreachable():
        row = column = value = None
    try:

        def _Pyceler_Module_Constants_8():
            try:
                pass
            except _Pyceler_Python_Builtins.UnboundLocalError as _Pyceler_Unbound:
                _Pyceler_Direct_Unbound(_Pyceler_Unbound)
                raise
        _Pyceler_Numeric_Rows_8 = _Pyceler_Direct_Value(_Pyceler_Direct_Globals(), 'range')(_Pyceler_Direct_Value(_Pyceler_Direct_Globals(), 'len')(values))
        _Pyceler_Numeric_Recovery_8 = [0, 0]
        for _Pyceler_Numeric_Block_8 in _Pyceler_Numeric_8_Blocks(_Pyceler_Numeric_Rows_8, _Pyceler_Numeric_Recovery_8):
            _Pyceler_Direct_Checkpoint()
            _Pyceler_Numeric_Result_8 = _Pyceler_Numeric_8_Try({'values': values, 'output': output, 'math': _Pyceler_Module_Constants_8.__globals__.get('math')}, _Pyceler_Numeric_Block_8, _Pyceler_Numeric_Rows_8, _Pyceler_Direct_Value(_Pyceler_Direct_Globals(), 'range'), _Pyceler_Direct_Value(_Pyceler_Direct_Globals(), 'len'), None, _Pyceler_Module_Constants_8.__code__, _Pyceler_Module_Constants_8.__globals__, _Pyceler_Numeric_Recovery_8)
            if _Pyceler_Numeric_Result_8 is None:
                if 0 < _Pyceler_Numeric_Recovery_8[0] < _Pyceler_Python_Builtins.len(_Pyceler_Numeric_Block_8):
                    continue
                for row in _Pyceler_Numeric_Block_8:
                    _Pyceler_Direct_Checkpoint()
                    for column in _Pyceler_Direct_Value(_Pyceler_Direct_Globals(), 'range')(_Pyceler_Direct_Value(_Pyceler_Direct_Globals(), 'len')(values[0])):
                        _Pyceler_Direct_Checkpoint()
                        value = values[row, column]
                        output[row, column] = math.sin(value) + math.sqrt(value + 1.0)
            else:
                pass
        return output
    except _Pyceler_Python_Builtins.UnboundLocalError as _Pyceler_Unbound:
        _Pyceler_Direct_Unbound(_Pyceler_Unbound)
        raise
values = np.linspace(0.0, 10.0, 256 * 128).reshape(256, 128)
output = np.zeros_like(values)
started = time.perf_counter()
transform(values, output)
_Pyceler_Direct_Value(_Pyceler_Direct_Globals(), 'print')('Checksum:', _Pyceler_Direct_Value(_Pyceler_Direct_Globals(), 'float')(output.sum()))
_Pyceler_Direct_Value(_Pyceler_Direct_Globals(), 'print')('Runtime:', time.perf_counter() - started)
