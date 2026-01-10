# Next.js Development Patterns

Expert knowledge for Next.js development. This context helps the nextjs-dev agent understand Next.js idioms, App Router patterns, and common issues.

## App Router vs Pages Router

Next.js 13+ introduced the App Router. Understanding both is crucial for migrations and legacy codebases.

| Feature | App Router (`app/`) | Pages Router (`pages/`) |
|---------|---------------------|-------------------------|
| Components | Server Components by default | Client Components only |
| Data fetching | `fetch` with caching, Server Components | `getServerSideProps`, `getStaticProps` |
| Layouts | Nested layouts with `layout.tsx` | `_app.tsx`, manual nesting |
| Loading UI | `loading.tsx` | Manual implementation |
| Error handling | `error.tsx` | `_error.tsx` |
| Metadata | `metadata` export, `generateMetadata` | `Head` component |

---

## App Router Fundamentals

### File Conventions

```
app/
├── layout.tsx          # Root layout (required)
├── page.tsx            # Home page (/)
├── loading.tsx         # Loading UI
├── error.tsx           # Error boundary
├── not-found.tsx       # 404 page
├── global-error.tsx    # Global error boundary
│
├── dashboard/
│   ├── layout.tsx      # Dashboard layout
│   ├── page.tsx        # /dashboard
│   └── settings/
│       └── page.tsx    # /dashboard/settings
│
├── blog/
│   ├── page.tsx        # /blog
│   └── [slug]/
│       └── page.tsx    # /blog/:slug (dynamic route)
│
├── api/
│   └── users/
│       └── route.ts    # API route: /api/users
│
└── (marketing)/        # Route group (doesn't affect URL)
    ├── about/
    │   └── page.tsx    # /about
    └── contact/
        └── page.tsx    # /contact
```

### Server vs Client Components

```tsx
// Server Component (default) - runs on server only
// Can: fetch data, access backend, use async/await
// Cannot: use hooks, browser APIs, event handlers
export default async function ProductList() {
  const products = await db.products.findMany(); // Direct DB access!
  return (
    <ul>
      {products.map(p => <li key={p.id}>{p.name}</li>)}
    </ul>
  );
}

// Client Component - add 'use client' directive
'use client';

import { useState } from 'react';

export default function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

### When to Use Client Components

| Need | Component Type |
|------|----------------|
| Fetch data | Server |
| Access backend resources | Server |
| Keep sensitive info on server | Server |
| Use hooks (useState, useEffect) | Client |
| Use browser APIs | Client |
| Add event handlers | Client |
| Use React Context | Client |

### Composition Pattern

```tsx
// Server Component with Client Component children
// page.tsx (Server)
import { AddToCart } from './AddToCart';

export default async function ProductPage({ params }) {
  const product = await getProduct(params.id);
  
  return (
    <div>
      <h1>{product.name}</h1>
      <p>{product.description}</p>
      {/* Client Component for interactivity */}
      <AddToCart productId={product.id} />
    </div>
  );
}

// AddToCart.tsx (Client)
'use client';

export function AddToCart({ productId }: { productId: string }) {
  const [adding, setAdding] = useState(false);
  
  async function handleAdd() {
    setAdding(true);
    await addToCart(productId);
    setAdding(false);
  }
  
  return <button onClick={handleAdd} disabled={adding}>Add to Cart</button>;
}
```

---

## Data Fetching

### Server Components with fetch

```tsx
// Fetching in Server Components
async function getUser(id: string) {
  const res = await fetch(`https://api.example.com/users/${id}`, {
    // Cache options
    cache: 'force-cache',      // Default: cache indefinitely (static)
    // cache: 'no-store',      // Never cache (dynamic)
    // next: { revalidate: 60 }, // Revalidate every 60 seconds (ISR)
  });
  
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
}

export default async function UserProfile({ params }) {
  const user = await getUser(params.id);
  return <div>{user.name}</div>;
}
```

### Caching Strategies

```tsx
// Static (cached forever until redeployed)
fetch(url, { cache: 'force-cache' }); // Default

