"""Amplifier TypeScript/JavaScript Development Bundle.

Provides comprehensive TS/JS development tools including:
- ESLint for linting
- Prettier for formatting
- TypeScript compiler for type checking
- Stub detection for incomplete code

Usage:
    from amplifier_bundle_ts_dev import check_files, check_content, CheckConfig

    # Check files
    result = check_files(["src/"])

    # Check content
    result = check_content("const x: any = 1;")

    # With custom config
    config = CheckConfig(enable_prettier=False)
    result = check_files(["src/"], config=config)
"""

from .checker import TypeScriptChecker
from .checker import check_content
from .checker import check_files
from .config import find_project_root
from .config import has_eslint_config
from .config import has_prettier_config
from .config import has_typescript_config
from .config import load_config
from .models import CheckConfig
from .models import CheckResult
from .models import Issue
from .models import Severity

__all__ = [
    # Main API
    "check_files",
    "check_content",
    "TypeScriptChecker",
    # Config
    "CheckConfig",
    "load_config",
    "find_project_root",
    "has_eslint_config",
    "has_prettier_config",
    "has_typescript_config",
    # Models
    "CheckResult",
    "Issue",
    "Severity",
]

__version__ = "0.1.0"
