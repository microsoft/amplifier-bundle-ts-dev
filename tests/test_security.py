import asyncio
import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from amplifier_bundle_ts_dev import checker as shared_core
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
    checker = core.TypeScriptChecker(core.CheckConfig(), working_dir=tmp_path)
    local_bin = tmp_path / "node_modules" / ".bin"
    local_bin.mkdir(parents=True)
    (local_bin / "eslint").write_text("malicious")

    with patch.object(core.subprocess, "run") as run:
        result = checker.check_files([tmp_path])

    run.assert_not_called()
    assert {issue.code for issue in result.issues} == {"TOOL-EXECUTION-DISABLED"}


def test_shared_checker_disables_untrusted_external_tools(tmp_path: Path) -> None:
    checker = TypeScriptChecker(CheckConfig(), working_dir=tmp_path)
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


@pytest.fixture(params=["shared", "tool", "hooks"])
def core(request):
    if request.param == "shared":
        return shared_core
    name = request.param
    return load_module(
        f"boundary_core_{name}",
        ROOT / f"modules/{name}-ts-check/amplifier_module_{name}_ts_check/_core.py",
    )


@pytest.fixture
def workspace():
    # Stub detection deliberately suppresses files whose paths contain "test".
    # Use a neutral path so the positive controls exercise real stub detection.
    with tempfile.TemporaryDirectory(prefix="ts-boundary-") as directory:
        root = Path(directory) / "workspace"
        root.mkdir()
        (root / "package.json").write_text("{}")
        yield root


@pytest.fixture(autouse=True)
def no_real_external_tools(monkeypatch):
    # This entire suite uses synthetic binaries and mocked subprocess results.
    monkeypatch.setattr(shared_core.subprocess, "run", Mock(side_effect=AssertionError("real execution forbidden")))


def test_recursive_symlink_read_is_reauthorized(core, workspace):
    outside = workspace.parent / "private.txt"
    outside.write_text("// TODO: OUTSIDE_MARKER\n")
    inside = workspace / "local.ts"
    inside.write_text("// TODO: INSIDE_MARKER\n")
    nested = workspace / "src"
    nested.mkdir()
    (nested / "leak.ts").symlink_to(outside)
    (nested / "safe.ts").symlink_to(inside)
    outside_dir = workspace.parent / "private-dir"
    outside_dir.mkdir()
    (outside_dir / "hidden.ts").write_text("// TODO: OUTSIDE_DIRECTORY_MARKER\n")
    (nested / "linked-dir").symlink_to(outside_dir, target_is_directory=True)
    checker = core.TypeScriptChecker(core.CheckConfig(), working_dir=workspace)
    read_text = Path.read_text
    opened = []

    def guarded_read(path, *args, **kwargs):
        opened.append(path)
        assert path.resolve().is_relative_to(workspace), "outside read attempted"
        return read_text(path, *args, **kwargs)

    with patch.object(Path, "read_text", guarded_read):
        result = checker.check_files(["."])
    assert all(path.resolve().is_relative_to(workspace) for path in opened)
    assert inside in opened
    assert any("INSIDE_MARKER" in issue.message for issue in result.issues)
    assert not any("OUTSIDE_" in issue.message for issue in result.issues)
    assert any(issue.code == "INVALID-PATH" for issue in result.issues)
    assert not result.success
    assert checker.check_files([nested / "leak.ts"]).issues[0].code == "INVALID-PATH"
    assert checker.check_files([nested / "linked-dir"]).issues[0].code == "INVALID-PATH"


@pytest.mark.parametrize("name", ["eslint", "prettier", "tsc"])
def test_npm_sibling_package_symlinks_take_precedence(core, workspace, name):
    bin_dir = workspace / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    target = workspace / "node_modules" / name / "bin" / f"{name}.js"
    target.parent.mkdir(parents=True)
    target.write_text("synthetic, never executed")
    (bin_dir / name).symlink_to(f"../{name}/bin/{name}.js")
    checker = core.TypeScriptChecker(core.CheckConfig(allow_external_tools=True), working_dir=workspace)
    with patch.object(core.shutil, "which", return_value="/host/bin/tool") as which:
        assert checker._find_executable(name) == str(target)
        which.assert_not_called()


