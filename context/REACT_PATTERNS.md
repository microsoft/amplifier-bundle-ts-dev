# React Development Patterns

Expert knowledge for React development. This context helps the react-dev agent understand React idioms, common issues, and best practices.

## Component Patterns

### Functional Components (Preferred)

```tsx
// Good: Clear props interface, functional with hooks
interface UserCardProps {
  user: User;
  onSelect?: (user: User) => void;
  className?: string;
}

export function UserCard({ user, onSelect, className }: UserCardProps) {
  const handleClick = useCallback(() => {
    onSelect?.(user);
  }, [user, onSelect]);

  return (
    <div className={className} onClick={handleClick}>
      <Avatar src={user.avatar} />
      <span>{user.name}</span>
    </div>
  );
}
```

### Component Composition Over Props

```tsx
// Bad: Prop explosion
<Card
  title="Settings"
  showIcon={true}
  iconType="gear"
  headerAction={<Button>Save</Button>}
  footerLeft={<Button>Cancel</Button>}
  footerRight={<Button>Submit</Button>}
/>

// Good: Composition with children/slots
<Card>
  <Card.Header icon={<GearIcon />}>
    Settings
    <Card.Action><Button>Save</Button></Card.Action>
  </Card.Header>
  <Card.Body>{/* content */}</Card.Body>
  <Card.Footer>
    <Button>Cancel</Button>
    <Button>Submit</Button>
  </Card.Footer>
</Card>
```

### Render Props vs Hooks

```tsx
// Legacy: Render props (still valid for some cases)
<MousePosition>
  {({ x, y }) => <Cursor x={x} y={y} />}
</MousePosition>

// Modern: Custom hooks (preferred)
function Cursor() {
  const { x, y } = useMousePosition();
  return <div style={{ left: x, top: y }} />;
}
```

---

## Hooks Patterns

### The Rules of Hooks

1. **Only call hooks at the top level** - Never inside loops, conditions, or nested functions
2. **Only call hooks from React functions** - Components or custom hooks
3. **Custom hooks must start with "use"** - Convention that enables the rules

### useState Patterns

```tsx
// Simple state
const [count, setCount] = useState(0);

// Lazy initialization (for expensive computations)
const [data, setData] = useState(() => expensiveComputation());

// Object state - replace entire object, don't mutate
const [user, setUser] = useState({ name: '', email: '' });
setUser(prev => ({ ...prev, name: 'John' })); // Correct
// user.name = 'John'; setUser(user); // WRONG - mutation

// Consider useReducer for complex state
const [state, dispatch] = useReducer(reducer, initialState);
```

### useEffect Patterns

```tsx
// Effect with cleanup
useEffect(() => {
  const subscription = api.subscribe(handler);
  return () => subscription.unsubscribe(); // Cleanup!
}, [handler]);

// Fetch data pattern
useEffect(() => {
  let cancelled = false;
  
  async function fetchData() {
    const result = await api.getData(id);
    if (!cancelled) {
      setData(result);
    }
  }
  
  fetchData();
  return () => { cancelled = true; };
}, [id]);

// Event listener pattern
useEffect(() => {
  function handleResize() {
    setWidth(window.innerWidth);
  }
  
  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);
```

### Dependency Array Gotchas

```tsx
// BAD: Missing dependency - stale closure
useEffect(() => {
  const timer = setInterval(() => {
    setCount(count + 1); // count is stale!
  }, 1000);
  return () => clearInterval(timer);
}, []); // Missing 'count' dependency

// GOOD: Functional update
useEffect(() => {
  const timer = setInterval(() => {
    setCount(c => c + 1); // No dependency needed
  }, 1000);
  return () => clearInterval(timer);
}, []);

// GOOD: Include all dependencies
useEffect(() => {
  fetchUser(userId);
}, [userId, fetchUser]); // Both included
```

### useMemo and useCallback

```tsx
// useMemo: Memoize expensive computations
const sortedItems = useMemo(() => {
  return items.slice().sort((a, b) => a.name.localeCompare(b.name));
}, [items]);

// useCallback: Memoize functions (especially for child props)
const handleClick = useCallback(() => {
  onSelect(item.id);
}, [item.id, onSelect]);

// DON'T overuse - adds complexity
// BAD: Unnecessary memoization
const double = useMemo(() => count * 2, [count]); // Just compute it!
const double = count * 2; // GOOD: Simple computation
```

### Custom Hooks

```tsx
// Extract reusable logic
function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initialValue;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue] as const;
}

// Usage
const [theme, setTheme] = useLocalStorage('theme', 'light');
```

---

## State Management

### Lifting State Up

```tsx
// Before: Sibling communication problem
function App() {
  return (
    <>
      <SearchInput /> {/* Has the search term */}
      <ResultsList /> {/* Needs the search term */}
    </>
  );
}

// After: Lift state to common ancestor
function App() {
  const [searchTerm, setSearchTerm] = useState('');
  return (
    <>
      <SearchInput value={searchTerm} onChange={setSearchTerm} />
      <ResultsList searchTerm={searchTerm} />
    </>
  );
}
```

### Context for Cross-Cutting Concerns

