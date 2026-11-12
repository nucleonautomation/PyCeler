import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PyCeler import Native_Build as B
from Test.Workspace import Temporary_Directory

class Build_Deadline(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def setUp(self):
        Folder = Temporary_Directory(dir=self._Root / "Test_Run")
        self.addCleanup(Folder.cleanup)
        self._Folder = Path(Folder.name)
        self._Stage = self._Folder / "Stage"
        self._Output = self._Folder / "Output"
        self._Stage.mkdir()
        self._Output.mkdir()
        self._Original = self._Output / "Old.pyd"
        self._Original.write_bytes(b"previous published product")

    def _Build(self, Cache=False):
        return B._Build(self._Stage, [Path("Source.pyx")], self._Output, "abi", "3.11", False, False, Cache=Cache)

    def test_Configuration_Is_Opt_In_And_Finite(self):
        for Value in (None, "", "0", "0.0", "-0"):
            with self.subTest(Value=Value), patch.dict(os.environ, clear=True):
                if Value is not None:
                    os.environ["PYCELER_BUILD_TIMEOUT_SECONDS"] = Value
                self.assertIsNone(B._Build_Deadline())
        for Value, Expected in (("0.01", 0.01), ("900", 900), (" 3.5 ", 3.5), ("1e100", 1e100)):
            with patch.dict(os.environ, PYCELER_BUILD_TIMEOUT_SECONDS=Value):
                self.assertEqual(B._Build_Deadline(), Expected)
        for Value in ("-1", "NaN", "Infinity", "-inf", "invalid", "1e999"):
            with patch.dict(os.environ, PYCELER_BUILD_TIMEOUT_SECONDS=Value), self.assertRaises(ValueError):
                B._Build_Deadline()

    def test_Unlimited_Path_Keeps_Existing_Subprocess_Contract(self):
        with patch.dict(os.environ, PYCELER_BUILD_TIMEOUT_SECONDS="0"), patch.object(B.subprocess, "run", return_value=SimpleNamespace(returncode=7)) as Run, patch.object(B, "_Run_Bounded_Build") as Bounded:
            with self.assertRaisesRegex(RuntimeError, "Native build failed"):
                self._Build()
        Bounded.assert_not_called()
        self.assertEqual(Run.call_count, 1)
        self.assertNotIn("timeout", Run.call_args.kwargs)
        self.assertEqual(self._Original.read_bytes(), b"previous published product")

    def test_Timeout_Preserves_Log_Outputs_And_Excludes_Cache_Publication(self):
        def _Prepare(Stage, Request, Cache):
            return dict(Status="enabled")
        def _Expire(Command, Directory, Stream, Seconds):
            Stream.write("owned compiler reached controlled deadline\n")
            Stream.flush()
            raise B._Build_Timeout(Seconds, Seconds + 0.01, Stream.name, "complete")
        with patch.dict(os.environ, PYCELER_BUILD_TIMEOUT_SECONDS="0.5"), patch("PyCeler.Binary_Cache._Prepare_Binary_Cache", side_effect=_Prepare), patch("PyCeler.Binary_Cache._Finish_Binary_Cache") as Finish, patch.object(B, "_Publish") as Publish, patch.object(B, "_Run_Bounded_Build", side_effect=_Expire):
            with self.assertRaises(B._Build_Timeout) as Caught:
                self._Build(Cache=self._Folder / "Cache")
        Finish.assert_not_called()
        Publish.assert_not_called()
        self.assertEqual(Caught.exception.Cleanup, "complete")
        self.assertEqual(Caught.exception.Seconds, 0.5)
        self.assertTrue(Caught.exception.Log.is_file())
        self.assertIn("controlled deadline", Caught.exception.Log.read_text(encoding="utf-8"))
        self.assertEqual(self._Original.read_bytes(), b"previous published product")
        self.assertEqual(list(self._Output.iterdir()), [self._Original])

    def test_Cache_Hit_Starts_No_Worker_With_A_Deadline(self):
        def _Prepare(Stage, Request, Cache):
            Request.update(Paths=[], Cached_Products=["Cached.pyd"])
            (Stage / "Products").mkdir()
            (Stage / "Products/Cached.pyd").write_bytes(b"cache mock")
            return dict(Status="enabled")
        with patch.dict(os.environ, PYCELER_BUILD_TIMEOUT_SECONDS="0.000001"), patch("PyCeler.Binary_Cache._Prepare_Binary_Cache", side_effect=_Prepare), patch("PyCeler.Binary_Cache._Finish_Binary_Cache") as Finish, patch.object(B, "_Run_Bounded_Build") as Bounded, patch.object(B.subprocess, "run") as Run:
            Result = self._Build(Cache=self._Folder / "Cache")
        self.assertEqual(Result, (self._Output / "Cached.pyd",))
        self.assertEqual(Finish.call_count, 1)
        Bounded.assert_not_called()
        Run.assert_not_called()
        self.assertIn("compatible binary cache", (self._Folder / "Logs/Stage.log").read_text(encoding="utf-8"))

    def test_Deadline_Record_Is_Typed_And_Cleanup_Failure_Stops_Success(self):
        Name = "_Windows_Bounded_Build" if os.name == "nt" else "_Posix_Bounded_Build"
        Log = self._Folder / "Bounded.log"
        for Timed, Cleanup, Error in ((True, "complete", B._Build_Timeout), (False, "owned child remains", RuntimeError)):
            with self.subTest(Timed=Timed), Log.open("w", encoding="utf-8") as Stream, patch.object(B, Name, return_value=dict(Return_Code=0, Timed_Out=Timed, Cleanup=Cleanup)):
                with self.assertRaises(Error):
                    B._Run_Bounded_Build([sys.executable], self._Folder, Stream, 0.1)
            Records = [json.loads(Line.partition(": ")[2]) for Line in Log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(Records[-1]["Cleanup"], Cleanup)
            self.assertEqual(Records[-1]["Timed_Out"], Timed)

    @unittest.skipIf(os.name == "nt", "POSIX process-group ownership contract")
    def test_Posix_Never_Signals_A_Group_After_Losing_Child_Ownership(self):
        Process = SimpleNamespace(pid=12345)
        with patch.object(B.os, "waitid", side_effect=ChildProcessError), patch.object(B.os, "killpg") as Signal:
            self.assertIn("ownership was lost", B._Posix_Group_Cleanup(Process, True))
        Signal.assert_not_called()

    @unittest.skipIf(os.name == "nt", "POSIX process-group ownership contract")
    def test_Posix_Only_Uses_Read_Only_Group_Checks_After_Reaping(self):
        import signal
        Calls = []
        Process = SimpleNamespace(pid=12345, wait=lambda **Keywords: Calls.append("reaped"))
        def _Signal(Pid, Value):
            Calls.append((Pid, Value))
            if Value == 0:
                raise ProcessLookupError
        with patch.object(B.os, "waitid", return_value=object()), patch.object(B.os, "killpg", side_effect=_Signal):
            self.assertEqual(B._Posix_Group_Cleanup(Process, False), "complete")
        self.assertEqual(Calls, [(12345, signal.SIGKILL), "reaped", (12345, 0)])

    @unittest.skipUnless(os.name == "nt", "Windows creation-time ownership contract")
    def test_Windows_Job_Is_Assigned_At_Creation_And_Never_Inherited(self):
        C, W, Original, Startup, Extended, Process, Limits, Accounting = B._Windows_Build_API()
        Calls, Inherited = [], []
        def _Initialize(Address, Count, Flags, Size):
            C.cast(Size, C.POINTER(C.c_size_t))[0] = 256
            return bool(Address)
        def _Update(Address, Flags, Attribute, Value, Size, Previous, Returned):
            Calls.append(Attribute)
            if Attribute == 0x2000D:
                self.assertEqual(list(Value), [98])
            else:
                Inherited.extend(list(Value))
            return True
        def _Duplicate(Current, Original, Target, Address, Rights, Inherit, Options):
            C.cast(Address, C.POINTER(W.HANDLE))[0] = 101 + len(Inherited)
            Inherited.append(101 + len(Inherited))
            self.assertTrue(Inherit)
            return True
        def _Create(Application, Command, Process_Attributes, Thread_Attributes, Inherit, Flags, Environment, Directory, Start, Information):
            self.assertEqual(Calls, [0x2000D, 0x20002])
            self.assertEqual(set(Inherited), {101, 102})
            self.assertNotIn(98, Inherited)
            self.assertTrue(Flags & 0x80000 and Flags & 0x8000000)
            self.assertEqual(Start.contents.cb, C.sizeof(Extended))
            self.assertEqual(Start.contents.dwFlags, 0x101)
            Result = C.cast(Information, C.POINTER(Process)).contents
            Result.hProcess, Result.hThread = 201, 202
            return True
        def _Exit(Handle, Address):
            C.cast(Address, C.POINTER(W.DWORD))[0] = 0
            return True
        def _Wait(Handle, Milliseconds):
            self.assertEqual({Call.args[0] for Call in Api.CloseHandle.call_args_list}, {101, 102})
            return 0
        Api = SimpleNamespace(CreateJobObjectW=Mock(return_value=98), SetInformationJobObject=Mock(return_value=True),
                              InitializeProcThreadAttributeList=Mock(side_effect=_Initialize), UpdateProcThreadAttribute=Mock(side_effect=_Update),
                              GetCurrentProcess=Mock(return_value=1), DuplicateHandle=Mock(side_effect=_Duplicate),
                              CreateProcessW=Mock(side_effect=_Create), WaitForSingleObject=Mock(side_effect=_Wait), GetExitCodeProcess=Mock(side_effect=_Exit),
                              TerminateJobObject=Mock(return_value=True), QueryInformationJobObject=Mock(return_value=True),
                              CloseHandle=Mock(return_value=True), DeleteProcThreadAttributeList=Mock())
        Types = C, W, Api, Startup, Extended, Process, Limits, Accounting
        with (self._Folder / "Windows.log").open("w", encoding="utf-8") as Stream, patch.object(B, "_Windows_Build_API", return_value=Types):
            Record = B._Windows_Bounded_Build([sys.executable], self._Folder, Stream, time.monotonic() + 10)
        self.assertEqual(Record["Cleanup"], "complete")
        Api.CreateJobObjectW.assert_called_once_with(None, None)
        Api.TerminateJobObject.assert_called_once_with(98, 1)
        self.assertEqual({Call.args[0] for Call in Api.CloseHandle.call_args_list}, {98, 101, 102, 201, 202})
        Calls.clear()
        Inherited.clear()
        Api.TerminateJobObject.reset_mock()
        Api.CloseHandle.reset_mock()
        Api.WaitForSingleObject.side_effect = KeyboardInterrupt("controlled wait interruption")
        with (self._Folder / "Windows_Interrupted.log").open("w", encoding="utf-8") as Stream, patch.object(B, "_Windows_Build_API", return_value=Types):
            with self.assertRaises(KeyboardInterrupt):
                B._Windows_Bounded_Build([sys.executable], self._Folder, Stream, time.monotonic() + 10)
        Api.TerminateJobObject.assert_called_once_with(98, 1)
        self.assertEqual({Call.args[0] for Call in Api.CloseHandle.call_args_list}, {98, 101, 102, 201, 202})
        self.assertIn('"Cleanup": "complete"', (self._Folder / "Windows_Interrupted.log").read_text(encoding="utf-8"))
        Calls.clear()
        Inherited.clear()
        Api.TerminateJobObject.reset_mock()
        Api.CloseHandle.reset_mock()
        Interrupted = []
        def _Close(Handle):
            if Handle == 102 and not Interrupted:
                Interrupted.append(Handle)
                raise KeyboardInterrupt("interruption after closing inherited handle")
            return True
        Api.CloseHandle.side_effect = _Close
        with (self._Folder / "Windows_Close_Interrupted.log").open("w", encoding="utf-8") as Stream, patch.object(B, "_Windows_Build_API", return_value=Types):
            with self.assertRaises(KeyboardInterrupt):
                B._Windows_Bounded_Build([sys.executable], self._Folder, Stream, time.monotonic() + 10)
        Api.TerminateJobObject.assert_called_once_with(98, 1)
        Closed = [Call.args[0] for Call in Api.CloseHandle.call_args_list]
        self.assertEqual(set(Closed), {98, 101, 102, 201, 202})
        self.assertEqual(len(Closed), len(set(Closed)), "A retired handle value was closed again")

    def test_Interrupted_Bounded_Worker_Preserves_Interrupt_And_Log(self):
        Name = "_Windows_Bounded_Build" if os.name == "nt" else "_Posix_Bounded_Build"
        Log = self._Folder / "Interrupted.log"
        with Log.open("w", encoding="utf-8") as Stream, patch.object(B, Name, side_effect=KeyboardInterrupt("controlled interrupt")):
            with self.assertRaises(KeyboardInterrupt):
                B._Run_Bounded_Build([sys.executable], self._Folder, Stream, 10)
        self.assertIn('"Status": "interrupted"', Log.read_text(encoding="utf-8"))

    def test_Log_Failure_Cannot_Replace_An_Original_Interrupt(self):
        Error = KeyboardInterrupt("original interruption")
        with patch.object(B, "_Deadline_Log", side_effect=OSError("disk full")):
            B._Deadline_Exception_Log(None, {}, Error)
            with self.assertRaises(OSError):
                B._Deadline_Exception_Log(None, {}, None)
        self.assertIn("disk full", Error.__notes__[0])

class Build_Deadline_Processes(unittest.TestCase):
    _Root = Path(__file__).resolve().parents[1]

    def test_Real_Bounded_Compile_And_Expired_Rebuild_Preserve_Published_Bytes(self):
        from PyCeler import Compile
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Source = Folder / "Bounded_Compile.pyx"
            Source.write_text("def Value():\n    return 73\n", encoding="utf-8")
            Environment = dict(PYCELER_BUILD_DIR=str(Folder / "Build"), PYCELER_BUILD_TIMEOUT_SECONDS="60")
            with patch.dict(os.environ, Environment):
                Binary = Compile(Source, Folder / "Output", Convert=False, OpenMP=False, Cache=False)
            Logs = list((Folder / "Build/Logs").glob("*.log"))
            self.assertEqual(len(Logs), 1)
            Records = [json.loads(Line.partition(": ")[2]) for Line in Logs[0].read_text(encoding="utf-8").splitlines() if Line.startswith("Build deadline: ")]
            self.assertEqual(Records[-1]["Return_Code"], 0)
            self.assertEqual(Records[-1]["Cleanup"], "complete")
            self.assertFalse(Records[-1]["Timed_Out"])
            self.assertTrue(Records[-1]["Launched"])
            Before = {File.name: File.read_bytes() for File in Binary.parent.iterdir() if File.is_file()}
            Program = "import importlib.util,json,sys\nSpec=importlib.util.spec_from_file_location('Bounded_Compile',sys.argv[1])\nModule=importlib.util.module_from_spec(Spec)\nSpec.loader.exec_module(Module)\nprint(json.dumps(dict(Value=Module.Value(),Binary=Module.__file__)))"
            Process = subprocess.run([sys.executable, "-I", "-B", "-c", Program, str(Binary)], capture_output=True, text=True, timeout=30)
            self.assertEqual(Process.returncode, 0, Process.stdout + Process.stderr)
            Loaded = json.loads(Process.stdout)
            self.assertEqual(Loaded["Value"], 73)
            self.assertEqual(Path(Loaded["Binary"]).resolve(), Binary.resolve())
            Source.write_text("def Value():\n    return 91\n", encoding="utf-8")
            with patch.dict(os.environ, {**Environment, "PYCELER_BUILD_TIMEOUT_SECONDS": "1e-300"}):
                with self.assertRaises(B._Build_Timeout) as Caught:
                    Compile(Source, Binary.parent, Convert=False, OpenMP=False, Cache=False)
            After = {File.name: File.read_bytes() for File in Binary.parent.iterdir() if File.is_file()}
            self.assertEqual(After, Before)
            self.assertEqual(Caught.exception.Cleanup, "complete")
            Expired = [json.loads(Line.partition(": ")[2]) for Line in Caught.exception.Log.read_text(encoding="utf-8").splitlines() if Line.startswith("Build deadline: ")]
            self.assertTrue(Expired[-1]["Timed_Out"])
            self.assertFalse(Expired[-1]["Launched"])
            Report = dict(Binary=str(Binary), Binary_SHA256=hashlib.sha256(Binary.read_bytes()).hexdigest(), Loaded=Loaded,
                          Successful_Deadline=Records[-1], Expired_Deadline=Expired[-1], Published_Bytes_Unchanged=True)
            (Folder / "Bounded_Compile.json").write_text(json.dumps(Report, indent=2), encoding="utf-8")

    def _Wait(self, File, Seconds=15):
        End = time.monotonic() + Seconds
        while not File.is_file():
            if time.monotonic() >= End:
                self.fail("Controlled worker readiness was not reached: " + str(File))
            time.sleep(0.01)

    def _Case(self, Mode):
        with Temporary_Directory(dir=self._Root / "Test_Run") as Directory:
            Folder = Path(Directory)
            Token = uuid.uuid4().hex
            Fixture = self._Root / "Test/Build_Deadline_Child.py"
            Sentinel = subprocess.Popen([sys.executable, "-I", "-B", str(Fixture), str(Folder), "sentinel", Mode, Token], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            Stop = threading.Event()
            Records, Errors, Handles = [], [], []
            def _Watch():
                try:
                    End = time.monotonic() + 15
                    while not (Folder / "worker.json").is_file():
                        if Stop.wait(0.01):
                            return
                        if time.monotonic() >= End:
                            raise AssertionError("The owned process tree never became ready")
                    for Role in ("worker", "child", "grandchild"):
                        Record = json.loads((Folder / (Role + ".json")).read_text(encoding="utf-8"))
                        if Record["Token"] != Token or Record["Role"] != Role:
                            raise AssertionError(Record)
                        Records.append(Record)
                        if os.name == "nt":
                            import ctypes as C
                            from ctypes import wintypes as W
                            Api = C.WinDLL("kernel32", use_last_error=True)
                            Api.OpenProcess.restype, Api.OpenProcess.argtypes = W.HANDLE, [W.DWORD, W.BOOL, W.DWORD]
                            Handle = Api.OpenProcess(0x100000, False, Record["Pid"])
                            if not Handle:
                                raise C.WinError(C.get_last_error())
                            Handles.append(Handle)
                    (Folder / "observed.ready").write_text(Token, encoding="utf-8")
                except BaseException as Error:
                    Errors.append(str(Error))
            Watcher = threading.Thread(target=_Watch)
            try:
                self._Wait(Folder / "sentinel.json")
                Watcher.start()
                with (Folder / "Worker.log").open("w", encoding="utf-8") as Stream:
                    Command = [sys.executable, "-I", "-B", str(Fixture), str(Folder), "worker", Mode, Token]
                    if Mode == "linger":
                        self.assertEqual(B._Run_Bounded_Build(Command, Folder, Stream, 10), 0)
                    else:
                        with self.assertRaises(B._Build_Timeout) as Caught:
                            B._Run_Bounded_Build(Command, Folder, Stream, 4)
                        self.assertEqual(Caught.exception.Cleanup, "complete")
                Stop.set()
                Watcher.join(timeout=5)
                self.assertFalse(Watcher.is_alive())
                self.assertFalse(Errors, Errors)
                self.assertEqual([Record["Role"] for Record in Records], ["worker", "child", "grandchild"])
                self.assertIsNone(Sentinel.poll(), "Cleanup terminated the unrelated sentinel")
                if os.name == "nt":
                    C, W, Api, *Types = B._Windows_Build_API()
                    Exit_Deadline = time.monotonic() + 5
                    for Handle in Handles:
                        Milliseconds = max(0, int((Exit_Deadline - time.monotonic()) * 1000))
                        self.assertEqual(Api.WaitForSingleObject(Handle, Milliseconds), 0)
                self.assertIsNone(Sentinel.poll(), "Termination observation affected the unrelated sentinel")
                Log = (Folder / "Worker.log").read_text(encoding="utf-8")
                self.assertIn("ready grandchild", Log)
                self.assertIn('"Cleanup": "complete"', Log)
                with (Folder / "Next.log").open("w", encoding="utf-8") as Stream:
                    self.assertEqual(B._Run_Bounded_Build([sys.executable, "-I", "-B", "-c", "print('next worker completed')"], Folder, Stream, 10), 0)
            finally:
                Stop.set()
                if Watcher.ident is not None:
                    Watcher.join(timeout=5)
                (Folder / "finish").write_text(Token, encoding="utf-8")
                (Folder / "sentinel.stop").write_text(Token, encoding="utf-8")
                try:
                    Sentinel.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    Sentinel.terminate()
                    Sentinel.wait(timeout=5)
                if Handles:
                    C, W, Api, *Types = B._Windows_Build_API()
                    for Handle in Handles:
                        Api.CloseHandle(Handle)

    def test_Deadline_Terminates_Only_Owned_Child_And_Grandchild(self):
        self._Case("ignore")

    def test_Successful_Worker_Exit_Closes_Lingering_Owned_Children(self):
        self._Case("linger")

if __name__ == "__main__":
    unittest.main()
