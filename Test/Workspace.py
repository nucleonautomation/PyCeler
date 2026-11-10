import tempfile
from types import SimpleNamespace
from PyCeler.Native_Build import _Cleanup_Workspace

class Temporary_Directory(tempfile.TemporaryDirectory):

    def cleanup(self):
        _Cleanup_Workspace(SimpleNamespace(cleanup=super().cleanup))
