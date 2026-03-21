# Skill: SWR Data Fetching Pattern

**Category:** Frontend Data Management  
**Tech Stack:** React, SWR, TypeScript  
**Author:** Dallas  
**Date:** 2025-01-27

## Overview

Reusable pattern for client-side data fetching with automatic caching, revalidation, and type safety using SWR.

## When to Use

- Fetching paginated API lists (users, products, orders)
- Single resource fetching with cache (user profile, settings)
- Real-time data that needs background revalidation
- Reducing duplicate API calls across components

## Pattern

### 1. Define API Client Method

```typescript
// services/api.ts
export const usersApi = {
  async list(page = 1, pageSize = 20): Promise<PaginatedResponse<User>> {
    const { data } = await api.get<PaginatedResponse<User>>("/users", {
      params: { page, page_size: pageSize },
    });
    return data;
  },
  
  async get(id: number): Promise<User> {
    const { data } = await api.get<User>(`/users/${id}`);
    return data;
  },
};
```

### 2. Create SWR Hook

```typescript
// hooks/use-api.ts
import useSWR from "swr";
import { usersApi } from "@/services/api";
import type { PaginatedResponse, User } from "@/types";

export function useUsers(page = 1, pageSize = 20) {
  return useSWR<PaginatedResponse<User>>(
    ["users", page, pageSize], // Cache key (array for multiple params)
    () => usersApi.list(page, pageSize),
    { revalidateOnFocus: false } // Optional: disable auto-revalidation
  );
}

export function useUser(id: number | null) {
  return useSWR(
    id ? ["user", id] : null, // null key = don't fetch
    () => usersApi.get(id!),
    { revalidateOnFocus: false }
  );
}
```

### 3. Use in Component

```typescript
// app/users/page.tsx
"use client";

import { useUsers } from "@/hooks/use-api";
import { useState } from "react";

export default function UsersPage() {
  const [page, setPage] = useState(1);
  const { data, error, isLoading, mutate } = useUsers(page, 20);

  if (isLoading) return <Loader />;
  if (error) return <ErrorMessage />;

  const handleCreate = async (userData: UserCreate) => {
    await usersApi.create(userData);
    mutate(); // Revalidate cache after mutation
  };

  return (
    <div>
      {data.items.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
      <Pagination page={page} total={data.pages} onChange={setPage} />
    </div>
  );
}
```

## Key Features

### 1. Cache Key Strategy

```typescript
// Single resource
useSWR(["user", id], fetcher);

// List with filters
useSWR(["users", page, pageSize, filters], fetcher);

// Conditional fetch (null = don't fetch)
useSWR(id ? ["user", id] : null, fetcher);

// Dependent fetches
const { data: user } = useUser(userId);
const { data: posts } = usePosts(user?.id); // Only fetches after user loads
```

### 2. Manual Revalidation

```typescript
const { data, mutate } = useUsers(page);

// Revalidate after mutation
await usersApi.update(id, updates);
mutate(); // Refetches data

// Optimistic update
mutate({ ...data, items: [...data.items, newUser] }, false); // Update cache without revalidation
await usersApi.create(newUser);
mutate(); // Revalidate to confirm
```

### 3. Global Cache Invalidation

```typescript
import { mutate } from "swr";

// Invalidate all user-related caches
await usersApi.delete(id);
mutate((key) => Array.isArray(key) && key[0] === "users"); // Revalidate all "users" keys
```

## Configuration Options

```typescript
useSWR(key, fetcher, {
  revalidateOnFocus: false,    // Don't revalidate when window regains focus
  revalidateOnReconnect: true,  // Revalidate when network reconnects
  dedupingInterval: 2000,       // Dedupe requests within 2s
  errorRetryCount: 3,           // Retry failed requests 3 times
  errorRetryInterval: 5000,     // Wait 5s between retries
  suspense: false,              // Enable Suspense mode
});
```

## Best Practices

### ✅ Do

- Use array cache keys for multiple parameters: `["users", page, filters]`
- Return `null` key to skip fetching: `id ? ["user", id] : null`
- Call `mutate()` after create/update/delete operations
- Disable `revalidateOnFocus` for static data
- Use TypeScript generics for type safety: `useSWR<User>(key, fetcher)`

### ❌ Don't

- Don't use object cache keys (not serializable)
- Don't call hooks conditionally (breaks React rules)
- Don't forget to handle `isLoading` and `error` states
- Don't mutate data without revalidating (creates stale cache)

## TypeScript Integration

```typescript
// types/api.ts
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
}

// hooks/use-api.ts
export function useUsers(page = 1, pageSize = 20) {
  return useSWR<PaginatedResponse<User>>( // Type-safe response
    ["users", page, pageSize],
    () => usersApi.list(page, pageSize)
  );
}
```

## Error Handling

```typescript
const { data, error, isLoading } = useUsers();

if (isLoading) {
  return <Skeleton />;
}

if (error) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>
        {error.response?.data?.detail || "Failed to load users"}
      </AlertDescription>
    </Alert>
  );
}

// data is guaranteed to exist here
return <UserList users={data.items} />;
```

## Performance Tips

1. **Disable revalidation for static data:**
   ```typescript
   useSWR(key, fetcher, { revalidateOnFocus: false, revalidateOnReconnect: false });
   ```

2. **Prefetch data on hover:**
   ```typescript
   import { preload } from "swr";
   
   <button onMouseEnter={() => preload(["user", 123], userFetcher)}>
     View User
   </button>
   ```

3. **Dedupe identical requests:**
   ```typescript
   // Multiple components calling useUser(1) will share same request
   const { data } = useUser(1); // First call fetches
   const { data } = useUser(1); // Second call reuses cache
   ```

## Related Patterns

- **API Client Pattern:** See `lib/api-client.ts` for Axios setup
- **Type-Safe API:** See `services/api.ts` for endpoint definitions
- **Pagination Pattern:** Combine with page state for infinite scroll

## References

- [SWR Documentation](https://swr.vercel.app/)
- [SWR with Next.js](https://swr.vercel.app/docs/with-nextjs)
- AssistantAudit Implementation: `hooks/use-api.ts`
