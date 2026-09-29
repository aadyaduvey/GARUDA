// ISO dates from the API are calendar dates (IST); parse them as local dates, never UTC.
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export const fmtDate = (iso: string) =>
  parseDate(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

export const fmtDay = (iso: string) => parseDate(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

/** A UTC timestamp shown as IST wall time, e.g. "25 Sept, 02:21 IST". */
export const fmtTimeIST = (iso: string) =>
  `${new Date(iso).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })} IST`

/** 'YYYY-MM' -> 'Aug 2026'. */
export const fmtMonth = (ym: string) => parseDate(`${ym}-01`).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })

export const fmtIndex = (n: number) => n.toFixed(2)

const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })
export const fmtINR = (n: number) => `₹${inr.format(n)}`

export const fmtSigned = (n: number, digits = 2) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${Math.abs(n).toFixed(digits)}`

export const fmtPct = (share: number) => `${Math.round(share * 100)}%`

/** Round axis ticks (steps of 1, 2, 2.5 or 5 x 10^n) covering the values and `include` (e.g. the base 100). */
export function niceScale(values: number[], include?: number, targetTicks = 5): { domain: [number, number]; ticks: number[] } {
  const all = include === undefined ? values : [...values, include]
  const [min, max] = [Math.min(...all), Math.max(...all)]
  const raw = (max - min || 1) / (targetTicks - 1)
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw)!
  const [lo, hi] = [Math.floor(min / step) * step, Math.ceil(max / step) * step]
  const ticks: number[] = []
  for (let t = lo; t <= hi + step / 2; t += step) ticks.push(Number(t.toFixed(10)))
  return { domain: [lo, hi], ticks }
}
