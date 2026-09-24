import { useEffect, useState } from 'react'
import { api } from './api'
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

export default function App() {
  const [view, go] = useHashView()
  const routes = useApi(api.routes, [])
  const anomalies = useApi(api.anomalies, [])
  const [routeId, setRouteId] = useState<number>()
  const selectedRoute = routeId ?? routes.data?.[0]?.id

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

      <nav className="border-b border-line bg-white">
        <ul className="mx-auto flex max-w-[1400px] flex-wrap px-6">
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
      </nav>

      <main className="mx-auto max-w-[1400px] px-6 py-8">
        {view === 'national' && <NationalView anomalies={anomalies.data} />}
        {(view === 'routes' || view === 'yield') && (
          <Async state={routes} isEmpty={(r) => r.length === 0} empty="No routes yet. Seed the database: uv run python -m app.seed">
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
