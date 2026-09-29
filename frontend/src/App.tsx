import { useEffect, useRef, useState } from 'react'
import { type Dataset, type Status, STATIC, api, noDataHint, setDataset } from './api'
import { LiveBanner } from './components/LiveBanner'
import { StatusStrip } from './components/StatusStrip'
import { Async } from './components/ui'
import { useApi } from './useApi'
import { AnomaliesView } from './views/AnomaliesView'
import { ExportView } from './views/ExportView'
import { NationalView } from './views/NationalView'
import { RouteExplorer } from './views/RouteExplorer'
import { YieldCurveView } from './views/YieldCurveView'

const VIEWS = [
  { id: 'national', label: 'National Index' },
  { id: 'routes', label: 'Route Explorer' },
  { id: 'yield', label: 'Yield Curve' },
  { id: 'anomalies', label: 'Anomaly Alerts' },
  { id: 'export', label: 'CPI Export' },
] as const
type ViewId = (typeof VIEWS)[number]['id']

const viewFromHash = (): ViewId => VIEWS.find((v) => `#${v.id}` === window.location.hash)?.id ?? 'national'

/** The current view lives in the URL hash so a refresh (or a bookmarked link) keeps it. */
function useHashView(): [ViewId, (v: ViewId) => void] {
  const [view, setView] = useState(viewFromHash)
  useEffect(() => {
    const onHash = () => setView(viewFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  return [view, (v) => (window.location.hash = v)]
}

const DATASET_KEY = 'garuda.dataset'
const STATUS_POLL_MS = 30_000

function storedDataset(): Dataset {
  try {
    return localStorage.getItem(DATASET_KEY) === 'live' ? 'live' : 'demo'
  } catch {
    return 'demo'
  }
}

const initialDataset = storedDataset()
setDataset(initialDataset)

/** Changes whenever new data lands (a scrape, a reseed), so the views know to refetch. */
const dataSignature = (s: Status | undefined) =>
  s ? `${s.latest_period}|${Object.values(s.fares_by_source).reduce((a, b) => a + b, 0)}|${s.last_run?.run_at}` : ''

export default function App() {
  const [view, go] = useHashView()
  const [dataset, setDatasetState] = useState<Dataset>(initialDataset)
  const [refresh, setRefresh] = useState(0)
  const routes = useApi(api.routes, [dataset, refresh])
  const anomalies = useApi(api.anomalies, [dataset, refresh])
  const status = useApi(api.status, [dataset])
  const snapshot = useApi(() => (STATIC ? api.snapshotMeta() : Promise.resolve(null)), [])
  const [routeId, setRouteId] = useState<number>()
  const selectedRoute = routeId ?? routes.data?.[0]?.id

  // Poll the status; when the data underneath changes, remount the views so every chart refetches.
  const { reload: reloadStatus } = status
  useEffect(() => {
    const id = window.setInterval(reloadStatus, STATUS_POLL_MS)
    return () => window.clearInterval(id)
  }, [reloadStatus])
  const signature = dataSignature(status.data)
  const lastSignature = useRef(signature)
  useEffect(() => {
    if (lastSignature.current && signature && signature !== lastSignature.current) setRefresh((n) => n + 1)
    lastSignature.current = signature
  }, [signature])

  const switchDataset = (d: Dataset) => {
    setDataset(d)
    try {
      localStorage.setItem(DATASET_KEY, d)
    } catch {
      /* private mode etc.: the choice just won't persist */
    }
    lastSignature.current = ''
    setRouteId(undefined)
    setDatasetState(d)
  }

  return (
    <div className="min-h-screen">
      <header className="bg-navy-900 text-white">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-baseline justify-between gap-x-8 gap-y-1 px-6 py-5">
          <div>
            <h1 className="text-3xl font-bold tracking-wide">GARUDA</h1>
            <p className="text-lg text-white/85">Real-time Airfare Price Index · domestic sub-index for CPI Division 07</p>
          </div>
          <p className="text-white/75">Prototype for MoSPI · Smart India Hackathon SIH26056</p>
        </div>
      </header>
      <StatusStrip status={status.data} publishedAt={snapshot.data?.generated_at} />

      <nav className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-x-6 px-6">
          <ul className="flex flex-wrap">
            {VIEWS.map((v) => (
              <li key={v.id}>
                <button
                  onClick={() => go(v.id)}
                  aria-current={view === v.id ? 'page' : undefined}
                  className={`border-b-4 px-4 py-3 text-lg font-medium transition-colors ${
                    view === v.id ? 'border-accent text-navy-900' : 'border-transparent text-ink-2 hover:text-navy-900'
                  }`}
                >
                  {v.label}
                  {v.id === 'anomalies' && anomalies.data && anomalies.data.length > 0 && (
                    <span className="ml-2 rounded-full bg-critical px-2 py-0.5 text-sm font-semibold text-white">{anomalies.data.length}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          <div role="group" aria-label="Dataset" className="my-2 flex rounded-md border border-navy-800/40 p-0.5">
            {(['demo', 'live'] as const).map((d) => (
              <button
                key={d}
                onClick={() => switchDataset(d)}
                aria-pressed={dataset === d}
                className={`rounded px-3 py-1.5 font-medium ${dataset === d ? 'bg-navy-900 text-white' : 'text-ink-2 hover:text-navy-900'}`}
              >
                {d === 'demo' ? 'Demo data' : 'Live · Akasa'}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <main key={`${dataset}-${refresh}`} className="mx-auto max-w-[1400px] px-6 py-8">
        {dataset === 'live' && <LiveBanner status={status.data} />}
        {view === 'national' && <NationalView anomalies={anomalies.data} />}
        {(view === 'routes' || view === 'yield') && (
          <Async state={routes} isEmpty={(r) => r.length === 0} empty={noDataHint()}>
            {(list) => {
              const View = view === 'routes' ? RouteExplorer : YieldCurveView
              return <View routes={list} routeId={selectedRoute ?? list[0].id} onRouteChange={setRouteId} />
            }}
          </Async>
        )}
        {view === 'anomalies' && (
          <AnomaliesView
            anomalies={anomalies}
            onOpenRoute={(id) => {
              setRouteId(id)
              go('routes')
            }}
          />
        )}
        {view === 'export' && <ExportView />}
      </main>
    </div>
  )
}
