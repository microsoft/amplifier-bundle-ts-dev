"""Amplifier tool module for TypeScript/JavaScript code quality checks.

This module provides the `ts_check` tool that agents can use to
check TypeScript/JavaScript code for formatting, linting, type errors, and stubs.
"""

from typing import Any

from amplifier_core import ToolResult

from ._core import CheckConfig
from ._core import check_content
from ._core import check_files


class TsCheckTool:
    """Tool for checking TypeScript/JavaScript code quality."""

    @property
    def name(self) -> str:
        return "ts_check"

    @property
    def description(self) -> str:
        return """Check TypeScript/JavaScript code for quality issues.

Runs ESLint (linting), Prettier (formatting), tsc (type checking), and stub detection
on TypeScript/JavaScript files or code content.

Input options:
- paths: List of file paths or directories to check
- content: TypeScript/JavaScript code as a string to check
- fix: If true, auto-fix issues where possible (only works with paths)

Examples:
- Check a file: {"paths": ["src/main.ts"]}
- Check a directory: {"paths": ["src/"]}
- Check multiple paths: {"paths": ["src/", "tests/test_main.ts"]}
- Check code string: {"content": "const x: any = 1;"}
- Auto-fix issues: {"paths": ["src/"], "fix": true}

Returns:
- success: True if no errors (warnings are OK)
- clean: True if no issues at all
- summary: Human-readable summary
- issues: List of issues with file, line, code, message, severity"""

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths or directories to check",
                },
                "content": {
                    "type": "string",
                    "description": "TypeScript/JavaScript code as a string to check (alternative to paths)",
                },
                "fix": {
                    "type": "boolean",
                    "description": "Auto-fix issues where possible",
                    "default": False,
                },
                "checks": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["eslint", "prettier", "tsc", "stubs"]},
                    "description": "Specific checks to run (default: all)",
                },
            },
        }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the TypeScript/JavaScript check tool.

        Args:
            input_data: Tool input with paths, content, fix, and/or checks

        Returns:
            ToolResult with check output
        """
        paths = input_data.get("paths")
        content = input_data.get("content")
        fix = input_data.get("fix", False)
        checks = input_data.get("checks")

        # Build config based on requested checks
        config_overrides = {}
        if checks:
            config_overrides["enable_eslint"] = "eslint" in checks
            config_overrides["enable_prettier"] = "prettier" in checks
            config_overrides["enable_tsc"] = "tsc" in checks
            config_overrides["enable_stub_check"] = "stubs" in checks

        config = CheckConfig.from_dict(config_overrides) if config_overrides else None

        # Run checks
        if content:
            result = check_content(content, config=config)
        elif paths:
            result = check_files(paths, config=config, fix=fix)
        else:
            # Default to current directory
            result = check_files(["."], config=config, fix=fix)

        return ToolResult(success=result.success, output=result.to_tool_output())


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Mount the ts_check tool into the coordinator.

    Args:
        coordinator: The Amplifier coordinator instance
        config: Optional module configuration

    Returns:
        Module metadata
    """
    tool = TsCheckTool()

    # Register the tool
    await coordinator.mount("tools", tool, name=tool.name)

    return {
        "name": "tool-ts-check",
        "version": "0.1.0",
        "provides": ["ts_check"],
    }
