"""Data models for TypeScript/JavaScript code checking."""

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any


class Severity(Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    """A single code quality issue."""

    file: str
    line: int
    column: int
    code: str
    message: str
    severity: Severity
    source: str  # eslint, prettier, tsc, stub-check
    suggestion: str | None = None
    end_line: int | None = None
    end_column: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "suggestion": self.suggestion,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }


@dataclass
class CheckResult:
    """Result of running code checks."""

    issues: list[Issue] = field(default_factory=list)
    files_checked: int = 0
    checks_run: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if no errors (warnings are OK)."""
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def clean(self) -> bool:
        """True if no issues at all."""
        return len(self.issues) == 0

    def merge(self, other: "CheckResult") -> "CheckResult":
        """Merge another result into this one."""
        return CheckResult(
            issues=self.issues + other.issues,
            files_checked=max(self.files_checked, other.files_checked),
            checks_run=list(set(self.checks_run + other.checks_run)),
        )

    def to_tool_output(self) -> dict[str, Any]:
        """Format for tool output."""
        # Group issues by severity
        errors = [i for i in self.issues if i.severity == Severity.ERROR]
        warnings = [i for i in self.issues if i.severity == Severity.WARNING]
        infos = [i for i in self.issues if i.severity == Severity.INFO]

        summary_parts = []
        if errors:
            summary_parts.append(f"{len(errors)} error(s)")
        if warnings:
            summary_parts.append(f"{len(warnings)} warning(s)")
        if infos:
            summary_parts.append(f"{len(infos)} info(s)")

        if not summary_parts:
            summary = f"All checks passed. {self.files_checked} file(s) checked."
        else:
            summary = f"Found {', '.join(summary_parts)} in {self.files_checked} file(s)."

        return {
            "success": self.success,
            "clean": self.clean,
            "summary": summary,
            "files_checked": self.files_checked,
            "checks_run": self.checks_run,
            "issues": [i.to_dict() for i in self.issues],
            "error_count": len(errors),
            "warning_count": len(warnings),
            "info_count": len(infos),
        }

    def to_hook_output(self) -> dict[str, Any]:
        """Format for hook injection."""
        issues_text = "\n".join(f"  {i.file}:{i.line}:{i.column}: [{i.code}] {i.message}" for i in self.issues)
        return {
            "summary": f"Found {len(self.issues)} issue(s)",
            "issues_text": issues_text,
            "has_errors": not self.success,
        }


@dataclass
class CheckConfig:
    """Configuration for the checker."""

    enable_eslint: bool = True
    enable_prettier: bool = True
    enable_tsc: bool = True
    enable_stub_check: bool = True

    # Paths to exclude
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "node_modules/**",
            "dist/**",
            "build/**",
            ".next/**",
            "coverage/**",
            "*.min.js",
        ]
    )

    # Stub patterns to detect (pattern, description)
    stub_patterns: list[tuple[str, str]] = field(
        default_factory=lambda: [
            (r"//\s*TODO:", "TODO comment"),
            (r"//\s*FIXME:", "FIXME comment"),
            (r"//\s*HACK:", "HACK comment"),
            (r"//\s*XXX:", "XXX comment"),
            (
                r'throw\s+new\s+Error\s*\(\s*["\']not\s+implemented',
                "Not implemented error",
            ),
            (r'throw\s+new\s+Error\s*\(\s*["\']TODO', "TODO error"),
            (r"console\.(log|debug|info)\s*\(", "Console statement (debugging)"),
            (r":\s*any\s*[;,\)\}=]", "Explicit 'any' type"),
            (r"as\s+any\s*[;,\)\}]", "Type assertion to 'any'"),
        ]
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckConfig":
        """Create config from dictionary, using defaults for missing values."""
        return cls(
            enable_eslint=data.get("enable_eslint", True),
            enable_prettier=data.get("enable_prettier", True),
            enable_tsc=data.get("enable_tsc", True),
            enable_stub_check=data.get("enable_stub_check", True),
            exclude_patterns=data.get("exclude_patterns", cls().exclude_patterns),
        )
