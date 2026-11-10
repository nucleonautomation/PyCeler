import _thread
import importlib.util
import signal
import sys
import threading
import time

Spec = importlib.util.spec_from_file_location(sys.argv[2], sys.argv[1])
Module = importlib.util.module_from_spec(Spec)
sys.modules[sys.argv[2]] = Module
Observed = []
Clock = time.perf_counter
Timer = None

def _Clock():
    global Timer
    time.perf_counter = Clock
    Timer = threading.Timer(0.01, _thread.interrupt_main)
    Timer.start()
    return Clock()

def _Handle(Signum, Frame):
    Observed.append((Module.Index, Module.Total, Module.Done))
    if sys.argv[3] == "cancel":
        raise KeyboardInterrupt("audit cancellation")
    Module.Total = -(2**200)

Previous = signal.signal(signal.SIGINT, _Handle)
time.perf_counter = _Clock
Cancelled = False
try:
    Spec.loader.exec_module(Module)
except KeyboardInterrupt:
    Cancelled = True
finally:
    time.perf_counter = Clock
    if Timer is not None:
        Timer.join()
    signal.signal(signal.SIGINT, Previous)
assert len(Observed) == 1 and Observed[0][0] >= 0 and Observed[0][1] > 0 and Observed[0][2] is False, Observed
if sys.argv[3] == "cancel":
    assert Cancelled and Module.Total > 0 and Module.Index > 0 and Module.Done is False, Module.__dict__
else:
    assert not Cancelled and Module.Total < 0 and Module.Done is True, Module.__dict__
print(sys.argv[2], sys.argv[3], Observed, "preserved")
