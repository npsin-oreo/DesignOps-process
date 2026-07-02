# POC Patterns Reference — DesignOps Loop

Read this file when entering PROTOTYPE mode for patterns, boilerplates, and mock data strategies.

---

## POC Philosophy

> A good POC shows **core user value** at **minimum viable fidelity**.
> It's not production code — but it must look presentable enough for stakeholder review.

---

## Project Structure

```
src/
  app/
    (poc)/
      layout.tsx          # POC shell — nav, breadcrumb
      page.tsx            # Entry / landing screen
      [feature]/
        page.tsx          # Feature screen
        [id]/
          page.tsx        # Detail screen (if any)
  components/
    poc/                  # POC-only components (not reused in production)
      POCNav.tsx
      POCDataTable.tsx
      [FeatureName]/
        index.tsx
  data/
    mock/
      patients.ts         # Mock data per domain
      orders.ts
      voicebot-calls.ts
  lib/
    mock-utils.ts         # Helper for generating mock data
```

---

## Layout Boilerplate

### App Shell (layout.tsx)

```tsx
// app/(poc)/layout.tsx
import { POCNav } from "@/components/poc/POCNav"

export default function POCLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <POCNav />
      <main className="container mx-auto px-4 py-6 max-w-7xl">
        {children}
      </main>
    </div>
  )
}
```

### Page with States

```tsx
// app/(poc)/[feature]/page.tsx
import { Suspense } from "react"
import { FeatureContent } from "@/components/poc/Feature/index"
import { Skeleton } from "@/components/ui/skeleton"

export default function FeaturePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Feature Name</h1>
          <p className="text-sm text-muted-foreground">Description of this screen</p>
        </div>
        <PrimaryAction />
      </div>

      <Suspense fallback={<FeatureSkeleton />}>
        <FeatureContent />
      </Suspense>
    </div>
  )
}

function FeatureSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full rounded-lg" />
      ))}
    </div>
  )
}
```

---

## Mock Data Patterns

> Mock data should be realistic to the project's domain and locale (real-looking names, IDs,
> and document numbers). The examples below use English placeholders — swap them for the
> project's actual locale.

> **Demo-prefill (track G):** forms open with **valid seed defaults**, never blank. A POC exists to
> be walked through — if a form starts empty and the submit/confirm is disabled until it validates,
> the gated action (and any confirm dialog behind it) is unreachable in a demo and invisible to the
> render gate. Seed every field with a realistic default so the primary action is enabled on load and
> each confirm is one click away. To express "not ready", guard the action **inside** the dialog — do
> not disable the modal **trigger** (a disabled trigger never opens; gate 4 flags it).

### Pattern 1: Static Array (most common)

```ts
// data/mock/patients.ts
export interface MockPatient {
  id: string
  hn: string
  name: string
  age: number
  status: "waiting" | "in-progress" | "completed"
  appointmentTime: string
  doctor: string
}

export const mockPatients: MockPatient[] = [
  {
    id: "p001",
    hn: "HN-2024-0001",
    name: "John Carter",
    age: 45,
    status: "waiting",
    appointmentTime: "09:00",
    doctor: "Dr. Emily Reed",
  },
  {
    id: "p002",
    hn: "HN-2024-0002",
    name: "Maria Santos",
    age: 32,
    status: "in-progress",
    appointmentTime: "09:30",
    doctor: "Dr. Emily Reed",
  },
]
```

### Pattern 2: Generated Mock (when you need a lot of data)

```ts
// lib/mock-utils.ts
export function generateMockItems<T>(
  count: number,
  factory: (index: number) => T
): T[] {
  return Array.from({ length: count }, (_, i) => factory(i))
}

// Usage:
export const mockOrders = generateMockItems(20, (i) => ({
  id: `ORD-${String(i + 1).padStart(4, "0")}`,
  total: Math.floor(Math.random() * 5000) + 500,
  status: ["pending", "processing", "completed"][i % 3],
  createdAt: new Date(Date.now() - i * 86400000).toISOString(),
}))
```

### Pattern 3: State Machine Mock (for interactive POCs)

```tsx
// components/poc/OrderManager/index.tsx
"use client"

import { useState } from "react"
import { mockOrders } from "@/data/mock/orders"

export function OrderManager() {
  const [orders, setOrders] = useState(mockOrders)
  const [filter, setFilter] = useState<string>("all")

  const filtered = filter === "all"
    ? orders
    : orders.filter((o) => o.status === filter)

  function handleStatusChange(id: string, newStatus: string) {
    setOrders((prev) =>
      prev.map((o) => o.id === id ? { ...o, status: newStatus } : o)
    )
  }

  return (
    // ... UI
  )
}
```

