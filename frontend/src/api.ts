// Typed client for the GARUDA API. Types mirror backend/app/schemas.py.

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

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
  latest_period: string | null
  fares_by_source: Record<string, number>
  last_live_fare_at: string | null
  last_run: ScraperRun | null
}

async function get(path: string): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`)
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
