# amplifier-bundle-ts-dev

Comprehensive TypeScript/JavaScript development tools for [Amplifier](https://github.com/microsoft/amplifier) - the "TypeScript/JavaScript Development Home" in the Amplifier ecosystem.

## What's Included

| Component | Description |
|-----------|-------------|
| **Tool Module** | `ts_check` - agent-callable tool for quality checks |
| **Hook Module** | Automatic checking on file write/edit events |
| **LSP Integration** | Includes lsp-typescript for code intelligence |
| **Shared Library** | Core checking logic used by tool and hook modules |

### Expert Agents

| Agent | Expertise | Use For |
|-------|-----------|---------|
| **ts-dev** | General TypeScript/JavaScript | Code quality, type errors, imports |
| **react-dev** | React & hooks | Component patterns, re-renders, state management |
| **nextjs-dev** | Next.js App Router | SSR/SSG, hydration, caching, Server Components |
| **node-dev** | Node.js backend | Async patterns, security, APIs, error handling |

## Quick Start

### As Amplifier Bundle

```yaml
# In your bundle.yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-ts-dev@main
```

This gives you:
- TypeScript/JavaScript LSP (code intelligence)
- TypeScript/JavaScript quality checks (tool + hook)
- All four expert agents (ts-dev, react-dev, nextjs-dev, node-dev)

## Checks Performed

| Check | Tool | What It Catches |
|-------|------|-----------------|
| **Lint** | ESLint | Bugs, imports, style, React rules |
| **Format** | Prettier | Code formatting |
| **Types** | tsc | TypeScript type errors |
| **Stubs** | custom | TODOs, console.log, 'any' types, placeholders |

## Agent Usage

### General TypeScript/JavaScript (`ts-dev`)

```
> @ts-dev Check src/utils.ts for issues
> @ts-dev Help me fix these type errors
```

### React Development (`react-dev`)

```
> @react-dev Why does this component keep re-rendering?
> @react-dev Extract this logic into a custom hook
> @react-dev Review this component for hooks best practices
```

**Specialties:**
- Hooks patterns and rules
- Re-render debugging
- State management guidance
- Component composition
- Testing with React Testing Library

### Next.js Development (`nextjs-dev`)

```
> @nextjs-dev I'm getting a hydration mismatch on this page
> @nextjs-dev What caching strategy should I use for this API?
> @nextjs-dev Help me migrate this pages/ route to app/ router
```

**Specialties:**
- App Router file conventions
- Server Components vs Client Components
- Data fetching and caching strategies
- Hydration error diagnosis
- SSR/SSG/ISR guidance

### Node.js Backend (`node-dev`)

```
> @node-dev Review this Express app for security issues
> @node-dev Help me design proper error handling
> @node-dev Why is this async function not working correctly?
```

**Specialties:**
- Async patterns and event loop
- Security (OWASP Top 10)
- Error handling middleware
- API design (REST)
- Performance optimization

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
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   ts-dev    │  │  react-dev  │  │ nextjs-dev  │  │  node-dev   │    │
│  │   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │                │           │
│         └────────────────┴────────┬───────┴────────────────┘           │
│                                   │                                     │
│         ┌─────────────────────────┼─────────────────────────┐          │
│         │                         │                         │          │
│  ┌──────┴──────┐  ┌───────────────┴───────────────┐  ┌──────┴──────┐   │
│  │ Tool Module │  │        SHARED CORE            │  │ Hook Module │   │
│  │  ts_check   │  │ checker.py, config.py, models │  │ auto-check  │   │
│  └─────────────┘  └───────────────────────────────┘  └─────────────┘   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  INCLUDES: lsp-typescript (code intelligence)                           │
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

## Context Files

Each agent loads specialized knowledge:

| File | Content |
|------|---------|
| `TS_BEST_PRACTICES.md` | TypeScript/JavaScript development philosophy |
| `REACT_PATTERNS.md` | React hooks, components, state, performance |
| `NEXTJS_PATTERNS.md` | App Router, Server Components, caching |
| `NODEJS_PATTERNS.md` | Async, error handling, security, APIs |

## Development Philosophy

This bundle embodies **type-safe pragmatism**:

1. **Type safety as a feature** - Use TypeScript's type system to catch bugs early
2. **Explicit over implicit** - Clear code beats clever code
3. **Modern patterns first** - ES modules, async/await, optional chaining
4. **Framework-aware** - Specialized guidance for React, Next.js, Node.js
5. **Clean imports** - Organized, no circular dependencies

See [TS_BEST_PRACTICES.md](context/TS_BEST_PRACTICES.md) for the full guide.

## Future Roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| MVP | ESLint, Prettier, tsc, stubs | ✅ Done |
| Agents | Framework-specific experts | ✅ Done |
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
