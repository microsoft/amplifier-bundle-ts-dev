# Node.js Development Patterns

Expert knowledge for Node.js backend development. This context helps the node-dev agent understand Node.js idioms, async patterns, error handling, and security best practices.

## Async Patterns

### The Event Loop

Node.js uses a single-threaded event loop. Understanding it is crucial for performance.

```
   ┌───────────────────────────┐
┌─>│           timers          │ ← setTimeout, setInterval
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │     pending callbacks     │ ← I/O callbacks deferred
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │       idle, prepare       │ ← internal use
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │           poll            │ ← retrieve I/O events
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │           check           │ ← setImmediate
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
└──┤      close callbacks      │ ← socket.on('close')
   └───────────────────────────┘
```

**Key insight**: Long-running synchronous operations BLOCK the event loop.

### Async/Await Best Practices

```typescript
// BAD: Sequential when could be parallel
async function getPageData() {
  const user = await getUser();      // Wait...
  const posts = await getPosts();    // Then wait...
  const comments = await getComments(); // Then wait...
  return { user, posts, comments };
}

// GOOD: Parallel when independent
async function getPageData() {
  const [user, posts, comments] = await Promise.all([
    getUser(),
    getPosts(),
    getComments(),
  ]);
  return { user, posts, comments };
}

// GOOD: Promise.allSettled for partial failures OK
async function fetchAllUsers(ids: string[]) {
  const results = await Promise.allSettled(
    ids.map(id => getUser(id))
  );
  
  const users = results
    .filter((r): r is PromiseFulfilledResult<User> => r.status === 'fulfilled')
    .map(r => r.value);
    
  const errors = results
    .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
    .map(r => r.reason);
    
  return { users, errors };
}
```

### Error Handling in Async Code

```typescript
// BAD: Unhandled promise rejection
async function riskyOperation() {
  const data = await fetchData(); // If this throws, unhandled!
  return process(data);
}

// GOOD: Try-catch with proper error handling
async function riskyOperation() {
  try {
    const data = await fetchData();
    return process(data);
  } catch (error) {
    logger.error('Failed to fetch data', { error });
    throw new ApplicationError('Data fetch failed', { cause: error });
  }
}

// GOOD: Error handling at the boundary
app.get('/api/data', async (req, res, next) => {
  try {
    const data = await getData();
    res.json(data);
  } catch (error) {
    next(error); // Pass to error middleware
  }
});
```

### Streams

```typescript
import { createReadStream, createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import { createGzip } from 'zlib';

// Process large files without loading into memory
async function compressFile(input: string, output: string) {
  await pipeline(
    createReadStream(input),
    createGzip(),
    createWriteStream(output)
  );
}

// Transform stream
import { Transform } from 'stream';

const upperCase = new Transform({
  transform(chunk, encoding, callback) {
    this.push(chunk.toString().toUpperCase());
    callback();
  }
});

// Async iteration over streams
import { createInterface } from 'readline';

async function processLines(filePath: string) {
  const rl = createInterface({
    input: createReadStream(filePath),
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    await processLine(line);
  }
}
```

---

## Error Handling

### Custom Error Classes

```typescript
// Base application error
class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500,
    public isOperational: boolean = true
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

// Specific error types
class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super(`${resource} with id ${id} not found`, 'NOT_FOUND', 404);
  }
}

class ValidationError extends AppError {
  constructor(message: string, public fields: Record<string, string>) {
    super(message, 'VALIDATION_ERROR', 400);
  }
}

class UnauthorizedError extends AppError {
  constructor(message = 'Authentication required') {
    super(message, 'UNAUTHORIZED', 401);
  }
}
```

### Express Error Middleware

```typescript
// Error handling middleware (must have 4 parameters)
function errorHandler(
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
) {
  // Log the error
  logger.error('Request failed', {
    error: err,
    path: req.path,
    method: req.method,
    requestId: req.id,
  });

  // Handle known errors
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      error: {
        code: err.code,
        message: err.message,
        ...(err instanceof ValidationError && { fields: err.fields }),
      },
    });
  }

  // Handle unknown errors (don't leak details in production)
  const isDev = process.env.NODE_ENV === 'development';
  res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: isDev ? err.message : 'An unexpected error occurred',
      ...(isDev && { stack: err.stack }),
    },
  });
}

// Must be last middleware
app.use(errorHandler);
```

