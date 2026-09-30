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
    assert result.success is False
    assert result.to_tool_output()["success"] is False


def test_shared_checker_disables_untrusted_external_tools(tmp_path: Path) -> None:
    checker = TypeScriptChecker(CheckConfig(), working_dir=tmp_path)
    local_bin = tmp_path / "node_modules" / ".bin"
    local_bin.mkdir(parents=True)
    (local_bin / "eslint").write_text("malicious")

    with patch("amplifier_bundle_ts_dev.checker.subprocess.run") as run:
        result = checker.check_files([tmp_path])

    run.assert_not_called()
    assert {issue.code for issue in result.issues} == {"TOOL-EXECUTION-DISABLED"}
    assert result.success is False
    assert result.to_tool_output()["success"] is False


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
        root = (Path(directory) / "workspace").resolve()
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
    assert result.success is False


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
    monkeypatch.setenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", str(workspace))
    handler = mounted_handler(adapter, child, {})
    checks = {"checks": ["stubs"]} if adapter[0] == "tool" else {}
    result = invoke_handler(adapter, handler, "file.ts", **checks)
    output = str(vars(result))
    assert "CHILD_MARKER" in output
    assert "WRONG_MARKER" not in output
    assert "TOOL-EXECUTION-DISABLED" not in output
    denied = invoke_handler(adapter, handler, "../../private.ts", **checks)
    assert "outside the workspace" in str(vars(denied))


def direct_handler(adapter, working_dir, config):
    name, module = adapter
    if name == "tool":
        return module.TsCheckTool(config, working_dir=working_dir).execute
    return module.TsCheckHooks(config, working_dir=working_dir).handle_tool_post


@pytest.mark.parametrize("construction", ["mounted", "direct"])
def test_module_config_cannot_grant_trust_or_expand_workspace(adapter, workspace, monkeypatch, construction):
    source = workspace / "file.ts"
    outside = workspace.parent / "outside.ts"
    source.write_text("const value = 1;\n")
    outside.write_text("const outside = 1;\n")
    (workspace / "package.json").write_text('{"amplifier-ts-dev":{"allow_external_tools":true}}')
    monkeypatch.delenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", raising=False)
    config = {"allow_external_tools": True, "workspace_root": "/", "checks": ["eslint"]}
    handler = (
        mounted_handler(adapter, workspace, config)
        if construction == "mounted"
        else direct_handler(adapter, workspace, config)
    )
    core_module = sys.modules[f"{adapter[1].__name__}._core"]

    with patch.object(core_module.subprocess, "run") as run:
        result = invoke_handler(adapter, handler, "file.ts", checks=["eslint"])

    run.assert_not_called()
    assert "TOOL-EXECUTION-DISABLED" in str(vars(result))
    rejected = invoke_handler(adapter, handler, outside, checks=["eslint"])
    assert "outside the workspace" in str(vars(rejected))


def test_trusted_workspace_environment_authorizes_only_its_root(adapter, workspace, monkeypatch):
    child = workspace / "src"
    child.mkdir()
    sibling = workspace / "sibling.ts"
    outside = workspace.parent / "outside.ts"
    sibling.write_text("const value = 1;\n")
    outside.write_text("const outside = 1;\n")
    monkeypatch.chdir(workspace.parent)
    monkeypatch.setenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", str(workspace))
    config = {"allow_external_tools": False, "workspace_root": "/", "checks": ["eslint"]}
    handler = direct_handler(adapter, child, config)
    core_module = sys.modules[f"{adapter[1].__name__}._core"]
    with (
        patch.object(core_module.TypeScriptChecker, "_find_executable", return_value="/host/bin/tool"),
        patch.object(core_module.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="[]")) as run,
    ):
        invoke_handler(adapter, handler, "../sibling.ts", checks=["eslint"])
    run.assert_called_once()
    command = run.call_args.args[0]
    assert command[command.index("--") + 1 :] == [str(sibling)]
    assert run.call_args.kwargs["cwd"] == child
    rejected = invoke_handler(adapter, handler, "../../outside.ts", checks=["eslint"])
    assert "outside the workspace" in str(vars(rejected))


