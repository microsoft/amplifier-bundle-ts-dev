# TypeScript/JavaScript Development Tools

This bundle provides comprehensive TypeScript/JavaScript development capabilities for Amplifier.

## Available Tools

### ts_check

Run code quality checks on TypeScript/JavaScript files or code content.

```
ts_check(paths=["src/"])           # Check a directory
ts_check(paths=["src/main.ts"])    # Check a specific file
ts_check(content="const x: any = 1;")  # Check code string
ts_check(paths=["src/"], fix=true)  # Auto-fix issues
```

**Checks performed:**
- **ESLint**: Linting rules (bugs, style, React, imports)
- **Prettier**: Code formatting
- **tsc**: TypeScript type checking (--noEmit)
- **stub detection**: TODOs, console statements, 'any' types, placeholders

### LSP Tools (via lsp-typescript)

Semantic code intelligence for TypeScript/JavaScript:

| Tool | Use For |
|------|---------|
| `hover` | Get type info and JSDoc |
| `goToDefinition` | Find where a symbol is defined |
| `findReferences` | Find all usages of a symbol |
| `incomingCalls` | What calls this function? |
| `outgoingCalls` | What does this function call? |
| `goToImplementation` | Find interface implementations |

## Automatic Checking Hook

When enabled, TypeScript/JavaScript files are automatically checked after write/edit operations.

**Behavior:**
- Triggers on `write_file`, `edit_file`, and similar tools
- Checks `.ts`, `.tsx`, `.js`, `.jsx`, `.mts`, `.mjs`, `.cts`, `.cjs` files
- Runs ESLint, Prettier, and tsc checks
- Injects issues into agent context for awareness

**Configuration** (in `package.json`):
```json
{
  "amplifier-ts-dev": {
    "hook": {
      "enabled": true,
      "file_patterns": ["*.ts", "*.tsx", "*.js", "*.jsx"],
      "report_level": "warning",
      "auto_inject": true
    }
  }
}
```

## Tool Installation

The checker looks for tools in this order:
1. Local `node_modules/.bin/` (preferred)
2. Global installation

Install the required tools:
```bash
# Local (recommended)
npm install -D eslint prettier typescript

# Global
npm install -g eslint prettier typescript
```

### ESLint Setup

For projects without ESLint config, basic rules are applied. For best results, create a config:

```bash
# Initialize ESLint
npm init @eslint/config

# Or for React projects
npm install -D eslint @eslint/js @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint-plugin-react eslint-plugin-react-hooks
```

### Prettier Setup

Create `.prettierrc` for consistent formatting:
```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5"
}
```

### TypeScript Setup

Ensure `tsconfig.json` exists for type checking:
```bash
npx tsc --init
```

## Configuration

Configure via `package.json`:

```json
{
  "amplifier-ts-dev": {
    "enable_eslint": true,
    "enable_prettier": true,
    "enable_tsc": true,
    "enable_stub_check": true,
    "exclude_patterns": [
      "node_modules/**",
      "dist/**",
      "build/**",
      ".next/**"
    ]
  }
}
```

## Best Practices

See @ts-dev:context/TS_BEST_PRACTICES.md for the full development philosophy.

**Key points:**
1. Run `ts_check` after writing TypeScript/JavaScript code
2. Fix issues immediately - don't accumulate debt
3. Use LSP tools to understand code before modifying
4. Avoid `any` - use proper types
5. Keep imports organized