// Dynamic (never cached)
fetch(url, { cache: 'no-store' });

// ISR - Incremental Static Regeneration
fetch(url, { next: { revalidate: 3600 } }); // Revalidate hourly

// Tag-based revalidation
fetch(url, { next: { tags: ['products'] } });
// Later: revalidateTag('products')
```

### Parallel Data Fetching

```tsx
// BAD: Sequential (waterfall)
async function Page() {
  const user = await getUser();    // Wait...
  const posts = await getPosts();  // Then wait...
  return <div>{/* ... */}</div>;
}

// GOOD: Parallel
async function Page() {
  const [user, posts] = await Promise.all([
    getUser(),
    getPosts(),
  ]);
  return <div>{/* ... */}</div>;
}

// BETTER: Suspense boundaries for streaming
async function Page() {
  const userPromise = getUser();
  const postsPromise = getPosts();
  
  return (
    <div>
      <Suspense fallback={<UserSkeleton />}>
        <UserSection userPromise={userPromise} />
      </Suspense>
      <Suspense fallback={<PostsSkeleton />}>
        <PostsSection postsPromise={postsPromise} />
      </Suspense>
    </div>
  );
}
```

### Server Actions

```tsx
// Define in Server Component or separate file with 'use server'
async function createPost(formData: FormData) {
  'use server';
  
  const title = formData.get('title');
  const content = formData.get('content');
  
  await db.posts.create({ data: { title, content } });
  revalidatePath('/posts');
  redirect('/posts');
}

// Use in form
export default function NewPostForm() {
  return (
    <form action={createPost}>
      <input name="title" required />
      <textarea name="content" required />
      <button type="submit">Create</button>
    </form>
  );
}

// Or call programmatically from Client Component
'use client';

import { createPost } from './actions';

export function CreateButton() {
  async function handleClick() {
    await createPost({ title: 'New Post' });
  }
  return <button onClick={handleClick}>Create</button>;
}
```

---

## Routing Patterns

### Dynamic Routes

```tsx
// app/blog/[slug]/page.tsx
export default function BlogPost({ params }: { params: { slug: string } }) {
  return <h1>Post: {params.slug}</h1>;
}

// app/shop/[...categories]/page.tsx (catch-all)
// Matches: /shop/clothes, /shop/clothes/shirts, etc.
export default function Category({ params }: { params: { categories: string[] } }) {
  return <div>Categories: {params.categories.join(' > ')}</div>;
}

// app/shop/[[...categories]]/page.tsx (optional catch-all)
// Also matches: /shop
```

### Route Groups

```tsx
// Organize without affecting URL
app/
├── (marketing)/
│   ├── layout.tsx      # Marketing-specific layout
│   ├── about/page.tsx  # /about
│   └── blog/page.tsx   # /blog
│
├── (shop)/
│   ├── layout.tsx      # Shop-specific layout
│   ├── cart/page.tsx   # /cart
│   └── products/page.tsx # /products
│
└── layout.tsx          # Root layout
```

### Parallel Routes

```tsx
// app/layout.tsx
export default function Layout({
  children,
  analytics,
  team,
}: {
  children: React.ReactNode;
  analytics: React.ReactNode;
  team: React.ReactNode;
}) {
  return (
    <div>
      {children}
      {analytics}
      {team}
    </div>
  );
}

// app/@analytics/page.tsx - Slot
// app/@team/page.tsx - Slot
```

### Intercepting Routes

```tsx
// Intercept route to show modal while preserving URL
app/
├── feed/
│   └── page.tsx
├── photo/
│   └── [id]/
│       └── page.tsx      # /photo/123 (full page)
│
└── @modal/
    └── (.)photo/
        └── [id]/
            └── page.tsx  # Intercepts /photo/123 when navigating from /feed
```

---

## Layouts and Templates

### Root Layout (Required)

```tsx
// app/layout.tsx
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'My App',
  description: 'App description',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Header />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
