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
|-------|-----------|---------
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

The `amplifier-ts-dev` section in `package.json` cannot enable executable checks.
ESLint, Prettier, and `tsc` are disabled unless module configuration sets
`allow_external_tools: true`; the
built-in stub check remains available. Module configuration is supplied through the
application's normal configuration loading. This is a configuration opt-in, not a
persisted trusted workspace, and requires no launch environment setting.

For the tool module:

```yaml
tools:
  - module: tool-ts-check
    config:
      allow_external_tools: true
```

Hook module configuration:

```yaml
hooks:
  - module: hooks-ts-check
    config:
      allow_external_tools: true
      checks: [eslint, prettier, tsc, stubs]
```

## Hook Behavior

When enabled, the hook automatically runs checks after TypeScript/JavaScript file edits:

1. You write/edit a `.ts`, `.tsx`, `.js`, or `.jsx` file
2. Hook triggers the built-in stub check only
3. Issues are injected into agent context
4. Agent is aware of problems immediately

The default does not execute project-local tools or configuration. Set
`allow_external_tools: true` and select executable checks in the hook module
configuration to opt in. For example, `checks: [eslint, prettier, tsc, stubs]`
restores all checks. Enabling external tools permits project-local binaries and
project configuration/plugins to execute, so only opt in for workspaces you trust.

This creates a tight feedback loop for stub issues without running executables
on every edit. Module configuration can extend it with executable checks when needed.

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

After installation, set `allow_external_tools: true` in the tool or hook module
configuration to run executable checks. Package configuration cannot grant this
permission. File operands are canonicalized to the workspace, and paths beginning
with `-` or escaping the workspace are rejected.

The opt-in must be a boolean `true`, not a string or integer. Standard npm `.bin`
symlinks to sibling packages inside the project's `node_modules` are supported;
targets outside that installation tree are not selected as local tools. If no
permitted local tool exists, `PATH` lookup remains the fallback. Opting in trusts
executable code, plugins and project configuration; these checks are not a sandbox
for ESLint, Prettier or TypeScript.

Both mounted modules resolve relative operands and run subprocesses from the
`session.working_dir` capability (falling back to process cwd at mount time). Their
authorization boundary defaults to that directory, **not** an ancestor inferred from
`package.json`. Module configuration can set an optional absolute `workspace_root`
to use a containing workspace; the session working directory must be inside that
root. Tool inputs and `package.json` cannot override either value. The Python API
accepts separate `working_dir` and `workspace_root` keyword arguments with the same
defaults.

Package discovery cannot enlarge the authorization boundary. Without a wider
module-configured root, parent package configuration and parent `node_modules` are
not used. Built-in recursive scanning revalidates discovered files before reading:
outside symlink targets produce `INVALID-PATH`, while in-root symlinks still work.
This is canonical-path confinement, not protection against concurrent filesystem
replacement between validation and opening.

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
| MVP | ESLint, Prettier, tsc, stubs | Done |
| Agents | Framework-specific experts | Done |
| Testing | Jest/Vitest integration | Planned |
| Bundling | Webpack/Vite analysis | Planned |
| Dependencies | npm-audit, outdated checks | Planned |
| Performance | Bundle size analysis | Planned |

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
