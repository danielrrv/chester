# -*- coding: utf-8 -*-
import unittest
import subprocess
from unittest.mock import patch, MagicMock
from core.commands.commands import SecurityGuard, execute_protected_command

class TestSecurityGuard(unittest.TestCase):

    def test_forbidden_binaries(self):
        for binary in SecurityGuard.FORBIDDEN_BINARIES:
            command = {"binary": binary, "args": []}
            is_safe, message = SecurityGuard.is_safe(command)
            self.assertFalse(is_safe, f"Binary '{binary}' should be forbidden")
            self.assertIn("estrictamente prohibido", message)

    def test_dangerous_patterns_in_args(self):
        dangerous_args = [
            {"binary": "ls", "args":["-rf", "/"]},
            {"binary": "cat", "args":["/etc/passwed"]},
            {"binary": "echo", "args":["../../secret.txt"]},
            {"binary": "mkdir", "args":["-m", "777", "test_dir"]}
        ]
        for command in dangerous_args:
            is_safe, message = SecurityGuard.is_safe(command)
            self.assertFalse(is_safe, f"Args {command['args']} should be dangerous")
            self.assertIn("Patrón peligroso detectado", message)

    def test_dangerous_patterns_in_inline_script(self):
        dangerous_scripts = [
            {"binary": "bash", "inline_script": "rm -rf /"},
            {"binary": "python", "inline_script": "import os; open('/etc/shadow')"},
            {"binary": "sh", "inline_script": "cd ../../ && ls"},
            {"binary": "perl", "inline_script": "chmod 77 file"}
        ]
        for command in dangerous_scripts:
            is_safe, message = SecurityGuard.is_safe(command)
            self.assertFalse(is_safe, f"Inline script '{command['inline_script']}' should be dangerous")
            self.assertIn("Patrón peligroso detectado", message)

    def test_safe_commands(self):
        safe_commands = [
            {"binary": "ls", "args":["-l", "."]},
            {"binary": "echo", "args":["Hello, World!"]},
            {"binary": "python", "inline_script": "print('Safe script')"}]
        for command in safe_commands: 
            is_safe, message = SecurityGuard.is_safe(command)
            self.assertTrue(is_safe, f"Command '{command}' should be safe")
            self.assertEqual("Safe", message)

class TestExecutedProtectedCommand(unittest.TestCase):

    @patch('commands.subprocess.run')
    @patch('commands.subprocess.Popen')
    def test_security_refusal(self, mock_popen, mock_run):
        #test with a forbidden binary
        command = {"binary": "rm", "args": ["file.txt"]}
        result = execute_protected_command(command)
        self.assertIn("SECURITY_REFUSAL", result)
        mock_run.assert_not_called()
        mock_popen.assert_not_called()

        #test with a dangerous pattern in args
        command = {"binary": "ls", "args": ["-rf", "/"]}
        result = execute_protected_command(command)
        self.assertIn("SECURITY_REFUSAL", result)
        mock_run.assert_not_called()
        mock_popen.assert_not_called()

    @patch('commands.subprocess.run')
    @patch('commands.subprocess.Popen')
    def test_successful_binary_execution(self, mock_popen, mock_run):
        mock_run.return_value = MagicMock(stdout="output from ls", stderr="", returncode=0)
        command = {"binary": "ls", "args": ["-l"]}
        result = execute_protected_command(command)
        self.assertIn("STDOUT: output from ls", result)
        self.assertIn("STDERR: ", result)
        mock_run.assert_called_once_with(["ls", "-l"], capture_output=True, text=True, timeout=30)
        mock_popen.assert_not_called()

    @patch('commands.subprocess.Popen')
    @patch('commands.subprocess.run')
    def test_successful_inline_script_execution(self, mock_run, mock_popen):
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("output from script", "")
        mock_popen.return_value = mock_process

        command = {"binary": "bash", "inline_script": "echo hello"}
        result = execute_protected_command(command)

        self.assertIn("STDOUT: output from script", result)
        self.assertIn("STDERR: ", result)
        mock_popen.assert_called_once_with(
            ["bash"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        mock_process.communicate.assert_called_once_with(input="echo hello")
        mock_run.assert_not_called()

    @patch('commands.subprocess.run')
    @patch('commands.subprocess.Popen')
    def test_execution_esror_handling(self, mock_popen, mock_run):
        mock_run.side_effect = FileNotFoundError("binary not found")
        command = {"binary": "nonexistent_binary", "args": []}
        result = execute_protected_command(command)
        self.assertIn('EXECUTION_ERROR: binary not found', result)
        mock_run.assert_called_once()
        mock_popen.assert_not_called()

if __name__ == '__main__':
    unittest.main()
