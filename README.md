# amplifier-bundle-ts-dev

Comprehensive TypeScript/JavaScript development tools for [Amplifier](https://github.com/microsoft/amplifier) - the "TypeScript/JavaScript Development Home" in the Amplifier ecosystem.

## What's Included

| Component | Description |
|-----------|-------------|
| **Tool Module** | `ts_check` - agent-callable tool for quality checks |
| **Hook Module** | Automatic checking on file write/edit events |
| **Agent** | `ts-dev` - expert TypeScript/JavaScript developer agent |
| **LSP Integration** | Includes lsp-typescript for code intelligence |
| **Shared Library** | Core checking logic used by tool and hook modules |

## Quick Start

### As Amplifier Bundle

```yaml
# In your bundle.yaml
includes:
  - bundle: git+https://github.com/robotdad/amplifier-bundle-ts-dev@main
```

This gives you:
- Foundation tools and agents
- TypeScript/JavaScript LSP (code intelligence)
- TypeScript/JavaScript quality checks (tool + hook)
- TypeScript/JavaScript development expert agent

## Checks Performed

| Check | Tool | What It Catches |
|-------|------|-----------------|
| **Lint** | ESLint | Bugs, imports, style, React rules |
| **Format** | Prettier | Code formatting |
| **Types** | tsc | TypeScript type errors |
| **Stubs** | custom | TODOs, console.log, 'any' types, placeholders |

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

Hook configuration:

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

## Agent Usage

The `ts-dev` agent is an expert TypeScript/JavaScript developer that wields both quality checks and LSP tools:

```
# Within Amplifier
> @ts-dev Check src/auth.ts for issues

# The agent will:
# 1. Run ts_check on the file
# 2. Use LSP to understand code structure
# 3. Provide actionable recommendations
```

**Agent capabilities:**
- Code quality analysis
- Type error diagnosis
- Import organization
- Code structure understanding (via LSP)
- React component analysis
- Best practices guidance

## Hook Behavior

When enabled, the hook automatically runs checks after TypeScript/JavaScript file edits:

1. You write/edit a `.ts`, `.tsx`, `.js`, or `.jsx` file
2. Hook triggers and runs ESLint, Prettier, and tsc checks
3. Issues are injected into agent context
4. Agent is aware of problems immediately

This creates a tight feedback loop - issues are caught as you work, not at the end.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    amplifier-bundle-ts-dev                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────────────┐          │
│  │  Tool   │  │  Hook   │  │   CLI   │  │     ts-dev        │          │
│  │ Module  │  │ Module  │  │(future) │  │      Agent        │          │
│  └────┬────┘  └────┬────┘  └────┬────┘  └─────────┬─────────┘          │
│       │            │            │                  │                    │
│       └────────────┴─────┬──────┴──────────────────┘                    │
│                          │                                              │
│                   ┌──────┴──────┐                                       │
│                   │ SHARED CORE │                                       │
│                   │ checker.py  │                                       │
│                   └─────────────┘                                       │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  INCLUDES: lsp-typescript                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tool Prerequisites

The checker uses these tools (install as needed):

```bash
# Local installation (recommended)
npm install -D eslint prettier typescript

# For React projects
npm install -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin \
  eslint-plugin-react eslint-plugin-react-hooks

# Global installation
npm install -g eslint prettier typescript
```

## Development Philosophy

This bundle embodies **type-safe pragmatism**:

1. **Type safety as a feature** - Use TypeScript's type system to catch bugs early
2. **Explicit over implicit** - Clear code beats clever code
3. **Modern patterns first** - ES modules, async/await, optional chaining
4. **React best practices** - Functional components, hooks, proper typing
5. **Clean imports** - Organized, no circular dependencies

See [TS_BEST_PRACTICES.md](context/TS_BEST_PRACTICES.md) for the full guide.

## Future Roadmap

This bundle is the "TypeScript/JavaScript Development Home" - a collection point for TS/JS-specific capabilities:

| Phase | Feature | Status |
|-------|---------|--------|
| MVP | ESLint, Prettier, tsc, stubs | ✅ Done |
| Testing | Jest/Vitest integration | 🔮 Planned |
| Bundling | Webpack/Vite analysis | 🔮 Planned |
| Dependencies | npm-audit, outdated checks | 🔮 Planned |
| Performance | Bundle size analysis | 🔮 Planned |

## Contributing

Contributions welcome! Please ensure:
- Code passes all quality checks
- New features include tests
- Documentation is updated

## License

MIT License - see [LICENSE](LICENSE) for details.