---

## Common POC Components

### KPI Card (Dashboard / VoiceBot)

```tsx
interface KPICardProps {
  label: string
  value: string | number
  unit?: string
  trend?: { value: number; direction: "up" | "down" | "neutral" }
  variant?: "default" | "success" | "warning" | "danger"
}

export function KPICard({ label, value, unit, trend, variant = "default" }: KPICardProps) {
  const trendColor = trend?.direction === "up" ? "text-emerald-600" : "text-red-500"
  const trendIcon = trend?.direction === "up" ? "↑" : "↓"

  return (
    <div className="rounded-lg border bg-card p-4 space-y-2">
      <p className="text-sm text-muted-foreground">{label}</p>
      <div className="flex items-end gap-2">
        <span className="text-3xl font-semibold tabular-nums">{value}</span>
        {unit && <span className="text-sm text-muted-foreground mb-1">{unit}</span>}
      </div>
      {trend && (
        <p className={`text-sm ${trendColor}`}>
          {trendIcon} {Math.abs(trend.value)}% from last month
        </p>
      )}
    </div>
  )
}
```

### Status Badge (HIS / Queue)

```tsx
const statusConfig = {
  waiting:       { label: "Waiting",     className: "bg-amber-100 text-amber-800" },
  "in-progress": { label: "In progress", className: "bg-blue-100 text-blue-800" },
  completed:     { label: "Completed",   className: "bg-green-100 text-green-800" },
  cancelled:     { label: "Cancelled",   className: "bg-red-100 text-red-800" },
}

export function StatusBadge({ status }: { status: keyof typeof statusConfig }) {
  const config = statusConfig[status]
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  )
}
```

### Data Table with Pagination

```tsx
"use client"

import { useState } from "react"
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"

interface Column<T> {
  key: keyof T
  label: string
  render?: (value: T[keyof T], row: T) => React.ReactNode
}

interface POCDataTableProps<T> {
  data: T[]
  columns: Column<T>[]
  pageSize?: number
}

export function POCDataTable<T extends { id: string }>({
  data,
  columns,
  pageSize = 10,
}: POCDataTableProps<T>) {
  const [page, setPage] = useState(0)
  const paged = data.slice(page * pageSize, (page + 1) * pageSize)
  const totalPages = Math.ceil(data.length / pageSize)

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={String(col.key)}>{col.label}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {paged.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                  No data
                </TableCell>
              </TableRow>
            ) : (
              paged.map((row) => (
                <TableRow key={row.id}>
                  {columns.map((col) => (
                    <TableCell key={String(col.key)}>
                      {col.render
                        ? col.render(row[col.key], row)
                        : String(row[col.key])}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, data.length)} of {data.length}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setPage(p => p - 1)} disabled={page === 0}>Previous</Button>
            <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
```

---

## Empty / Error / Loading States

### Empty State

```tsx
import { Inbox } from "@phosphor-icons/react"

interface EmptyStateProps {
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Inbox size={48} className="text-muted-foreground/40 mb-4" />
      <h3 className="font-medium text-foreground">{title}</h3>
      {description && <p className="text-sm text-muted-foreground mt-1 max-w-xs">{description}</p>}
      {action && (
        <Button onClick={action.onClick} className="mt-4" variant="outline">
          {action.label}
        </Button>
      )}
    </div>
  )
}
```

### Error State

```tsx
import { WarningCircle } from "@phosphor-icons/react"

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 flex gap-3">
      <WarningCircle size={20} className="text-destructive shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-medium text-destructive">Something went wrong</p>
        <p className="text-sm text-muted-foreground mt-1">{message}</p>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry} className="mt-3">
            Try again
          </Button>
        )}
      </div>
    </div>
  )
}
```

---

## POC Quality Checklist

Before presenting the POC to stakeholders:

- [ ] Every screen has a clear title + description
- [ ] Primary action is visible and functional (at least navigates)
- [ ] Mock data is realistic enough — not "Lorem ipsum" or "User 1", "User 2"
- [ ] An empty state on at least 1 main screen
- [ ] An error state on at least 1 form or critical action
- [ ] Mobile responsive on every screen (viewable on a phone)
- [ ] Loading skeleton on data-heavy screens
- [ ] Navigation between screens works (no dead links)
- [ ] UI copy is correct and natural — not machine-translated