```

### Nested Layouts

```tsx
// app/dashboard/layout.tsx
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="dashboard">
      <Sidebar />
      <div className="content">{children}</div>
    </div>
  );
}
// Children: /dashboard, /dashboard/settings, etc.
```

### Templates (Re-mount on Navigation)

```tsx
// app/dashboard/template.tsx
// Unlike layout, template creates new instance on each navigation
export default function Template({ children }: { children: React.ReactNode }) {
  return <div>{children}</div>;
}
```

---

## Metadata and SEO

### Static Metadata

```tsx
// app/page.tsx
export const metadata = {
  title: 'Home',
  description: 'Welcome to our site',
  openGraph: {
    title: 'Home',
    description: 'Welcome to our site',
    images: ['/og-image.png'],
  },
};
```

### Dynamic Metadata

```tsx
// app/blog/[slug]/page.tsx
export async function generateMetadata({ params }): Promise<Metadata> {
  const post = await getPost(params.slug);
  
  return {
    title: post.title,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      images: [post.coverImage],
    },
  };
}
```

---

## Common Issues and Solutions

### Hydration Mismatch

```tsx
// BAD: Server/client render differently
function Component() {
  return <p>Time: {new Date().toLocaleTimeString()}</p>; // Different on server vs client!
}

// GOOD: Use useEffect for client-only values
'use client';

function Component() {
  const [time, setTime] = useState<string>();
  
  useEffect(() => {
    setTime(new Date().toLocaleTimeString());
  }, []);
  
  return <p>Time: {time ?? 'Loading...'}</p>;
}

// OR: Suppress hydration warning (use sparingly)
<time suppressHydrationWarning>{new Date().toLocaleTimeString()}</time>
```

### "use client" Boundary Issues

```tsx
// BAD: Importing Server Component into Client Component
'use client';
import ServerComponent from './ServerComponent'; // Won't work as expected!

// GOOD: Pass as children
'use client';
export function ClientWrapper({ children }) {
  return <div onClick={...}>{children}</div>;
}

// In page.tsx (Server)
<ClientWrapper>
  <ServerComponent />
</ClientWrapper>
```

### Dynamic Import for Client-Only Libraries

```tsx
// For libraries that access window/document
'use client';

import dynamic from 'next/dynamic';

const Chart = dynamic(() => import('./Chart'), {
  ssr: false, // Only load on client
  loading: () => <p>Loading chart...</p>,
});
```

### Route Handler vs Server Action

| Use Case | Solution |
|----------|----------|
| Form submission | Server Action |
| Mutation from UI | Server Action |
| External API endpoint | Route Handler |
| Webhook receiver | Route Handler |
| Complex validation before mutation | Server Action |

---

## Performance Patterns

### Image Optimization

```tsx
import Image from 'next/image';

<Image
  src="/hero.jpg"
  alt="Hero"
  width={1200}
  height={600}
  priority // Load immediately (above fold)
/>

<Image
  src="/thumbnail.jpg"
  alt="Thumbnail"
  width={300}
  height={200}
  placeholder="blur"
  blurDataURL="data:image/..." // Or auto-generated for static imports
/>
```

### Font Optimization

```tsx
import { Inter, Roboto_Mono } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

const robotoMono = Roboto_Mono({
  subsets: ['latin'],
  variable: '--font-roboto-mono',
});

export default function RootLayout({ children }) {
  return (
    <html className={`${inter.variable} ${robotoMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

### Script Optimization

```tsx
import Script from 'next/script';

<Script
  src="https://analytics.example.com/script.js"
  strategy="lazyOnload" // Load after page is interactive
/>

<Script
  id="structured-data"
  type="application/ld+json"
  dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
/>
```

---

## Debugging Tips

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Hydration mismatch | Different server/client render | useEffect for dynamic values |
| "use client" not working | Missing directive or wrong file | Ensure 'use client' is first line |
| fetch not caching | Dynamic function used | Remove cookies(), headers() if not needed |
| Layout not updating | Layouts don't remount | Use template.tsx or key prop |
| Server Action failing | Not marked with 'use server' | Add directive to function or file |
| Slow page | Waterfall data fetching | Use Promise.all or Suspense |
