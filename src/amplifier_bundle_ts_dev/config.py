"""Configuration loading for ts-dev bundle."""

import json
from pathlib import Path
from typing import Any

from .models import CheckConfig


def find_project_root(start_path: Path | None = None) -> Path | None:
    """Find project root by looking for package.json or tsconfig.json."""
    current = start_path or Path.cwd()

    for path in [current] + list(current.parents):
        if (path / "package.json").exists():
            return path
        if (path / "tsconfig.json").exists():
            return path

    return None


def load_config(project_root: Path | None = None) -> CheckConfig:
    """Load configuration from package.json or use defaults.

    Looks for configuration in package.json under "amplifier-ts-dev" key.
    Falls back to sensible defaults if not found.
    """
    if project_root is None:
        project_root = find_project_root()

    if project_root is None:
        return CheckConfig()

    package_json = project_root / "package.json"
    if not package_json.exists():
        return CheckConfig()

    try:
        with open(package_json) as f:
            pkg: dict[str, Any] = json.load(f)

        config_data: dict[str, Any] = pkg.get("amplifier-ts-dev", {})
        return CheckConfig.from_dict(config_data)
    except (json.JSONDecodeError, OSError):
        return CheckConfig()


def has_eslint_config(project_root: Path | None = None) -> bool:
    """Check if project has ESLint configuration."""
    if project_root is None:
        project_root = find_project_root() or Path.cwd()

    eslint_configs = [
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.cjs",
        ".eslintrc.json",
        ".eslintrc.yaml",
        ".eslintrc.yml",
        "eslint.config.js",
        "eslint.config.mjs",
        "eslint.config.cjs",
    ]

    for config in eslint_configs:
        if (project_root / config).exists():
            return True

    # Check package.json for eslintConfig
    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as f:
                pkg: dict[str, Any] = json.load(f)
            if "eslintConfig" in pkg:
                return True
        except (json.JSONDecodeError, OSError):
            pass

    return False


def has_prettier_config(project_root: Path | None = None) -> bool:
    """Check if project has Prettier configuration."""
    if project_root is None:
        project_root = find_project_root() or Path.cwd()

    prettier_configs = [
        ".prettierrc",
        ".prettierrc.js",
        ".prettierrc.cjs",
        ".prettierrc.json",
        ".prettierrc.yaml",
        ".prettierrc.yml",
        ".prettierrc.toml",
        "prettier.config.js",
        "prettier.config.cjs",
    ]

    for config in prettier_configs:
        if (project_root / config).exists():
            return True

    # Check package.json for prettier
    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as f:
                pkg: dict[str, Any] = json.load(f)
            if "prettier" in pkg:
                return True
        except (json.JSONDecodeError, OSError):
            pass

    return False


def has_typescript_config(project_root: Path | None = None) -> bool:
    """Check if project has TypeScript configuration."""
    if project_root is None:
        project_root = find_project_root() or Path.cwd()

    return (project_root / "tsconfig.json").exists()