@pytest.mark.parametrize("environment", ["missing", "relative", "nonexistent", "file", "unrelated-directory"])
def test_invalid_trusted_workspace_environment_fails_closed(adapter, workspace, monkeypatch, environment):
    if environment == "missing":
        monkeypatch.delenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", raising=False)
    elif environment == "relative":
        monkeypatch.setenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", "relative")
    elif environment == "nonexistent":
        monkeypatch.setenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", str(workspace / "missing"))
    elif environment == "file":
        file_path = workspace / "not-a-directory"
        file_path.write_text("")
        monkeypatch.setenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", str(file_path))
    else:
        unrelated = workspace.parent / "unrelated"
        unrelated.mkdir()
        monkeypatch.setenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", str(unrelated))

    config = {"allow_external_tools": True, "workspace_root": "/", "checks": ["eslint"]}
    handler = direct_handler(adapter, workspace, config)
    instance = handler.__self__

    assert instance.workspace_root == workspace
    assert instance.allow_external_tools is False
    if adapter[0] == "hooks":
        assert instance.check_config.allow_external_tools is False


def test_unresolvable_trusted_workspace_environment_fails_closed(adapter, workspace, monkeypatch):
    unresolvable = workspace / "unresolvable"
    unresolvable.mkdir()
    monkeypatch.setenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", str(unresolvable))
    module = adapter[1]
    original_resolve = Path.resolve

    def raise_for_trusted_root(path, *args, **kwargs):
        if path == unresolvable:
            raise OSError("cannot resolve trusted workspace")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(module.Path, "resolve", raise_for_trusted_root)
    handler = direct_handler(adapter, workspace, {"allow_external_tools": True, "workspace_root": "/"})
    instance = handler.__self__

    assert instance.workspace_root == workspace
    assert instance.allow_external_tools is False


def test_mounted_adapters_do_not_authorize_parent_by_discovery(adapter, workspace):
    child = workspace / "src"
    child.mkdir()
    (workspace / "file.ts").write_text("// TODO: WRONG_MARKER\n")
    handler = mounted_handler(adapter, child, {})
    result = invoke_handler(adapter, handler, "../file.ts")
    assert "outside the workspace" in str(vars(result))


@pytest.mark.parametrize("adapter", ["hooks"], indirect=True)
def test_behavior_default_hook_runs_only_stubs(adapter, workspace):
    source = workspace / "file.ts"
    source.write_text("// TODO: DEFAULT_HOOK_MARKER\n")
    behavior = (ROOT / "behaviors" / "ts-dev.yaml").read_text()
    expected_hook_checks = """      checks:
        - stubs
"""
    assert expected_hook_checks in behavior
    handler = mounted_handler(adapter, workspace, {"checks": ["stubs"]})
    core_module = sys.modules[f"{adapter[1].__name__}._core"]

    with patch.object(core_module.subprocess, "run") as run:
        result = invoke_handler(adapter, handler, "file.ts")

    run.assert_not_called()
    output = str(vars(result))
    assert "DEFAULT_HOOK_MARKER" in output
    assert "TOOL-EXECUTION-DISABLED" not in output


@pytest.mark.parametrize("adapter", ["hooks"], indirect=True)
def test_bare_hook_constructor_runs_only_stubs(adapter, workspace):
    source = workspace / "file.ts"
    source.write_text("// TODO: BARE_HOOK_MARKER\n")
    hooks = adapter[1].TsCheckHooks(working_dir=workspace)
    core_module = sys.modules[f"{adapter[1].__name__}._core"]

    with patch.object(core_module.subprocess, "run") as run:
        result = asyncio.run(
            hooks.handle_tool_post("tool:post", {"tool_name": "write_file", "tool_input": {"path": "file.ts"}})
        )

    run.assert_not_called()
    output = str(vars(result))
    assert "BARE_HOOK_MARKER" in output
    assert "TOOL-EXECUTION-DISABLED" not in output


@pytest.mark.parametrize("adapter", ["hooks"], indirect=True)
def test_trusted_hook_explicit_eslint_check_can_execute(adapter, workspace, monkeypatch):
    source = workspace / "file.ts"
    source.write_text("const value = 1;\n")
    monkeypatch.setenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", str(workspace))
    hooks = adapter[1].TsCheckHooks(
        {"checks": ["eslint"]},
        working_dir=workspace,
    )
    core_module = sys.modules[f"{adapter[1].__name__}._core"]

    with (
        patch.object(core_module.TypeScriptChecker, "_find_executable", return_value="/host/bin/eslint"),
        patch.object(
            core_module.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout="[]"),
        ) as run,
    ):
        asyncio.run(hooks.handle_tool_post("tool:post", {"tool_name": "write_file", "tool_input": {"path": "file.ts"}}))

    run.assert_called_once()


