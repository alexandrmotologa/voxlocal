"""Unit tests for VoxLocal CLI commands and options."""

from typer.testing import CliRunner

from voxlocal import __version__
from voxlocal.cli import app

runner = CliRunner()


def test_cli_version_flag_long():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"VoxLocal version {__version__}" in result.stdout


def test_cli_version_flag_short():
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    assert f"VoxLocal version {__version__}" in result.stdout


def test_cli_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"VoxLocal version {__version__}" in result.stdout