@pytest.mark.parametrize("layout", ["file-escape", "install-escape", "missing", "regular"])
def test_executable_confinement_and_global_fallback(core, workspace, layout):
    outside = workspace.parent / "outside-install"
    outside.mkdir()
    (outside / "eslint").write_text("never executed")
    install_dir = workspace / "node_modules"
    if layout == "install-escape":
        install_dir.symlink_to(outside, target_is_directory=True)
    bin_dir = install_dir / ".bin"
    bin_dir.mkdir(parents=True)
    if layout == "file-escape":
        (bin_dir / "eslint").symlink_to(outside / "eslint")
    elif layout in ("regular", "install-escape"):
        (bin_dir / "eslint").write_text("never executed")
    checker = core.TypeScriptChecker(core.CheckConfig(allow_external_tools=True), working_dir=workspace)
    with patch.object(core.shutil, "which", return_value=None):
        selected = checker._find_executable("eslint")
    assert selected == (str(bin_dir / "eslint") if layout == "regular" else None)
    if layout == "missing":
        with patch.object(core.shutil, "which", return_value="/host/bin/eslint"):
            assert checker._find_executable("eslint") == "/host/bin/eslint"


@pytest.mark.parametrize("trust", [False, None, "false", "true", 1, {}, [True]])
def test_only_literal_true_authorizes_lookup(core, workspace, trust):
    checker = core.TypeScriptChecker(core.CheckConfig(allow_external_tools=trust), working_dir=workspace)
    with patch.object(core.shutil, "which") as which:
        result = checker.check_files(["."])
    which.assert_not_called()
    assert {issue.code for issue in result.issues} == {"TOOL-EXECUTION-DISABLED"}


def test_relative_paths_use_cwd_not_package_root(core, workspace, monkeypatch):
    child = workspace / "src"
    child.mkdir()
    (child / "file.ts").write_text("// TODO: CHILD_MARKER\n")
    (workspace / "file.ts").write_text("// TODO: WRONG_MARKER\n")
    monkeypatch.chdir(child)
    assert core.validate_paths(["file.ts"], workspace) == [str(child / "file.ts")]
    monkeypatch.chdir(workspace.parent)
    checker = core.TypeScriptChecker(working_dir=child, workspace_root=workspace)
    assert checker.project_root == workspace
    result = checker.check_files(["file.ts"])
    assert any("CHILD_MARKER" in issue.message for issue in result.issues)
    assert not any("WRONG_MARKER" in issue.message for issue in result.issues)
    default_result = checker.check_files([])
    assert not any("WRONG_MARKER" in issue.message for issue in default_result.issues)
    assert checker.check_files(["../../private.ts"]).issues[0].code == "INVALID-PATH"


def test_package_metadata_cannot_expand_default_authorization(core, workspace):
    child = workspace / "src"
    child.mkdir()
    (workspace / "sibling.ts").write_text("// TODO: OUTSIDE_AUTHORITY\n")
    checker = core.TypeScriptChecker(working_dir=child)
    assert checker.workspace_root == child
    assert checker.project_root == child
    assert checker.check_files(["../sibling.ts"]).issues[0].code == "INVALID-PATH"
    with pytest.raises(ValueError, match="outside the workspace"):
        core.TypeScriptChecker(working_dir=workspace.parent, workspace_root=workspace)


def test_project_config_cannot_grant_trust_in_any_copy(core, workspace):
    (workspace / "package.json").write_text('{"amplifier-ts-dev":{"allow_external_tools":true}}')
    assert core.TypeScriptChecker(working_dir=workspace).config.allow_external_tools is False


def test_project_config_symlink_does_not_read_outside(core, workspace):
    outside = workspace.parent / "outside.json"
    outside.write_text('{"amplifier-ts-dev":{"enable_stub_check":false}}')
    (workspace / "package.json").unlink()
    (workspace / "package.json").symlink_to(outside)
    assert core.TypeScriptChecker(working_dir=workspace).config.enable_stub_check is True


@pytest.fixture(params=["tool", "hooks"])
def adapter(request, monkeypatch):
    amplifier_core = ModuleType("amplifier_core")
    amplifier_core.__dict__.update(ToolResult=SimpleNamespace, HookResult=SimpleNamespace)
    monkeypatch.setitem(sys.modules, "amplifier_core", amplifier_core)
    name = request.param
    module = load_module(
        f"boundary_adapter_{name}",
        ROOT / f"modules/{name}-ts-check/amplifier_module_{name}_ts_check/__init__.py",
        package=f"boundary_adapter_{name}",
    )
    return name, module


def mounted_handler(adapter, working_dir, config):
    name, module = adapter
    coordinator = SimpleNamespace(
        get_capability=Mock(return_value=str(working_dir)),
        mount=AsyncMock(),
        hooks=SimpleNamespace(register=Mock()),
    )
    asyncio.run(module.mount(coordinator, config))
    coordinator.get_capability.assert_called_once_with("session.working_dir")
    if name == "tool":
        return coordinator.mount.call_args.args[1].execute
    return coordinator.hooks.register.call_args.args[1]


