export type TipRow = { name: string; value: string; color: string }

export function TooltipCard({ title, rows }: { title: string; rows: TipRow[] }) {
  return (
    <div className="rounded-md border border-line bg-white px-4 py-3 shadow-md">
      <div className="font-semibold">{title}</div>
      {rows.map((r) => (
        <div key={r.name} className="tnum mt-1 flex items-center gap-2 text-ink-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: r.color }} />
          <span>{r.name}</span>
          <span className="ml-auto pl-4 font-semibold text-ink">{r.value}</span>
        </div>
      ))}
    </div>
  )
}

export function Legend({ items }: { items: { name: string; color: string }[] }) {
  return (
    <ul className="mb-3 flex flex-wrap gap-x-6 gap-y-1 text-ink-2">
      {items.map((i) => (
        <li key={i.name} className="flex items-center gap-2">
          <span className="inline-block h-1 w-5 rounded-full" style={{ background: i.color }} />
          {i.name}
        </li>
      ))}
    </ul>
  )
}
