"""Tests for server CLI module."""

import pytest
from memu.server.cli import main


class TestServerCLI:
    """Test suite for memu-server CLI."""

    def test_cli_help(self, capsys):
        """Test that CLI shows help without error."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "MemU Server" in captured.out

    def test_cli_version(self, capsys):
        """Test that CLI shows version."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "1.4.0" in captured.out

    def test_cli_info(self, capsys):
        """Test info command."""
        result = main(["info"])
        
        assert result == 0
        captured = capsys.readouterr()
        assert "MemU" in captured.out
        assert "1.4.0" in captured.out

    def test_cli_start(self, capsys):
        """Test start command."""
        result = main(["start", "--host", "0.0.0.0", "--port", "8080"])
        
        assert result == 0
        captured = capsys.readouterr()
        assert "Starting MemU server" in captured.out
        assert "0.0.0.0" in captured.out
        assert "8080" in captured.out

    def test_cli_start_default(self, capsys):
        """Test start command with default values."""
        result = main(["start"])
        
        assert result == 0
        captured = capsys.readouterr()
        assert "127.0.0.1" in captured.out
        assert "8000" in captured.out

    def test_cli_no_args_shows_help(self, capsys):
        """Test that running without args shows help."""
        result = main([])
        
        assert result == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out
