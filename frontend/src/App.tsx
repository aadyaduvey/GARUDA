import { useEffect, useRef, useState } from 'react'
import { type Dataset, type Status, api, noDataHint, setDataset } from './api'
import { LiveBanner } from './components/LiveBanner'
import { Counters, MainNav, NewsTicker, PageTitle, SiteFooter, SiteHeader, TopStrip } from './components/portal'
import { StatusStrip } from './components/StatusStrip'
import { Async } from './components/ui'
import { fmtIndex, fmtMonth } from './format'
import { useApi } from './useApi'
import { AnomaliesView } from './views/AnomaliesView'
import { ExportView } from './views/ExportView'
import { NationalView } from './views/NationalView'
import { RouteExplorer } from './views/RouteExplorer'
import { YieldCurveView } from './views/YieldCurveView'

const VIEWS = [
  { id: 'national', label: 'National Index', description: 'The national domestic airfare sub-index, ready for CPI Division 07 (Transport).' },
  { id: 'routes', label: 'Route Explorer', description: 'The Jevons index and average fare by carrier for each of the 10 basket routes.' },
  { id: 'yield', label: 'Yield Curve', description: 'How fares rise as departure approaches: booking 30, 14, 7 and 1 days ahead.' },
  { id: 'anomalies', label: 'Anomaly Alerts', description: 'Routes whose index rose more than 2σ and 5% above their previous week.' },
  { id: 'export', label: 'CPI Export', description: 'Download the index in the shape MoSPI’s CPI series consumes.' },
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
  const official = useApi(api.official, [dataset, refresh])
  const status = useApi(api.status, [dataset])
  const [routeId, setRouteId] = useState<number>()
  const selectedRoute = routeId ?? routes.data?.[0]?.id
  const current = VIEWS.find((v) => v.id === view)!

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

  const fares = status.data ? Object.values(status.data.fares_by_source).reduce((a, b) => a + b, 0) : undefined
  const latestOfficial = official.data?.available ? official.data.series.at(-1) : undefined

  return (
    <div className="flex min-h-screen flex-col">
      <TopStrip />
      <SiteHeader>
        <div role="group" aria-label="Dataset" className="flex rounded-md border border-navy-800/40 p-0.5">
          {(['demo', 'live'] as const).map((d) => (
            <button
              key={d}
              onClick={() => switchDataset(d)}
              aria-pressed={dataset === d}
              className={`rounded px-3 py-1.5 font-medium ${dataset === d ? 'bg-navy-900 text-white' : 'text-ink-2 hover:text-navy-900'}`}
            >
              {d === 'demo' ? 'Demo data' : 'Live data'}
            </button>
          ))}
        </div>
      </SiteHeader>
      <MainNav
        items={VIEWS.map((v) => ({ id: v.id, label: v.label, badge: v.id === 'anomalies' ? anomalies.data?.length : undefined }))}
        current={view}
        onSelect={go}
      />
      <NewsTicker status={status.data} official={official.data} dataset={dataset} />
      <StatusStrip status={status.data} />
      <PageTitle title={current.label} description={current.description} onHome={view === 'national' ? undefined : () => go('national')} />

      <main id="main" tabIndex={-1} key={`${dataset}-${refresh}`} className="mx-auto w-full max-w-[1400px] flex-1 px-6 py-8 outline-none">
        {view === 'national' && (
          <div className="mb-6">
            <Counters
              items={[
                { value: fares?.toLocaleString('en-IN') ?? '—', label: 'Fares collected', sub: dataset === 'live' ? 'real, Akasa Air + SpiceJet' : 'synthetic demo' },
                { value: status.data?.days_collected ?? '—', label: 'Days of index', sub: `first ${status.data?.base_days ?? 7} form the base` },
                { value: routes.data?.length ?? '—', label: 'Routes in basket', sub: 'busiest domestic routes' },
                {
                  value: latestOfficial ? fmtIndex(latestOfficial.index) : '—',
                  label: 'Official CPI airfare',
                  sub: latestOfficial ? `MoSPI, ${fmtMonth(latestOfficial.month)} (2024 = 100)` : 'MoSPI, not loaded',
                },
              ]}
            />
          </div>
        )}
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
      <SiteFooter lastUpdated={status.data?.latest_period ?? null} />
    </div>
  )
}
