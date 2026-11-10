import unittest
from unittest.mock import Mock, patch
from PyCeler.Environment_Checker import Doctor

class Environment_Diagnostics(unittest.TestCase):
    def test_Inspection_Does_Not_Build(self):
        Backend = Mock()
        Backend._Interpreter.return_value = (["python"], "3.11")
        with patch("PyCeler.Environment_Checker._Backend", return_value=Backend), patch("PyCeler.Environment_Checker._Probe_Toolchain") as Probe:
            Report = Doctor()
        Probe.assert_not_called()
        Backend._Build.assert_not_called()
        self.assertFalse(Report["Build_Check"])
        self.assertEqual(Report["Candidates"]["Serial"]["Status"], "not run")
        self.assertIn("Cython", Report["Dependencies"])

    def test_Optional_OpenMP_Failure_Is_Reported_Separately(self):
        Backend = Mock()
        Backend._Interpreter.return_value = (["python"], "3.11")
        Results = [dict(Status="passed"), dict(Status="failed", Diagnostic="Missing OpenMP runtime")]
        with patch("PyCeler.Environment_Checker._Backend", return_value=Backend), patch("PyCeler.Environment_Checker._Probe_Toolchain", side_effect=Results) as Probe:
            Report = Doctor(Build_Check=True)
        self.assertEqual(Probe.call_count, 2)
        self.assertEqual(Report["Candidates"]["Serial"]["Status"], "passed")
        self.assertEqual(Report["Candidates"]["OpenMP"]["Status"], "failed")

    def test_Disabled_OpenMP_And_Invalid_Interpreter(self):
        Backend = Mock()
        Backend._Interpreter.side_effect = ValueError("Unsupported ABI floor")
        with patch("PyCeler.Environment_Checker._Backend", return_value=Backend), patch("PyCeler.Environment_Checker._Probe_Toolchain") as Probe:
            Report = Doctor(Build_Check=True, OpenMP=False)
        Probe.assert_not_called()
        self.assertEqual(Report["Python"]["Requested"]["Status"], "invalid")
        self.assertEqual(Report["Candidates"]["Serial"]["Status"], "not run")
        self.assertEqual(Report["Candidates"]["OpenMP"]["Status"], "disabled")