### Unhandled Rejection Handling

```typescript
// Catch unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection', { reason, promise });
  // In production, you might want to exit
  // process.exit(1);
});

// Catch uncaught exceptions
process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception', { error });
  // Give time to log, then exit
  setTimeout(() => process.exit(1), 1000);
});
```

---

## Security Patterns

### Input Validation with Zod

```typescript
import { z } from 'zod';

// Define schema
const createUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(100),
  name: z.string().min(1).max(100),
  role: z.enum(['user', 'admin']).default('user'),
});

type CreateUserInput = z.infer<typeof createUserSchema>;

// Validation middleware
function validate<T>(schema: z.ZodSchema<T>) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({
        error: {
          code: 'VALIDATION_ERROR',
          issues: result.error.issues,
        },
      });
    }
    req.body = result.data;
    next();
  };
}

// Usage
app.post('/users', validate(createUserSchema), createUserHandler);
```

### SQL Injection Prevention

```typescript
// BAD: String concatenation (SQL injection!)
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// GOOD: Parameterized queries
const [rows] = await db.execute(
  'SELECT * FROM users WHERE id = ?',
  [userId]
);

// GOOD: Query builder (Prisma, Drizzle, etc.)
const user = await prisma.user.findUnique({
  where: { id: userId },
});
```

### Authentication Patterns

```typescript
import jwt from 'jsonwebtoken';
import bcrypt from 'bcrypt';

// Password hashing
async function hashPassword(password: string): Promise<string> {
  const saltRounds = 12;
  return bcrypt.hash(password, saltRounds);
}

async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

// JWT tokens
interface TokenPayload {
  userId: string;
  role: string;
}

function generateToken(payload: TokenPayload): string {
  return jwt.sign(payload, process.env.JWT_SECRET!, {
    expiresIn: '24h',
    issuer: 'my-app',
  });
}

function verifyToken(token: string): TokenPayload {
  return jwt.verify(token, process.env.JWT_SECRET!, {
    issuer: 'my-app',
  }) as TokenPayload;
}

// Auth middleware
function authenticate(req: Request, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    throw new UnauthorizedError('Missing token');
  }
  
  try {
    const token = header.slice(7);
    req.user = verifyToken(token);
    next();
  } catch {
    throw new UnauthorizedError('Invalid token');
  }
}
```

### Rate Limiting

```typescript
import rateLimit from 'express-rate-limit';

// Basic rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per window
  message: { error: { code: 'RATE_LIMITED', message: 'Too many requests' } },
  standardHeaders: true,
  legacyHeaders: false,
});

app.use('/api/', limiter);

// Stricter limits for auth endpoints
const authLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 5, // 5 failed attempts per hour
  skipSuccessfulRequests: true,
});

app.use('/api/auth/login', authLimiter);
```

### Security Headers

```typescript
import helmet from 'helmet';

app.use(helmet()); // Sets various security headers

// Or configure individually
app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'", "'unsafe-inline'"],
    styleSrc: ["'self'", "'unsafe-inline'"],
    imgSrc: ["'self'", 'data:', 'https:'],
  },
}));
```

---

## API Design

### RESTful Conventions

```typescript
// Resource-oriented URLs
// GET    /api/users          - List users
// POST   /api/users          - Create user
// GET    /api/users/:id      - Get user
// PUT    /api/users/:id      - Replace user
// PATCH  /api/users/:id      - Update user
// DELETE /api/users/:id      - Delete user

// Nested resources
// GET    /api/users/:id/posts     - User's posts
// POST   /api/users/:id/posts     - Create post for user

// Query parameters for filtering/pagination
// GET    /api/users?role=admin&limit=10&offset=0
```

### Response Formatting

```typescript
// Success response
interface SuccessResponse<T> {
  data: T;
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
  };
}

// Error response
interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

// Consistent response helpers
function sendSuccess<T>(res: Response, data: T, meta?: object) {
  res.json({ data, meta });
}

function sendCreated<T>(res: Response, data: T) {
  res.status(201).json({ data });
}

function sendNoContent(res: Response) {
  res.status(204).send();
}
```

### Pagination