def invoke_handler(adapter, handler, path, **extra):
    if adapter[0] == "tool":
        return asyncio.run(handler({"paths": [path], **extra}))
    return asyncio.run(handler("tool:post", {"tool_name": "write_file", "tool_input": {"path": path}, **extra}))


def test_mounted_adapters_use_host_session_cwd(adapter, workspace, monkeypatch):
    child = workspace / "src"
    child.mkdir()
    (child / "file.ts").write_text("// TODO: CHILD_MARKER\n")
    (workspace / "file.ts").write_text("// TODO: WRONG_MARKER\n")
    monkeypatch.chdir(workspace.parent)
    handler = mounted_handler(adapter, child, {"workspace_root": str(workspace)})
    result = invoke_handler(adapter, handler, "file.ts", allow_external_tools=True, workspace_root="/")
    output = str(vars(result))
    assert "CHILD_MARKER" in output
    assert "WRONG_MARKER" not in output
    assert "TOOL-EXECUTION-DISABLED" in output
    denied = invoke_handler(adapter, handler, "../../private.ts", workspace_root="/")
    assert "outside the workspace" in str(vars(denied))


@pytest.mark.parametrize("trust", ["false", "true", 1, False])
def test_mounted_adapters_require_boolean_trust(adapter, workspace, trust):
    (workspace / "file.ts").write_text("const value = 1;\n")
    handler = mounted_handler(adapter, workspace, {"allow_external_tools": trust})
    result = invoke_handler(adapter, handler, "file.ts")
    assert "TOOL-EXECUTION-DISABLED" in str(vars(result))


def test_mounted_adapters_keep_authorized_execution_cwd_and_operand(adapter, workspace, monkeypatch):
    child = workspace / "src"
    child.mkdir()
    (child / "file.ts").write_text("const value = 1;\n")
    monkeypatch.chdir(workspace.parent)
    handler = mounted_handler(
        adapter,
        child,
        {"workspace_root": str(workspace), "allow_external_tools": True, "checks": ["eslint", "prettier"]},
    )
    core_module = sys.modules[f"{adapter[1].__name__}._core"]
    with (
        patch.object(core_module.TypeScriptChecker, "_find_executable", return_value="/host/bin/tool"),
        patch.object(core_module.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="[]")) as run,
    ):
        invoke_handler(adapter, handler, "file.ts", fix=True, checks=["eslint", "prettier"])
    assert run.call_count == 2
    for call in run.call_args_list:
        command = call.args[0]
        assert command[command.index("--") + 1 :] == [str(child / "file.ts")]
        assert call.kwargs["cwd"] == child
    if adapter[0] == "tool":
        assert "--fix" in run.call_args_list[0].args[0]
        assert "--write" in run.call_args_list[1].args[0]


def test_mounted_adapters_do_not_authorize_parent_by_discovery(adapter, workspace):
    child = workspace / "src"
    child.mkdir()
    (workspace / "file.ts").write_text("// TODO: WRONG_MARKER\n")
    handler = mounted_handler(adapter, child, {})
    result = invoke_handler(adapter, handler, "../file.ts")
    assert "outside the workspace" in str(vars(result))


def test_shared_content_uses_session_directory(core, workspace, monkeypatch):
    child = workspace / "src"
    child.mkdir()
    monkeypatch.chdir(workspace.parent)
    checker = core.TypeScriptChecker(working_dir=child, workspace_root=workspace)
    result = checker.check_content("// TODO: CONTENT_MARKER\n")
    assert any(issue.file == "stdin.ts" and "CONTENT_MARKER" in issue.message for issue in result.issues)
    assert list(child.iterdir()) == []


@pytest.mark.parametrize("adapter", ["tool"], indirect=True)
def test_mounted_tool_default_directory_and_content(adapter, workspace, monkeypatch):
    child = workspace / "src"
    child.mkdir()
    (child / "file.ts").write_text("// TODO: CHILD_MARKER\n")
    (workspace / "wrong.ts").write_text("// TODO: WRONG_MARKER\n")
    monkeypatch.chdir(workspace.parent)
    handler = mounted_handler(adapter, child, {"workspace_root": str(workspace)})
    result = asyncio.run(handler({}))
    assert "CHILD_MARKER" in str(result.output)
    assert "WRONG_MARKER" not in str(result.output)
    result = asyncio.run(handler({"content": "// TODO: CONTENT_MARKER\n"}))
    assert "CONTENT_MARKER" in str(result.output)
    assert sorted(path.name for path in child.iterdir()) == ["file.ts"]
