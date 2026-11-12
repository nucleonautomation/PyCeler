import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

def _Ready(Folder, Role, Token):
    Temporary = Folder / (Role + ".pending")
    Temporary.write_text(json.dumps(dict(Role=Role, Pid=os.getpid(), Token=Token)), encoding="utf-8")
    Temporary.replace(Folder / (Role + ".json"))
    print("ready " + Role, flush=True)

def _Wait(File, Seconds=15):
    Deadline = time.monotonic() + Seconds
    while not File.is_file():
        if time.monotonic() >= Deadline:
            raise RuntimeError("Readiness deadline exceeded: " + str(File))
        time.sleep(0.01)

def _Run():
    Folder, Role, Mode, Token = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
    if Mode == "ignore" and Role != "sentinel" and os.name != "nt":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if Role == "sentinel":
        _Ready(Folder, Role, Token)
        _Wait(Folder / "sentinel.stop", 120)
        return
    Child = None
    if Role in ("worker", "child"):
        Next = "child" if Role == "worker" else "grandchild"
        Child = subprocess.Popen([sys.executable, "-I", "-B", __file__, str(Folder), Next, Mode, Token])
        _Wait(Folder / (Next + ".json"))
    _Ready(Folder, Role, Token)
    if Role == "worker" and Mode == "linger":
        _Wait(Folder / "observed.ready")
        return
    End = time.monotonic() + 60
    while not (Folder / "finish").is_file() and time.monotonic() < End:
        time.sleep(0.02)
    if Child is not None:
        Child.wait(timeout=10)

if __name__ == "__main__":
    _Run()
