import type { ReactNode } from 'react'
import type { ApiState } from '../useApi'
import type { Route, Severity } from '../api'

export function Card({ title, subtitle, children }: { title: string; subtitle?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-line bg-white p-6">
      <h2 className="text-xl font-semibold text-navy-900">{title}</h2>
      {subtitle && <p className="mt-1 text-ink-2">{subtitle}</p>}
      <div className="mt-5">{children}</div>
    </section>
  )
}

export function StatTile({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="rounded-lg border border-line bg-white px-5 py-4">
      <div className="text-ink-2">{label}</div>
      <div className="mt-1 text-3xl font-semibold">{value}</div>
      {sub && <div className="mt-1 text-sm text-ink-2">{sub}</div>}
    </div>
  )
}

export function Loading() {
  return <p className="py-16 text-center text-lg text-ink-2">Loading…</p>
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-lg border border-critical/40 bg-critical/5 p-5">
      <p className="font-semibold text-critical">Could not load data</p>
      <p className="mt-1 text-ink-2">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 rounded-md bg-navy-900 px-4 py-2 font-medium text-white hover:bg-navy-800">
          Try again
        </button>
      )}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed border-line py-12 text-center text-lg text-ink-2">{children}</p>
}

/** Renders loading / error / empty states, then `children(data)`. Refetches hold the previous render, dimmed. */
export function Async<T>({
  state,
  isEmpty,
  empty,
  children,
}: {
  state: ApiState<T>
  isEmpty?: (data: T) => boolean
  empty?: ReactNode
  children: (data: T) => ReactNode
}) {
  if (state.error) return <ErrorBox message={state.error} onRetry={state.reload} />
  if (state.data === undefined) return <Loading />
  if (isEmpty?.(state.data)) return <Empty>{empty ?? 'No data yet.'}</Empty>
  return <div className={state.loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>{children(state.data)}</div>
}

/** The table-view twin of a chart: every charted value is readable without hover or colour. */
export function DataTable({ columns, rows }: { columns: string[]; rows: ReactNode[][] }) {
  return (
    <details className="mt-4">
      <summary className="cursor-pointer font-medium text-navy-800 hover:underline">View as table</summary>
      <div className="mt-3 max-h-96 overflow-auto rounded-md border border-line">
        <table className="tnum w-full text-left">
          <thead className="sticky top-0 bg-wash">
            <tr>
              {columns.map((c) => (
                <th key={c} className="px-4 py-2 font-semibold">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t border-line">
                {row.map((cell, j) => (
                  <td key={j} className="px-4 py-2">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

export function RouteSelect({ routes, value, onChange }: { routes: Route[]; value: number; onChange: (id: number) => void }) {
  return (
    <label className="flex items-center gap-3 font-medium">
      Route
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded-md border border-ink-2/40 bg-white px-3 py-2 text-lg"
      >
        {routes.map((r) => (
          <option key={r.id} value={r.id}>
            {r.label} · weight {Math.round(r.dgca_weight * 100)}%
          </option>
        ))}
      </select>
    </label>
  )
}

const SEVERITY: Record<Severity, { icon: string; label: string; color: string }> = {
  high: { icon: '▲', label: 'High', color: 'var(--color-critical)' },
  medium: { icon: '◆', label: 'Medium', color: 'var(--color-serious)' },
  low: { icon: '●', label: 'Low', color: 'var(--color-warning)' },
}

/** Status colour never carries meaning alone: icon + label + colour. */
export function SeverityBadge({ severity }: { severity: Severity }) {
  const s = SEVERITY[severity]
  return (
    <span className="inline-flex items-center gap-2 font-semibold">
      <span aria-hidden style={{ color: s.color }}>
        {s.icon}
      </span>
      {s.label}
    </span>
  )
}
