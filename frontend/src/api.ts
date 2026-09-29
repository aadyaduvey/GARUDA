// Typed client for the GARUDA API. Types mirror backend/app/schemas.py.

// Empty = same origin: the Vite dev server proxies /api to the backend (see vite.config.ts).
export const API_URL: string = import.meta.env.VITE_API_URL ?? ''

/** demo = synthetic seed (stable numbers); live = real scraped fares, collected daily. */
export type Dataset = 'demo' | 'live'
let dataset: Dataset = 'demo'
/** Every request is sent for this dataset. App sets it before rendering and on each switch. */
export const setDataset = (d: Dataset) => {
  dataset = d
}

/** Published website (`vite build --mode static`): read exported snapshot files, no API server. */
export const STATIC = import.meta.env.VITE_STATIC === '1'

/** What to tell the viewer when the current dataset has nothing to show yet. */
export const noDataHint = () =>
  STATIC
    ? 'This published copy has no data for this view yet.'
    : dataset === 'live'
      ? 'No live fares yet. Run `pnpm scrape`, or keep `pnpm start` running: it collects every day at 06:00 IST.'
      : 'No index values yet. Seed the demo data with `pnpm reseed`.'

export type Route = { id: number; origin: string; destination: string; label: string; dgca_weight: number }
export type BasePeriod = { start: string; end: string }

export type NationalPoint = { period: string; national_index: number }
export type NationalIndex = { base_period: BasePeriod | null; latest: NationalPoint | null; series: NationalPoint[] }

export type RoutePoint = { period: string; jevons_index: number; anomaly_flag: boolean }
export type Carrier = { airline: string; code: string; market_share: number; avg_fare: number }
export type RouteIndex = { route: Route; base_period: BasePeriod | null; series: RoutePoint[]; carriers: Carrier[] }

export type Severity = 'low' | 'medium' | 'high'
export type Anomaly = {
  route_id: number
  route: string
  period: string
  jevons_index: number
  z_score: number
  rise_pct: number
  severity: Severity
}

export type YieldPoint = { period: string; advance_days: number; avg_fare: number }
export type YieldCurve = { route: Route; premium_1d_vs_30d: number | null; series: YieldPoint[] }

export type SourceStatus = {
  airline: string
  name: string
  status: 'ok' | 'no_data' | 'failed' | 'unavailable'
  rows: number
  inserted: number
  error: string | null
}
export type ScraperRun = { run_at: string; mode: 'live' | 'dry_run'; index_rebuilt: boolean; sources: SourceStatus[] }
export type Status = {
  dataset: Dataset
  first_period: string | null
  latest_period: string | null
  days_collected: number
  base_days: number
  fares_by_source: Record<string, number>
  last_live_fare_at: string | null
  last_run: ScraperRun | null
}

// API path -> snapshot file written by backend/app/export_snapshot.py.
const SNAPSHOT_FILES: [RegExp, (m: RegExpMatchArray) => string][] = [
  [/^\/api\/routes$/, () => 'routes.json'],
  [/^\/api\/index\/national$/, () => 'national.json'],
  [/^\/api\/anomalies$/, () => 'anomalies.json'],
  [/^\/api\/status$/, () => 'status.json'],
  [/^\/api\/export\/cpi$/, () => 'cpi.csv'],
  [/^\/api\/index\/route\/(\d+)$/, (m) => `route-${m[1]}.json`],
  [/^\/api\/yield-curve\/(\d+)$/, (m) => `yield-${m[1]}.json`],
]

async function getSnapshot(path: string): Promise<Response> {
  const bare = path.split('?')[0]
  for (const [pattern, file] of SNAPSHOT_FILES) {
    const m = bare.match(pattern)
    if (!m) continue
    const response = await fetch(`${import.meta.env.BASE_URL}snapshot/${dataset}/${file(m)}`)
    if (!response.ok) throw new Error(`This published copy has no data for ${bare}.`)
    return response
  }
  throw new Error(`This published copy has no data for ${bare}.`)
}

async function get(path: string): Promise<Response> {
  if (STATIC) return getSnapshot(path)
  const url = new URL(`${API_URL}${path}`, window.location.origin)
  url.searchParams.set('dataset', dataset)
  let response: Response
  try {
    response = await fetch(url)
  } catch {
    throw new Error(`Cannot reach the GARUDA API${API_URL ? ` at ${API_URL}` : ''}. Start everything with 'pnpm start' in the project folder.`)
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ? `${body.detail}` : `API error ${response.status} on ${path}`)
  }
  return response
}

const json = async <T>(path: string): Promise<T> => (await get(path)).json() as Promise<T>

export const api = {
  routes: () => json<Route[]>('/api/routes'),
  national: () => json<NationalIndex>('/api/index/national'),
  routeIndex: (id: number) => json<RouteIndex>(`/api/index/route/${id}`),
  anomalies: () => json<Anomaly[]>('/api/anomalies'),
  yieldCurve: (id: number) => json<YieldCurve>(`/api/yield-curve/${id}`),
  status: () => json<Status>('/api/status'),
  cpiCsv: async (start: string, end: string) => {
    if (!STATIC) return (await get(`/api/export/cpi?${new URLSearchParams({ start, end })}`)).text()
    // The snapshot holds the full CSV; keep the header plus rows whose period (column 2) is in range.
    const [header, ...rows] = (await (await get('/api/export/cpi')).text()).trim().split('\n')
    const inRange = rows.filter((row) => {
      const period = row.split(',')[1]
      return period >= start && period <= end
    })
    return [header, ...inRange].join('\n') + '\n'
  },
  /** When the published copy was exported (static mode only). */
  snapshotMeta: async () => (await fetch(`${import.meta.env.BASE_URL}snapshot/meta.json`)).json() as Promise<{ generated_at: string }>,
}
