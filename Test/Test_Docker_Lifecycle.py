import subprocess
import unittest
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from Test.Run_Docker import _Command, _Execute

class Docker_Lifecycle(unittest.TestCase):
    def test_Disposable_Container_And_Persistent_Output(self):
        for Architecture in ("amd64", "arm64"):
            for Version in ("3.11", "3.14"):
                Command = _Command("pyceler-test-example", Path("workspace"), Architecture, Version, True)
                self.assertIn("--rm", Command)
                self.assertEqual(Command[Command.index("--platform") + 1], f"linux/{Architecture}")
                self.assertIn("type=bind,source=workspace,target=/work", Command)
                self.assertIn("org.pyceler.test=true", Command)
                self.assertTrue(Command[-1].endswith("Test/Run.py --no-wheels"))

    def test_Cleanup_On_Success_And_Failure(self):
        for Status in (0, 1, 137):
            with patch("Test.Run_Docker.subprocess.run", side_effect=[SimpleNamespace(returncode=Status), SimpleNamespace(returncode=0, stdout="")]) as Run:
                self.assertEqual(_Execute(["docker", "run"], "owned", StringIO(), 60), Status)
                self.assertEqual(Run.call_args.args[0], ["docker", "rm", "--force", "owned"])

    def test_Cleanup_On_Timeout_And_Interruption(self):
        for Error in (subprocess.TimeoutExpired("docker", 60), KeyboardInterrupt()):
            with patch("Test.Run_Docker.subprocess.run", side_effect=[Error, SimpleNamespace(returncode=1, stdout="No such container: owned")]) as Run:
                with self.assertRaises(type(Error)):
                    _Execute(["docker", "run"], "owned", StringIO(), 60)
                self.assertEqual(Run.call_args.args[0], ["docker", "rm", "--force", "owned"])
