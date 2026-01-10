"""Core TypeScript/JavaScript checking logic.

This module contains all the checking logic, shared by:
- Tool module (ts_check tool for agents)
- Hook module (automatic checks on file events)
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import find_project_root
from .config import has_eslint_config
from .config import has_typescript_config
from .config import load_config
from .models import CheckConfig
from .models import CheckResult
from .models import Issue
from .models import Severity


class TypeScriptChecker:
    """Main checker that orchestrates ESLint, Prettier, tsc, and stub detection."""

    # File extensions to check
    TS_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts"}
    JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
    ALL_EXTENSIONS = TS_EXTENSIONS | JS_EXTENSIONS

    def __init__(self, config: CheckConfig | None = None):
        """Initialize checker with optional config."""
        self.config = config or load_config()
        self.project_root = find_project_root()

    def check_files(self, paths: list[str | Path], fix: bool = False) -> CheckResult:
        """Run all enabled checks on the given paths.

        Args:
            paths: Files or directories to check
            fix: If True, auto-fix issues where possible

        Returns:
            CheckResult with all issues found
        """
        if not paths:
            paths = [Path.cwd()]

        path_strs = [str(p) for p in paths]
        results = CheckResult(files_checked=self._count_ts_js_files(path_strs))

        if self.config.enable_eslint:
            eslint_result = self._run_eslint(path_strs, fix=fix)
            results = results.merge(eslint_result)

        if self.config.enable_prettier:
            prettier_result = self._run_prettier(path_strs, fix=fix)
            results = results.merge(prettier_result)

        if self.config.enable_tsc:
            tsc_result = self._run_tsc(path_strs)
            results = results.merge(tsc_result)

        if self.config.enable_stub_check:
            stub_result = self._run_stub_check(path_strs)
            results = results.merge(stub_result)

        return results

    def check_content(self, content: str, filename: str = "stdin.ts") -> CheckResult:
        """Check TypeScript/JavaScript content string.

        Args:
            content: Source code as string
            filename: Virtual filename for error reporting

        Returns:
            CheckResult with issues found
        """
        # Determine extension from filename
        ext = Path(filename).suffix or ".ts"

        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = self.check_files([temp_path])
            # Rewrite paths to use the original filename
            for issue in result.issues:
                if issue.file == temp_path:
                    issue.file = filename
            return result
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _count_ts_js_files(self, paths: list[str]) -> int:
        """Count TypeScript/JavaScript files in the given paths."""
        count = 0
        for path_str in paths:
            path = Path(path_str)
            if path.is_file() and path.suffix in self.ALL_EXTENSIONS:
                count += 1
            elif path.is_dir():
                for ext in self.ALL_EXTENSIONS:
                    count += len(list(path.rglob(f"*{ext}")))
        return count

    def _find_executable(self, name: str) -> str | None:
        """Find executable, preferring local node_modules."""
        # Check local node_modules/.bin first
        if self.project_root:
            local_bin = self.project_root / "node_modules" / ".bin" / name
            if local_bin.exists():
                return str(local_bin)

        # Check global
        return shutil.which(name)

    def _run_eslint(self, paths: list[str], fix: bool = False) -> CheckResult:
        """Run ESLint check."""
        eslint = self._find_executable("eslint")

        if not eslint:
            return CheckResult(
                issues=[
                    Issue(
                        file="",
                        line=0,
                        column=0,
                        code="TOOL-NOT-FOUND",
                        message="eslint not found. Install with: npm install -D eslint",
                        severity=Severity.WARNING,
                        source="eslint",
                    )
                ],
                checks_run=["eslint"],
            )

        cmd = [eslint, "--format=json"]
        if fix:
            cmd.append("--fix")

        # Add default config if project doesn't have one
        if not has_eslint_config(self.project_root):
            # Use basic recommended rules
            cmd.extend(["--no-eslintrc", "--env", "browser,node,es2022"])

        cmd.extend(paths)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return CheckResult(
                issues=[
                    Issue(
                        file="",
                        line=0,
                        column=0,
                        code="TIMEOUT",
                        message="ESLint timed out after 120 seconds",
                        severity=Severity.ERROR,
                        source="eslint",
                    )
                ],
                checks_run=["eslint"],
            )
        except FileNotFoundError:
            return CheckResult(
                issues=[
                    Issue(
                        file="",
                        line=0,
                        column=0,
                        code="TOOL-NOT-FOUND",
                        message="eslint not found. Install with: npm install -D eslint",
                        severity=Severity.WARNING,
                        source="eslint",
                    )
                ],
                checks_run=["eslint"],
            )

        issues = []
        if result.stdout.strip():
            try:
                eslint_output = json.loads(result.stdout)
                for file_result in eslint_output:
                    file_path = file_result.get("filePath", "")
                    for msg in file_result.get("messages", []):
                        severity_map = {
                            2: Severity.ERROR,
                            1: Severity.WARNING,
                        }
                        severity = severity_map.get(msg.get("severity", 1), Severity.WARNING)

                        issues.append(
                            Issue(
                                file=file_path,
                                line=msg.get("line", 0),
                                column=msg.get("column", 0),
                                code=msg.get("ruleId") or "eslint",
                                message=msg.get("message", ""),
                                severity=severity,
                                source="eslint",
                                suggestion=msg.get("fix", {}).get("text") if msg.get("fix") else None,
                                end_line=msg.get("endLine"),
                                end_column=msg.get("endColumn"),
                            )
                        )
            except json.JSONDecodeError:
                pass

        return CheckResult(issues=issues, checks_run=["eslint"])

    def _run_prettier(self, paths: list[str], fix: bool = False) -> CheckResult:
        """Run Prettier format check."""
        prettier = self._find_executable("prettier")

        if not prettier:
            return CheckResult(
                issues=[
                    Issue(
                        file="",
                        line=0,
                        column=0,
                        code="TOOL-NOT-FOUND",
                        message="prettier not found. Install with: npm install -D prettier",
                        severity=Severity.WARNING,
                        source="prettier",
                    )
                ],
                checks_run=["prettier"],
            )

        if fix:
            cmd = [prettier, "--write"]
        else:
            cmd = [prettier, "--check"]

        # Add file extensions
        cmd.extend(paths)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return CheckResult(
                issues=[
                    Issue(
                        file="",
                        line=0,
                        column=0,
                        code="TIMEOUT",
                        message="Prettier timed out after 120 seconds",
                        severity=Severity.ERROR,
                        source="prettier",
                    )
                ],
                checks_run=["prettier"],
            )
        except FileNotFoundError:
            return CheckResult(
                issues=[
                    Issue(
                        file="",
                        line=0,
                        column=0,
                        code="TOOL-NOT-FOUND",
                        message="prettier not found. Install with: npm install -D prettier",
                        severity=Severity.WARNING,
                        source="prettier",
                    )
                ],
                checks_run=["prettier"],
            )

        issues = []
        if result.returncode != 0 and not fix:
            # Parse stderr for files that would be reformatted
            # Prettier outputs: "Checking formatting...\n[warn] file.ts\n..."
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line.startswith("[warn]"):
                    file_path = line[6:].strip()
                    issues.append(
                        Issue(
                            file=file_path,
                            line=1,
                            column=1,
                            code="FORMAT",
                            message="File would be reformatted",
                            severity=Severity.WARNING,
                            source="prettier",
                            suggestion="Run with --fix to auto-format",
                        )
                    )
                elif line and not line.startswith("Checking") and Path(line).suffix in self.ALL_EXTENSIONS:
                    # Sometimes prettier just outputs the filename
                    issues.append(
                        Issue(
                            file=line,
                            line=1,
                            column=1,
                            code="FORMAT",
                            message="File would be reformatted",
                            severity=Severity.WARNING,
                            source="prettier",
                            suggestion="Run with --fix to auto-format",
                        )
                    )

        return CheckResult(issues=issues, checks_run=["prettier"])

    def _run_tsc(self, paths: list[str]) -> CheckResult:
        """Run TypeScript type checking."""
        # Only run on TypeScript files or if project has tsconfig
        has_ts_files = any(Path(p).suffix in self.TS_EXTENSIONS for p in paths if Path(p).is_file())

        if not has_ts_files and not has_typescript_config(self.project_root):
            return CheckResult(checks_run=["tsc"])

        tsc = self._find_executable("tsc")

        if not tsc:
            return CheckResult(
                issues=[
                    Issue(
                        file="",
                        line=0,
                        column=0,
                        code="TOOL-NOT-FOUND",
                        message="tsc not found. Install with: npm install -D typescript",
                        severity=Severity.WARNING,
                        source="tsc",
                    )
                ],
                checks_run=["tsc"],
            )

        # Use --noEmit to just check types without generating output
        cmd = [tsc, "--noEmit", "--pretty", "false"]

        # If project has tsconfig, use it
        if self.project_root and has_typescript_config(self.project_root):
            cmd.extend(["--project", str(self.project_root / "tsconfig.json")])
        else:
            # Basic config for checking
            cmd.extend(["--allowJs", "--checkJs", "--strict"])
            cmd.extend(paths)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return CheckResult(
                issues=[
                    Issue(
                        file="",
                        line=0,
                        column=0,
                        code="TIMEOUT",
                        message="TypeScript compiler timed out after 120 seconds",
                        severity=Severity.ERROR,
                        source="tsc",
                    )
                ],
                checks_run=["tsc"],
            )
        except FileNotFoundError:
            return CheckResult(
                issues=[
                    Issue(
                        file="",
                        line=0,
                        column=0,
                        code="TOOL-NOT-FOUND",
                        message="tsc not found. Install with: npm install -D typescript",
                        severity=Severity.WARNING,
                        source="tsc",
                    )
                ],
                checks_run=["tsc"],
            )

        issues = []
        # Parse tsc output: file(line,col): error TSxxxx: message
        tsc_pattern = re.compile(r"(.+?)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s+(.+)")

        for line in result.stdout.split("\n"):
            match = tsc_pattern.match(line.strip())
            if match:
                file_path, line_num, col, severity_str, code, message = match.groups()
                severity = Severity.ERROR if severity_str == "error" else Severity.WARNING

                issues.append(
                    Issue(
                        file=file_path,
                        line=int(line_num),
                        column=int(col),
                        code=code,
                        message=message,
                        severity=severity,
                        source="tsc",
                    )
                )

        return CheckResult(issues=issues, checks_run=["tsc"])

    def _run_stub_check(self, paths: list[str]) -> CheckResult:
        """Check for TODOs, stubs, and placeholder code."""
        issues = []

        for path_str in paths:
            path = Path(path_str)
            if path.is_file() and path.suffix in self.ALL_EXTENSIONS:
                issues.extend(self._check_file_for_stubs(path))
            elif path.is_dir():
                for ext in self.ALL_EXTENSIONS:
                    for ts_file in path.rglob(f"*{ext}"):
                        if self._should_exclude(ts_file):
                            continue
                        issues.extend(self._check_file_for_stubs(ts_file))

        return CheckResult(issues=issues, checks_run=["stub-check"])

    def _should_exclude(self, path: Path) -> bool:
        """Check if path matches any exclude pattern."""
        path_str = str(path)
        for pattern in self.config.exclude_patterns:
            if pattern.endswith("/**"):
                dir_pattern = pattern[:-3]
                if dir_pattern in path_str:
                    return True
            elif pattern.startswith("*."):
                if path.suffix == pattern[1:]:
                    return True
            elif pattern in path_str:
                return True
        return False

    def _check_file_for_stubs(self, file_path: Path) -> list[Issue]:
        """Check a single file for stub patterns."""
        issues = []

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")
        except Exception:
            return issues

        for line_num, line in enumerate(lines, 1):
            for pattern, description in self.config.stub_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check for legitimate patterns
                    if self._is_legitimate_pattern(file_path, line_num, line, lines):
                        continue

                    issues.append(
                        Issue(
                            file=str(file_path),
                            line=line_num,
                            column=1,
                            code="STUB",
                            message=f"{description}: {line.strip()[:60]}",
                            severity=Severity.WARNING,
                            source="stub-check",
                            suggestion="Remove placeholder or implement functionality",
                        )
                    )

        return issues

    def _is_legitimate_pattern(self, file_path: Path, line_num: int, line: str, lines: list[str]) -> bool:
        """Check if a stub pattern is actually legitimate."""
        file_str = str(file_path).lower()

        # Test files are allowed to have mocks and stubs
        if "test" in file_str or "spec" in file_str or "__tests__" in file_str:
            return True

        # Config files often have console.log for debugging
        if file_path.name in ("jest.config.js", "webpack.config.js", "vite.config.ts"):
            return True

        # Type definition files may have 'any' legitimately
        if file_path.suffix == ".d.ts":
            return True

        # Console in scripts/tools directories
        if "/scripts/" in file_str or "/tools/" in file_str:
            if "console." in line:
                return True

        return False


# Convenience functions for direct use
def check_files(paths: list[str | Path], config: CheckConfig | None = None, fix: bool = False) -> CheckResult:
    """Check TypeScript/JavaScript files for issues.

    Args:
        paths: Files or directories to check
        config: Optional config (defaults loaded from package.json)
        fix: If True, auto-fix issues where possible

    Returns:
        CheckResult with issues found
    """
    checker = TypeScriptChecker(config)
    return checker.check_files(paths, fix=fix)


def check_content(content: str, filename: str = "stdin.ts", config: CheckConfig | None = None) -> CheckResult:
    """Check TypeScript/JavaScript content string.

    Args:
        content: Source code as string
        filename: Virtual filename for error reporting
        config: Optional config

    Returns:
        CheckResult with issues found
    """
    checker = TypeScriptChecker(config)
    return checker.check_content(content, filename)