```typescript
interface PaginationParams {
  page: number;
  limit: number;
}

interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
    hasMore: boolean;
  };
}

async function paginate<T>(
  query: () => Promise<T[]>,
  count: () => Promise<number>,
  params: PaginationParams
): Promise<PaginatedResponse<T>> {
  const [data, total] = await Promise.all([query(), count()]);
  const totalPages = Math.ceil(total / params.limit);
  
  return {
    data,
    meta: {
      total,
      page: params.page,
      limit: params.limit,
      totalPages,
      hasMore: params.page < totalPages,
    },
  };
}
```

---

## Performance Patterns

### Caching

```typescript
import NodeCache from 'node-cache';

const cache = new NodeCache({ stdTTL: 300 }); // 5 minute default TTL

async function getCachedUser(id: string): Promise<User> {
  const cacheKey = `user:${id}`;
  
  // Check cache
  const cached = cache.get<User>(cacheKey);
  if (cached) return cached;
  
  // Fetch and cache
  const user = await db.users.findUnique({ where: { id } });
  if (user) {
    cache.set(cacheKey, user);
  }
  return user;
}

// Cache invalidation
function invalidateUserCache(id: string) {
  cache.del(`user:${id}`);
}
```

### Connection Pooling

```typescript
// Database connection pool
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  max: 20,           // Max connections
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Use pool for queries
async function query<T>(sql: string, params?: unknown[]): Promise<T[]> {
  const client = await pool.connect();
  try {
    const result = await client.query(sql, params);
    return result.rows;
  } finally {
    client.release(); // Always release!
  }
}
```

### Worker Threads for CPU-Intensive Tasks

```typescript
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';

if (isMainThread) {
  // Main thread
  function runWorker(data: unknown): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const worker = new Worker(__filename, { workerData: data });
      worker.on('message', resolve);
      worker.on('error', reject);
      worker.on('exit', (code) => {
        if (code !== 0) reject(new Error(`Worker exited with code ${code}`));
      });
    });
  }
  
  // Usage
  const result = await runWorker({ numbers: [1, 2, 3, 4, 5] });
} else {
  // Worker thread
  const { numbers } = workerData;
  const result = heavyComputation(numbers);
  parentPort?.postMessage(result);
}
```

---

## Graceful Shutdown

```typescript
const server = app.listen(port);

// Track active connections
const connections = new Set<Socket>();
server.on('connection', (socket) => {
  connections.add(socket);
  socket.on('close', () => connections.delete(socket));
});

async function shutdown(signal: string) {
  logger.info(`${signal} received, starting graceful shutdown`);
  
  // Stop accepting new connections
  server.close(() => {
    logger.info('HTTP server closed');
  });
  
  // Close database connections
  await db.$disconnect();
  
  // Close remaining connections after timeout
  setTimeout(() => {
    connections.forEach((socket) => socket.destroy());
  }, 10000);
  
  // Exit
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
```

---

## Common Anti-Patterns

### 1. Blocking the Event Loop

```typescript
// BAD: Synchronous file read in request handler
app.get('/file', (req, res) => {
  const content = fs.readFileSync('large-file.txt'); // Blocks!
  res.send(content);
});

// GOOD: Async file read
app.get('/file', async (req, res) => {
  const content = await fs.promises.readFile('large-file.txt');
  res.send(content);
});

// BETTER: Stream for large files
app.get('/file', (req, res) => {
  const stream = fs.createReadStream('large-file.txt');
  stream.pipe(res);
});
```

### 2. Memory Leaks

```typescript
// BAD: Unbounded array growth
const requestLog: Request[] = [];
app.use((req, res, next) => {
  requestLog.push(req); // Never cleaned up!
  next();
});

// GOOD: Use proper logging with rotation
import pino from 'pino';
const logger = pino({
  transport: {
    target: 'pino/file',
    options: { destination: './app.log' },
  },
});
```

### 3. Callback Hell

```typescript
// BAD: Nested callbacks
fs.readFile('file1.txt', (err, data1) => {
  if (err) return handleError(err);
  fs.readFile('file2.txt', (err, data2) => {
    if (err) return handleError(err);
    fs.writeFile('output.txt', data1 + data2, (err) => {
      if (err) return handleError(err);
      console.log('Done!');
    });
  });
});

// GOOD: Async/await
async function processFiles() {
  const [data1, data2] = await Promise.all([
    fs.promises.readFile('file1.txt'),
    fs.promises.readFile('file2.txt'),
  ]);
  await fs.promises.writeFile('output.txt', data1 + data2);
  console.log('Done!');
}
```
