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

Project configuration cannot enable executable checks. ESLint, Prettier, and `tsc`
are disabled unless the process that launches Amplifier trusts the workspace; the
built-in stub check remains available. Enabling external tools permits project-local
binaries and project configuration/plugins to execute, so only opt in for workspaces
you trust.

The host is the process launcher: the person, script, service, or application that
starts Amplifier. To trust the current physical directory, the launcher sets this
environment variable when starting Amplifier:

```bash
AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT="$(pwd -P)" amplifier
```

The value must be an existing absolute directory that contains the session working
directory. It is a process-start setting, not a repository-managed setting. Legacy
module configuration fields `allow_external_tools` and `workspace_root` are ignored,
so project settings and bundle configuration cannot grant this permission.

Hook module configuration:

```yaml
hooks:
  - module: hooks-ts-check
    config:
      enabled: true
      file_patterns: ["*.ts", "*.tsx", "*.js", "*.jsx"]
      report_level: warning
      auto_inject: true
      checks: [stubs]
```

## Hook Behavior

When enabled, the hook automatically runs checks after TypeScript/JavaScript file edits:

1. You write/edit a `.ts`, `.tsx`, `.js`, or `.jsx` file
2. Hook triggers the built-in stub check only
3. Issues are injected into agent context
4. Agent is aware of problems immediately

The default does not execute project-local tools or configuration. A host that starts
Amplifier with `AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT` set as above can opt in to
ESLint, Prettier, or `tsc` by selecting them in the hook module configuration. For
example, `checks: [eslint, prettier, tsc, stubs]` restores all checks. Only enable
executable checks for workspaces you trust.

This creates a tight feedback loop for stub issues without running executables
on every edit. Trusted hosts can extend it with executable checks when needed.

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

After installation, the process that starts Amplifier must set
`AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT` to the existing absolute workspace
directory, for example:

```bash
AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT="$(pwd -P)" amplifier
```

The variable is read only from the host process environment at module construction.
It must contain the session working directory; otherwise executable checks stay
disabled and the session directory remains the workspace boundary. It is not a
repository-managed setting. `allow_external_tools` and `workspace_root` in module
configuration are ignored, so no project-level setting can grant executable-check
permission. File operands are canonicalized to the workspace, and paths beginning
with `-` or escaping the workspace are rejected.

Standard npm `.bin` symlinks to sibling packages inside the project's `node_modules`
are supported; targets outside that installation tree are not selected as local
tools. If no permitted local tool exists, trusted host `PATH` lookup remains the
fallback. Opting in trusts executable code, plugins and project configuration; these
checks are not a sandbox for ESLint, Prettier or TypeScript.

Both mounted modules resolve relative operands and run subprocesses from the
host's `session.working_dir` capability (falling back to process cwd at mount
time). Their authorization boundary defaults to that directory, **not** an
ancestor inferred from `package.json`. A launcher can authorize a containing
workspace only with `AMPLIFIER_TS_DEV_TRUSTED_WORKSPACE_ROOT`; the session working
directory must be inside that root. Tool inputs, project settings, and bundle
configuration cannot override either value. The Python API accepts separate
`working_dir` and `workspace_root` keyword arguments for explicit caller-owned use.

Package discovery cannot enlarge the authorization boundary. Without a wider
host-supplied root, parent package configuration and parent `node_modules` are
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
