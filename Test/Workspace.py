import tempfile
import os
import time
from types import SimpleNamespace
from PyCeler.Native_Build import _Cleanup_Workspace
# Test support/workload for workspace.
class Temporary_Directory(tempfile.TemporaryDirectory):

    def cleanup(self):
        Deadline = time.monotonic() + 30.0
        while True:
            try:
                _Cleanup_Workspace(SimpleNamespace(cleanup=super().cleanup))
                return
            except PermissionError:
                if os.name != 'nt' or time.monotonic() >= Deadline:
                    raise
                time.sleep(min(0.5, max(0.0, Deadline - time.monotonic())))
