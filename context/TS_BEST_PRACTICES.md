# TypeScript/JavaScript Development Philosophy

This document outlines the core development principles for TypeScript/JavaScript code in the Amplifier ecosystem.

## Core Philosophy: Type-Safe Pragmatism

We value **type safety without rigidity**, **modern patterns over legacy**, and **explicit code over clever tricks**.

---

## The Six Principles

### 1. Type Safety as a Feature, Not a Burden

TypeScript's type system is your ally. Use it to catch bugs early and document intent.

- **Avoid `any`**: Use `unknown` for truly unknown types, then narrow
- **Prefer inference**: Let TypeScript infer when obvious, annotate at boundaries
- **Use strict mode**: Enable `strict: true` in tsconfig.json
- **Generic when needed**: Use generics for reusable patterns, not everywhere

**Test**: *"Would a new developer understand the types without reading implementation?"*

### 2. Explicit Over Implicit

Code should communicate intent clearly. When TypeScript can't infer, be explicit.

| Implicit (Avoid) | Explicit (Prefer) |
|------------------|-------------------|
| `const data = await fetch(...)` | `const data: UserResponse = await fetch(...)` |
| `function process(x) { ... }` | `function process(x: Input): Output { ... }` |
| `export default` | `export const myFunction` |
| Magic strings | Enums or const objects |

**Key insight**: Function signatures are contracts. Make them clear.

### 3. Modern Patterns First

Use modern JavaScript/TypeScript features. They exist for good reasons.

| Legacy | Modern |
|--------|--------|
| `var` | `const` / `let` |
| `function() {}` | `() => {}` (for callbacks) |
| `.then().catch()` | `async/await` |
| `obj && obj.prop` | `obj?.prop` |
| `value || default` | `value ?? default` |
| `require()` | `import` |

**Exception**: Use `function` declarations for hoisting and named stack traces.

### 4. React Best Practices

For React projects, follow established patterns:

- **Functional components**: Use hooks, not class components
- **Custom hooks**: Extract reusable logic into `use*` functions
- **Props typing**: Define interfaces for all component props
- **State management**: Start with useState, lift up before adding libraries
- **Effect cleanup**: Always return cleanup functions from useEffect

```typescript
// Good: Clear props, typed, functional
interface UserCardProps {
  user: User;
  onSelect?: (user: User) => void;
}

export function UserCard({ user, onSelect }: UserCardProps) {
  const handleClick = useCallback(() => {
    onSelect?.(user);
  }, [user, onSelect]);

  return <div onClick={handleClick}>{user.name}</div>;
}
```

### 5. Import Organization

Imports tell a story about dependencies. Keep them organized.

```typescript
// 1. Node.js built-ins
import { readFile } from 'fs/promises';
import path from 'path';

// 2. External packages
import React, { useState } from 'react';
import { z } from 'zod';

// 3. Internal absolute imports
import { UserService } from '@/services/user';
import { Button } from '@/components/ui';

// 4. Relative imports
import { formatDate } from './utils';
import type { User } from './types';
```

**Rules**:
- Group by category with blank lines between
- Alphabetize within groups
- Use `type` imports for type-only imports
- Avoid circular dependencies

### 6. Error Handling

Handle errors explicitly. Don't let them silently fail.

```typescript
// Bad: Silent failure
async function getUser(id: string) {
  try {
    return await api.get(`/users/${id}`);
  } catch {
    return null; // What went wrong?
  }
}

// Good: Explicit error handling
async function getUser(id: string): Promise<Result<User, ApiError>> {
  try {
    const user = await api.get(`/users/${id}`);
    return { ok: true, value: user };
  } catch (error) {
    if (error instanceof NotFoundError) {
      return { ok: false, error: { code: 'NOT_FOUND', message: `User ${id} not found` } };
    }
    throw error; // Re-throw unexpected errors
  }
}
```

---

## The Golden Rule

> Write TypeScript as if the next person to read it is debugging a production incident at 2 AM. Make their life easier with types, clear names, and explicit error handling.

---

## Quick Reference

### Always Do
- Enable `strict: true` in tsconfig.json
- Type function parameters and return values
- Use `const` by default, `let` only when needed
- Handle errors explicitly
- Use async/await over raw promises
- Organize imports consistently

### Never Do
- Use `any` without a very good reason (and a comment explaining why)
- Use `@ts-ignore` without explanation
- Mix CommonJS and ES modules in the same project
- Catch errors and silently swallow them
- Use `==` instead of `===`
- Leave console.log statements in production code

### Consider Context
- **API boundaries**: Be extra strict with types at API boundaries
- **Internal utilities**: Can be more relaxed with inference
- **React components**: Always type props, can infer state
- **Test files**: Relax rules slightly for readability

---

## Common Patterns

### Result Type for Error Handling
```typescript
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };
```

### Discriminated Unions for State
```typescript
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };
```

### Type Guards
```typescript
function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'name' in value
  );
}
```

### Const Assertions
```typescript
const ROLES = ['admin', 'user', 'guest'] as const;
type Role = typeof ROLES[number]; // 'admin' | 'user' | 'guest'
```

---

## ESLint Rules We Care About

These rules catch real bugs:

| Rule | Why |
|------|-----|
| `@typescript-eslint/no-explicit-any` | Prevents type safety erosion |
| `@typescript-eslint/no-unused-vars` | Dead code removal |
| `no-console` | No debugging code in production |
| `react-hooks/rules-of-hooks` | Prevents hooks bugs |
| `react-hooks/exhaustive-deps` | Prevents stale closure bugs |
| `import/no-cycle` | Prevents circular dependencies |

## Stub Patterns We Flag

These indicate incomplete code:

| Pattern | Why It's Flagged |
|---------|------------------|
| `// TODO:` | Deferred work |
| `// FIXME:` | Known bug not fixed |
| `throw new Error("Not implemented")` | Placeholder |
| `console.log(...)` | Debug code |
| `: any` | Type safety hole |
| `as any` | Type assertion escape hatch |
