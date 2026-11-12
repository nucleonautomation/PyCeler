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
Requested = []
Clock = time.perf_counter
Watcher = None
Stopped = threading.Event()

def _Interrupt_During_Progress():
    Deadline = Clock() + 10.0
    while not Stopped.wait(0.001) and Clock() < Deadline:
        if Module.Done:
            return
        if Module.Index >= 0 and Module.Total > 0:
            Requested.append((Module.Index, Module.Total, Module.Done))
            _thread.interrupt_main()
            return

def _Clock():
    global Watcher
    time.perf_counter = Clock
    Watcher = threading.Thread(target=_Interrupt_During_Progress)
    Watcher.start()
    time.sleep(0.03)
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
    Stopped.set()
    if Watcher is not None:
        Watcher.join()
    signal.signal(signal.SIGINT, Previous)
assert len(Requested) == 1 and Requested[0][0] >= 0 and Requested[0][1] > 0 and Requested[0][2] is False, Requested
assert len(Observed) == 1 and Observed[0][0] >= 0 and Observed[0][1] > 0 and Observed[0][2] is False, Observed
if sys.argv[3] == "cancel":
    assert Cancelled and Module.Total > 0 and Module.Index > 0 and Module.Done is False, Module.__dict__
else:
    assert not Cancelled and Module.Total < 0 and Module.Done is True, Module.__dict__
print(sys.argv[2], sys.argv[3], Observed, "preserved")
