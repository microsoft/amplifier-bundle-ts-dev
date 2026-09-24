import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from amplifier_bundle_ts_dev.checker import TypeScriptChecker
from amplifier_bundle_ts_dev.checker import validate_paths
from amplifier_bundle_ts_dev.models import CheckConfig

ROOT = Path(__file__).parents[1]


def load_module(name: str, path: Path, package: str | None = None) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name,
        path,
        submodule_search_locations=[str(path.parent)] if package else None,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "core_path",
    [
        ROOT / "modules/tool-ts-check/amplifier_module_tool_ts_check/_core.py",
        ROOT / "modules/hooks-ts-check/amplifier_module_hooks_ts_check/_core.py",
    ],
)
def test_all_checker_copies_disable_untrusted_external_tools(tmp_path: Path, core_path: Path) -> None:
    core = load_module(f"security_core_{core_path.parent.parent.name}", core_path)
    checker = core.TypeScriptChecker(core.CheckConfig())
    checker.project_root = tmp_path
    local_bin = tmp_path / "node_modules" / ".bin"
    local_bin.mkdir(parents=True)
    (local_bin / "eslint").write_text("malicious")

    with patch.object(core.subprocess, "run") as run:
        result = checker.check_files([tmp_path])

    run.assert_not_called()
    assert {issue.code for issue in result.issues} == {"TOOL-EXECUTION-DISABLED"}


def test_shared_checker_disables_untrusted_external_tools(tmp_path: Path) -> None:
    checker = TypeScriptChecker(CheckConfig())
    checker.project_root = tmp_path
    local_bin = tmp_path / "node_modules" / ".bin"
    local_bin.mkdir(parents=True)
    (local_bin / "eslint").write_text("malicious")

    with patch("amplifier_bundle_ts_dev.checker.subprocess.run") as run:
        result = checker.check_files([tmp_path])

    run.assert_not_called()
    assert {issue.code for issue in result.issues} == {"TOOL-EXECUTION-DISABLED"}


def test_checker_rejects_option_and_outside_workspace_paths(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.ts"

    with pytest.raises(ValueError, match="must not begin"):
        validate_paths(["--config=payload.cjs"], tmp_path)
    with pytest.raises(ValueError, match="outside the workspace"):
        validate_paths([outside], tmp_path)


def test_project_config_cannot_enable_external_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "package.json").write_text('{"amplifier-ts-dev":{"allow_external_tools":true}}')
    monkeypatch.chdir(tmp_path)
    checker = TypeScriptChecker()

    assert checker.config.allow_external_tools is False


@pytest.mark.parametrize("runner_name", ["_run_eslint", "_run_prettier"])
def test_cli_uses_end_of_options_before_canonical_path(tmp_path: Path, runner_name: str) -> None:
    source = tmp_path / "src" / "file-name.ts"
    source.parent.mkdir()
    source.write_text("const value = 1;\n")
    checker = TypeScriptChecker(CheckConfig(enable_stub_check=False, enable_tsc=False, allow_external_tools=True))
    checker.project_root = tmp_path

    with (
        patch.object(checker, "_find_executable", return_value="trusted-tool"),
        patch("amplifier_bundle_ts_dev.checker.subprocess.run") as run,
    ):
        run.return_value.returncode = 0
        run.return_value.stdout = "[]"
        getattr(checker, runner_name)(validate_paths([source], tmp_path))

    command = run.call_args.args[0]
    marker = command.index("--")
    assert command[marker + 1 :] == [str(source.resolve())]


def test_tsc_receives_canonical_non_option_path(tmp_path: Path) -> None:
    source = tmp_path / "src" / "file.ts"
    source.parent.mkdir()
    source.write_text("const value: number = 1;\n")
    checker = TypeScriptChecker(CheckConfig(allow_external_tools=True))
    checker.project_root = tmp_path

    with (
        patch.object(checker, "_find_executable", return_value="trusted-tsc"),
        patch("amplifier_bundle_ts_dev.checker.subprocess.run") as run,
    ):
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        checker._run_tsc(validate_paths([source], tmp_path))

    command = run.call_args.args[0]
    assert str(source.resolve()) in command
    assert all(not operand.startswith("-") for operand in command if operand == str(source.resolve()))


def test_tool_rejects_leading_dash_path_before_checking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    amplifier_core = ModuleType("amplifier_core")

    class ToolResult:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    amplifier_core.__dict__["ToolResult"] = ToolResult
    monkeypatch.setitem(sys.modules, "amplifier_core", amplifier_core)
    package_name = "amplifier_module_tool_ts_check"
    package = ModuleType(package_name)
    package.__path__ = [str(ROOT / "modules/tool-ts-check" / package_name)]
    monkeypatch.setitem(sys.modules, package_name, package)
    core = load_module(
        f"{package_name}._core",
        ROOT / "modules/tool-ts-check" / package_name / "_core.py",
    )
    monkeypatch.setitem(sys.modules, f"{package_name}._core", core)
    tool_module = load_module(
        f"{package_name}.__init__",
        ROOT / "modules/tool-ts-check" / package_name / "__init__.py",
        package=package_name,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "package.json").write_text("{}")

    with patch.object(tool_module, "check_files") as check_files:
        result = asyncio.run(tool_module.TsCheckTool().execute({"paths": ["--config=payload.cjs"]}))

    check_files.assert_not_called()
    assert result.success is False
    assert result.output["code"] == "INVALID-PATH"


def test_hook_rejects_leading_dash_path_before_checking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    amplifier_core = ModuleType("amplifier_core")

    class HookResult:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    amplifier_core.__dict__["HookResult"] = HookResult
    monkeypatch.setitem(sys.modules, "amplifier_core", amplifier_core)
    package_name = "amplifier_module_hooks_ts_check"
    package = ModuleType(package_name)
    package.__path__ = [str(ROOT / "modules/hooks-ts-check" / package_name)]
    monkeypatch.setitem(sys.modules, package_name, package)
    core = load_module(
        f"{package_name}._core",
        ROOT / "modules/hooks-ts-check" / package_name / "_core.py",
    )
    monkeypatch.setitem(sys.modules, f"{package_name}._core", core)
    hooks_module = load_module(
        f"{package_name}.__init__",
        ROOT / "modules/hooks-ts-check" / package_name / "__init__.py",
        package=package_name,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "-payload.ts").write_text("const value = 1;\n")

    with patch.object(hooks_module, "check_files", new=AsyncMock()) as check_files:
        result = asyncio.run(
            hooks_module.TsCheckHooks().handle_tool_post(
                "tool:post",
                {"tool_name": "write_file", "tool_input": {"path": "-payload.ts"}},
            )
        )

    check_files.assert_not_called()
    assert result.user_message_level == "error"
