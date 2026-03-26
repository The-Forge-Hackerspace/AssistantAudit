"""
Tests for PowerShell script generation in interactive mode.

Covers the fix where interactive scripts were missing the Import-Module statement,
causing "Invoke-Monkey365 : The term 'Invoke-Monkey365' is not recognized" errors.
"""

from app.tools.monkey365_runner.executor import Monkey365Config, Monkey365Executor


def test_interactive_script_includes_module_import(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    assert "Set-Location" in script
    assert "Import-Module" in script
    assert "monkey365.psm1" in script
    assert "-Force" in script
    assert "Invoke-Monkey365" in script


def test_interactive_script_correct_module_path(tmp_path):
    monkey365_dir = tmp_path / "tools" / "monkey365"
    monkey365_dir.mkdir(parents=True)

    config = Monkey365Config(output_dir=str(tmp_path / "output"))

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path / "output"

    script = executor.build_script("test-scan")

    assert "Set-Location" in script


def test_script_module_import_before_invoke(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    import_pos = script.find("Import-Module")
    invoke_pos = script.find("Invoke-Monkey365")

    assert import_pos > 0
    assert invoke_pos > 0
    assert import_pos < invoke_pos


def test_script_uses_force_flag_for_reload(tmp_path):
    config = Monkey365Config(output_dir=str(tmp_path))

    monkey365_dir = tmp_path / "monkey365"
    monkey365_dir.mkdir()

    executor = Monkey365Executor.__new__(Monkey365Executor)
    executor.config = config
    executor.monkey365_path = monkey365_dir / "Invoke-Monkey365.ps1"
    executor.output_dir = tmp_path

    script = executor.build_script("test-scan")

    import_section = script[script.find("Import-Module"):script.find("Import-Module") + 100]
    assert "-Force" in import_section
