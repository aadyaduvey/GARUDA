// Typed client for the GARUDA API. Types mirror backend/app/schemas.py.

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8010'

/** demo = synthetic seed (stable numbers); live = real scraped fares, collected daily. */
export type Dataset = 'demo' | 'live'
let dataset: Dataset = 'demo'
/** Every request is sent for this dataset. App sets it before rendering and on each switch. */
export const setDataset = (d: Dataset) => {
  dataset = d
}

/** What to tell the viewer when the current dataset has nothing to show yet. */
export const noDataHint = () =>
  dataset === 'live'
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

async function get(path: string): Promise<Response> {
  const url = new URL(`${API_URL}${path}`)
  url.searchParams.set('dataset', dataset)
  let response: Response
  try {
    response = await fetch(url)
  } catch {
    throw new Error(`Cannot reach the GARUDA API at ${API_URL}. Start everything with 'pnpm start' in the project folder.`)
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
  cpiCsv: async (start: string, end: string) =>
    (await get(`/api/export/cpi?${new URLSearchParams({ start, end })}`)).text(),
}
