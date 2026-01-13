# Agent & Bundle Best Practices

Learnings extracted from debugging the ts-dev bundle with exp-delegation pattern.

## Key Insight: Sub-Agents Don't Inherit Bundle Tools

**This is the most important thing to understand.**

When an agent is spawned as a sub-session (via the `task` tool), it creates a NEW session with ONLY the tools declared in the agent's markdown file. It does **NOT** inherit tools from the parent bundle.

```
Parent Session (has bundle tools)
    │
    └─► task tool spawns agent
            │
            └─► New Sub-Session (ONLY has agent-declared tools)
```

This is why foundation agents like `foundation:explorer` declare their tools directly:

```yaml
# foundation:explorer agent
tools:
  - module: tool-filesystem
    source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
  - module: tool-search
    source: git+https://github.com/microsoft/amplifier-module-tool-search@main
  - module: tool-lsp
    source: ...
```

---

## Bundle Creation Best Practices

### 1. Understand the Two Tool Contexts

| Context | What Gets Tools | How |
|---------|-----------------|-----|
| **Bundle tools** | The ROOT session | Defined in `bundle.yaml` or behavior YAML |
| **Agent tools** | SUB-sessions when agent is spawned | Defined in agent `.md` file frontmatter |

### 2. Bundle Structure

```
my-bundle/
├── bundle.yaml          # Main entry point
├── behaviors/
│   └── my-behavior.yaml # Reusable capability sets
├── agents/
│   ├── agent-one.md     # Agent with its own tools
│   └── agent-two.md
├── context/
│   └── instructions.md  # Context files for agents
└── docs/
    └── README.md
```

### 3. Including Other Bundles

```yaml
# bundle.yaml
includes:
  # Include LSP support (brings tool-lsp with language config)
  - bundle: git+https://github.com/microsoft/amplifier-bundle-lsp-typescript@main
  
  # Include your behavior
  - bundle: my-bundle:behaviors/main
```

**Warning**: Include order matters. Later includes can override earlier ones.

---

## Agent Definition Best Practices

### 1. Always Declare Tools Agents Need

If your agent needs to read files, search, or use LSP - declare those tools:

```yaml
---
meta:
  name: my-agent
  description: "Description with examples..."

# Tools this agent needs when spawned as sub-session
tools:
  - module: tool-filesystem
    source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
  - module: tool-search
    source: git+https://github.com/microsoft/amplifier-module-tool-search@main
---

# Agent Instructions

Your agent instructions here...
```

### 2. Include Full Config for Tools That Need It

LSP tools need language configuration. Don't just reference the module - include the config:

```yaml
tools:
  - module: tool-lsp
    source: git+https://github.com/microsoft/amplifier-bundle-lsp@main#subdirectory=modules/tool-lsp
    config:
      languages:
        typescript:
          extensions: [".ts", ".tsx", ".mts", ".cts"]
          workspace_markers: ["tsconfig.json", "package.json", ".git"]
          server:
            command: ["typescript-language-server", "--stdio"]
            install_check: ["typescript-language-server", "--version"]
            install_hint: "Install with: npm install -g typescript-language-server typescript"
```

### 3. Agent Description Format

Include examples in the description for better delegation:

```yaml
meta:
  name: react-dev
  description: |
    Expert React developer specializing in hooks and component patterns.
    
    <example>
    user: 'Why does this component keep re-rendering?'
    assistant: 'I'll use ts-dev:react-dev to diagnose the re-render issue.'
    <commentary>Re-render debugging is react-dev's specialty.</commentary>
    </example>
```

### 4. Sub-Agents Cannot Spawn Other Agents

This is by design. Sub-agents don't have the `task` tool because:
- They're one-shot sessions
- Infinite agent nesting would be dangerous
- Give agents the tools they need directly instead

---

## Common Pitfalls

### ❌ Pitfall 1: Assuming Tool Inheritance

```yaml
# WRONG: Agent assumes it has bundle's tools
---
meta:
  name: my-agent
  description: "..."
# No tools declared - agent has NOTHING when spawned!
---
```

```yaml
# CORRECT: Agent declares what it needs
---
meta:
  name: my-agent
  description: "..."
tools:
  - module: tool-filesystem
    source: ...
---
```

### ❌ Pitfall 2: Overriding Configured Tools

```yaml
# WRONG: Re-declaring tool-lsp without config overrides the bundle's configured version
tools:
  - module: tool-lsp
    source: git+https://github.com/microsoft/amplifier-bundle-lsp@main#subdirectory=modules/tool-lsp
    # No config! This overrides the bundle's LSP that had language config
```

```yaml
# CORRECT: Include full config or don't re-declare
tools:
  - module: tool-lsp
    source: ...
    config:
      languages:
        typescript: { ... }  # Full config included
```

### ❌ Pitfall 3: Agent Instructions Promise Unavailable Capabilities

If your agent instructions say "use LSP to understand code" but the agent doesn't have LSP tools declared, it will fail. **Audit your agent instructions against declared tools.**

### ❌ Pitfall 4: Expecting Agents to Delegate Further

```markdown
# WRONG: Agent instructions that assume it can spawn other agents
If you need to explore files, use foundation:explorer...
```

```markdown
# CORRECT: Agent has the tools it needs directly
Use the read_file and grep tools to explore the codebase...
```

---

## The Delegation Pattern (exp-delegation)

The `exp-delegation` bundle demonstrates a minimal root session:

```
Root Session (exp-delegation)
├── Tools: tool-todo, tool-task (only!)
├── No file access, no bash, no grep
└── Must delegate everything to agents
    │
    ├─► foundation:file-ops (has tool-filesystem, tool-search)
    ├─► foundation:shell-exec (has tool-bash)
    ├─► foundation:explorer (has filesystem + search + lsp)
    └─► ts-dev:ts-dev (has ts-check + filesystem + search + lsp)
```

**Key principle**: The root session orchestrates, agents do the work.

### When Combining Bundles

When you include both `exp-delegation` and `ts-dev`:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=experiments/delegation-only
  - bundle: git+https://github.com/microsoft/amplifier-bundle-ts-dev@main
```

The ts-dev agents become available alongside foundation agents. Each agent brings its own tools when spawned.

---

## Checklist for New Agents

- [ ] Agent has `meta.name` and `meta.description`
- [ ] Description includes `<example>` blocks for delegation hints
- [ ] `tools:` section declares ALL tools the agent needs
- [ ] Tools that need config (like LSP) have full config included
- [ ] Agent instructions match the tools actually available
- [ ] Agent doesn't assume it can spawn other agents
- [ ] Tested agent works when spawned via `task` tool

---

## Debugging Agent Issues

### "No LSP support configured"
Agent is using tool-lsp without language configuration. Add full config to agent's tools section.

### "Agent spawning capability isn't available"  
Expected behavior. Sub-agents can't spawn other agents. Give the agent the tools it needs directly.

### Agent can't read files
Agent doesn't have `tool-filesystem` declared. Add it to the agent's tools section.

### Agent returns empty response
Check if agent has the tools it needs. Missing tools can cause silent failures.

### Agent works in bundle but not when delegated
Bundle-level tools don't transfer to sub-sessions. Declare tools in agent markdown.