@pytest.mark.parametrize("adapter", ["tool"], indirect=True)
def test_tool_preserves_project_stub_disable_without_project_trust(adapter, workspace):
    source = workspace / "file.ts"
    source.write_text("// TODO: PROJECT_DISABLED_STUB_MARKER\n")
    (workspace / "package.json").write_text(
        '{"amplifier-ts-dev":{"enable_stub_check":false,"allow_external_tools":true}}'
    )
    handler = mounted_handler(adapter, workspace, {})
    core_module = sys.modules[f"{adapter[1].__name__}._core"]

    with patch.object(core_module.subprocess, "run") as run:
        result = asyncio.run(handler({"paths": ["file.ts"]}))

    run.assert_not_called()
    assert all(issue["code"] != "STUB" for issue in result.output["issues"])
    assert {issue["code"] for issue in result.output["issues"]} == {"TOOL-EXECUTION-DISABLED"}
    assert result.success is False
    assert result.output["success"] is False


@pytest.mark.parametrize("adapter", ["tool"], indirect=True)
def test_tool_empty_check_list_preserves_default_checks(adapter, workspace):
    source = workspace / "file.ts"
    source.write_text("// TODO: EMPTY_CHECKS_MARKER\n")
    handler = mounted_handler(adapter, workspace, {})
    core_module = sys.modules[f"{adapter[1].__name__}._core"]

    with patch.object(core_module.subprocess, "run") as run:
        result = asyncio.run(handler({"paths": ["file.ts"], "checks": []}))

    run.assert_not_called()
    assert result.success is False
    assert result.output["success"] is False
    assert "stub-check" in result.output["checks_run"]
    assert {issue["code"] for issue in result.output["issues"]} == {"STUB", "TOOL-EXECUTION-DISABLED"}
    assert any("EMPTY_CHECKS_MARKER" in issue["message"] for issue in result.output["issues"])


@pytest.mark.parametrize("adapter", ["tool"], indirect=True)
def test_tool_explicit_stubs_override_project_stub_disable(adapter, workspace):
    source = workspace / "file.ts"
    source.write_text("// TODO: EXPLICIT_STUB_MARKER\n")
    (workspace / "package.json").write_text('{"amplifier-ts-dev":{"enable_stub_check":false}}')
    handler = mounted_handler(adapter, workspace, {})
    core_module = sys.modules[f"{adapter[1].__name__}._core"]

    with patch.object(core_module.subprocess, "run") as run:
        result = asyncio.run(handler({"paths": ["file.ts"], "checks": ["stubs"]}))

    run.assert_not_called()
    assert {issue["code"] for issue in result.output["issues"]} == {"STUB"}


@pytest.mark.parametrize("adapter", ["tool"], indirect=True)
def test_tool_preserves_project_exclude_patterns(adapter, workspace):
    source = workspace / "excluded.ts"
    source.write_text("// TODO: EXCLUDED_BY_PROJECT_CONFIG\n")
    (workspace / "package.json").write_text('{"amplifier-ts-dev":{"exclude_patterns":["excluded"]}}')
    handler = mounted_handler(adapter, workspace, {})
    core_module = sys.modules[f"{adapter[1].__name__}._core"]

    with patch.object(core_module.subprocess, "run") as run:
        result = asyncio.run(handler({"paths": ["."]}))

    run.assert_not_called()
    assert all(issue["code"] != "STUB" for issue in result.output["issues"])


@pytest.mark.parametrize("adapter", ["tool"], indirect=True)
def test_tool_does_not_load_parent_package_outside_workspace(adapter, workspace):
    child = workspace / "nested"
    child.mkdir()
    source = child / "file.ts"
    source.write_text("// TODO: OUTSIDE_PARENT_CONFIG_MARKER\n")
    (workspace / "package.json").write_text('{"amplifier-ts-dev":{"enable_stub_check":false}}')
    handler = mounted_handler(adapter, child, {})
    core_module = sys.modules[f"{adapter[1].__name__}._core"]

    with patch.object(core_module.subprocess, "run") as run:
        result = asyncio.run(handler({"paths": ["file.ts"]}))

    run.assert_not_called()
    assert any(issue["code"] == "STUB" for issue in result.output["issues"])


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
    monkeypatch.setenv("AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT", str(workspace))
    handler = mounted_handler(adapter, child, {})
    result = asyncio.run(handler({}))
    assert "CHILD_MARKER" in str(result.output)
    assert "WRONG_MARKER" not in str(result.output)
    result = asyncio.run(handler({"content": "// TODO: CONTENT_MARKER\n"}))
    assert "CONTENT_MARKER" in str(result.output)
    assert sorted(path.name for path in child.iterdir()) == ["file.ts"]