```tsx
// Create typed context
interface AuthContextType {
  user: User | null;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

// Custom hook for consuming
function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

// Provider component
function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  
  const login = useCallback(async (credentials: Credentials) => {
    const user = await api.login(credentials);
    setUser(user);
  }, []);
  
  const logout = useCallback(() => {
    setUser(null);
  }, []);
  
  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

### When to Use External State Management

| Scenario | Solution |
|----------|----------|
| Local UI state | useState |
| Shared between siblings | Lift state up |
| Deep prop drilling | Context |
| Server state (fetching, caching) | React Query / SWR |
| Complex client state | Zustand / Redux Toolkit |
| Form state | React Hook Form |

---

## Performance Patterns

### Avoiding Unnecessary Re-renders

```tsx
// Problem: New object reference every render
function Parent() {
  const style = { color: 'red' }; // New object every render!
  return <Child style={style} />;
}

// Solution 1: Move outside component
const style = { color: 'red' };
function Parent() {
  return <Child style={style} />;
}

// Solution 2: useMemo
function Parent() {
  const style = useMemo(() => ({ color: 'red' }), []);
  return <Child style={style} />;
}
```

### React.memo for Pure Components

```tsx
// Memoize component to prevent re-renders when props haven't changed
const ExpensiveList = React.memo(function ExpensiveList({ items }: Props) {
  return (
    <ul>
      {items.map(item => (
        <ExpensiveItem key={item.id} item={item} />
      ))}
    </ul>
  );
});

// Custom comparison function
const UserCard = React.memo(
  function UserCard({ user }: { user: User }) {
    return <div>{user.name}</div>;
  },
  (prevProps, nextProps) => prevProps.user.id === nextProps.user.id
);
```

### Code Splitting

```tsx
// Lazy load components
const Dashboard = lazy(() => import('./Dashboard'));
const Settings = lazy(() => import('./Settings'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  );
}
```

---

## Common Anti-Patterns

### 1. Prop Drilling

```tsx
// BAD: Passing props through many levels
<App user={user}>
  <Layout user={user}>
    <Sidebar user={user}>
      <UserMenu user={user} />  {/* Finally used here */}
    </Sidebar>
  </Layout>
</App>

// GOOD: Context for deeply nested data
<UserProvider user={user}>
  <App>
    <Layout>
      <Sidebar>
        <UserMenu />  {/* Uses useUser() hook */}
      </Sidebar>
    </Layout>
  </App>
</UserProvider>
```

### 2. Derived State in useState

```tsx
// BAD: Duplicating derived state
function ProductList({ products }) {
  const [filteredProducts, setFilteredProducts] = useState(products);
  const [searchTerm, setSearchTerm] = useState('');
  
  useEffect(() => {
    setFilteredProducts(products.filter(p => p.name.includes(searchTerm)));
  }, [products, searchTerm]);
  
  // ...
}

// GOOD: Compute during render
function ProductList({ products }) {
  const [searchTerm, setSearchTerm] = useState('');
  
  const filteredProducts = useMemo(
    () => products.filter(p => p.name.includes(searchTerm)),
    [products, searchTerm]
  );
  
  // ...
}
```

### 3. useEffect for Synchronization

```tsx
// BAD: Effect to sync state
function Form({ initialValue }) {
  const [value, setValue] = useState(initialValue);
  
  useEffect(() => {
    setValue(initialValue); // Sync on prop change
  }, [initialValue]);
}

// GOOD: Key to reset component
<Form key={userId} initialValue={userData} />
```

### 4. Fetching in useEffect Without Cleanup

```tsx
// BAD: Race condition, no cleanup
useEffect(() => {
  fetchData(id).then(setData);
}, [id]);

// GOOD: Cleanup to prevent stale updates
useEffect(() => {
  let active = true;
  fetchData(id).then(data => {
    if (active) setData(data);
  });
  return () => { active = false; };
}, [id]);

// BETTER: Use React Query or SWR
const { data } = useQuery(['data', id], () => fetchData(id));
```

---

## Testing Patterns

### React Testing Library Philosophy

```tsx
// Test behavior, not implementation
// BAD: Testing implementation details
expect(component.state.isOpen).toBe(true);
expect(wrapper.find('.dropdown-menu').hasClass('open')).toBe(true);

// GOOD: Testing user-visible behavior
expect(screen.getByRole('menu')).toBeVisible();
expect(screen.getByText('Settings')).toBeInTheDocument();
```

### Common Testing Patterns

```tsx
// Arrange-Act-Assert
test('submits form with user data', async () => {
  // Arrange
  const onSubmit = jest.fn();
  render(<LoginForm onSubmit={onSubmit} />);
  
  // Act
  await userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
  await userEvent.type(screen.getByLabelText('Password'), 'password123');
  await userEvent.click(screen.getByRole('button', { name: 'Login' }));
  
  // Assert
  expect(onSubmit).toHaveBeenCalledWith({
    email: 'test@example.com',
    password: 'password123',
  });
});

// Testing async behavior
test('shows loading state while fetching', async () => {
  render(<UserProfile userId="123" />);
  
  expect(screen.getByText('Loading...')).toBeInTheDocument();
  
  await waitFor(() => {
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });
});
```

---

## Debugging Tips

### React DevTools

- **Components tab**: Inspect component tree, props, state, hooks
- **Profiler tab**: Record and analyze re-renders
- **Highlight updates**: Visualize what's re-rendering

### Common Issues and Solutions

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Infinite re-render loop | useEffect dependency creates new reference | useMemo/useCallback, or move outside component |
| Stale state in callback | Closure captured old value | Functional update or add to dependencies |
| Child re-renders unnecessarily | Parent passes new object/function reference | React.memo + useMemo/useCallback |
| useEffect runs twice | StrictMode double-invocation | Ensure cleanup works correctly |
| State update on unmounted | Async operation completes after unmount | Cleanup with cancelled flag |
