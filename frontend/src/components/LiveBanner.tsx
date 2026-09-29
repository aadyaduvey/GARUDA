import type { Status } from '../api'
import { fmtDate, fmtDay, parseDate } from '../format'

const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

/** Explains what the live index is and how far its base week has got. */
export function LiveBanner({ status }: { status: Status | undefined }) {
  const days = status?.days_collected ?? 0
  const base = status?.base_days ?? 7
  let progress = 'No live fares collected yet.'
  if (status?.first_period && days < base) {
    progress = `Building the base week: day ${days} of ${base}. Until it is complete the base keeps moving, so values are provisional.`
  } else if (status?.first_period) {
    const start = parseDate(status.first_period)
    const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + base - 1)
    progress = `Base week ${fmtDay(status.first_period)} – ${fmtDate(isoDay(end))} = 100.`
  }

  return (
    <section className="mb-6 rounded-lg border border-accent/40 bg-accent/5 px-5 py-4">
      <p className="font-semibold text-navy-900">
        <span className="mr-2 rounded bg-accent px-2 py-0.5 text-sm font-bold tracking-wide text-white">LIVE</span>
        Real fares from Akasa Air and SpiceJet (6.7% of domestic passengers, DGCA Aug 2026), collected every time GARUDA
        starts and every 6 hours while it runs.
      </p>
      <p className="mt-1 text-ink-2">{progress}</p>
    </section>
  )
}
