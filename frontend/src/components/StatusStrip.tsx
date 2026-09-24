import { useEffect } from 'react'
import { type SourceStatus, api } from '../api'
import { fmtDate, fmtTimeIST } from '../format'
import { useApi } from '../useApi'

const REFRESH_MS = 60_000

const SOURCE_LABEL: Record<string, string> = { synthetic: 'synthetic seed', akasa_lowfare: 'live Akasa Air' }

// Status colour never carries meaning alone: every state has its own icon and words.
const STATE: Record<SourceStatus['status'], { icon: string; label: string; color: string }> = {
  ok: { icon: '✓', label: 'live', color: '#0ca30c' }, // 'cached sample' after an offline replay
  no_data: { icon: '○', label: 'no fares returned', color: '#b7791f' },
  failed: { icon: '✕', label: 'failed', color: 'var(--color-critical)' },
  unavailable: { icon: '–', label: 'not scraped', color: 'var(--color-ink-2)' },
}

/** Data freshness + scraper health, refreshed every minute. Renders nothing until the API answers. */
export function StatusStrip() {
  const status = useApi(api.status, [])
  const { reload } = status
  useEffect(() => {
    const id = window.setInterval(reload, REFRESH_MS)
    return () => window.clearInterval(id)
  }, [reload])

  const s = status.data
  if (!s) return null
  const counts = Object.entries(s.fares_by_source).sort(([, a], [, b]) => b - a)
  const run = s.last_run

  return (
    <div className="border-b border-line bg-wash text-sm text-ink-2">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-6 gap-y-1 px-6 py-2">
        <span>
          <span className="font-semibold text-ink">Index through</span> {s.latest_period ? fmtDate(s.latest_period) : '—'}
        </span>
        <span className="tnum">
          <span className="font-semibold text-ink">Fares</span>{' '}
          {counts.length ? counts.map(([src, n]) => `${n.toLocaleString('en-IN')} ${SOURCE_LABEL[src] ?? src}`).join(' · ') : 'none'}
        </span>
        <span>
          <span className="font-semibold text-ink">Last scrape</span>{' '}
          {run ? `${fmtTimeIST(run.run_at)}${run.mode === 'dry_run' ? ' (offline replay)' : ''}` : 'not run yet'}
        </span>
        {run && (
          <ul className="flex flex-wrap gap-x-4">
            {run.sources.map((src) => {
              const st = STATE[src.status]
              const label = src.status === 'ok' && run.mode === 'dry_run' ? 'cached sample' : st.label
              return (
                <li key={src.airline} title={src.error ?? `${src.rows} fares, ${src.inserted} new`} className="flex items-center gap-1.5">
                  <span aria-hidden className="font-bold" style={{ color: st.color }}>
                    {st.icon}
                  </span>
                  <span className="text-ink">{src.name}</span> {label}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
