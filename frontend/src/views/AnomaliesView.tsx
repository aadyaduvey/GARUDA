import type { Anomaly } from '../api'
import { Async, Card, SeverityBadge } from '../components/ui'
import { fmtDate, fmtIndex } from '../format'
import type { ApiState } from '../useApi'

export function AnomaliesView({ anomalies, onOpenRoute }: { anomalies: ApiState<Anomaly[]>; onOpenRoute: (routeId: number) => void }) {
  return (
    <Card
      title="Anomaly alerts"
      subtitle="A route is flagged when its index is more than 2 standard deviations above its previous 7 days and at least 5% higher. Severity: high ≥ 25% rise, medium ≥ 10%, low < 10%."
    >
      <Async state={anomalies} isEmpty={(d) => d.length === 0} empty="No anomalies flagged in the collected period.">
        {(rows) => (
          <div className="overflow-x-auto rounded-md border border-line">
            <table className="tnum w-full text-left text-lg">
              <thead className="bg-wash">
                <tr>
                  {['Date', 'Route', 'Route index', 'Rise vs 7-day mean', 'z-score', 'Severity'].map((c) => (
                    <th key={c} className="px-5 py-3 font-semibold">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={`${a.route_id}-${a.period}`} className="border-t border-line">
                    <td className="px-5 py-3">{fmtDate(a.period)}</td>
                    <td className="px-5 py-3">
                      <button onClick={() => onOpenRoute(a.route_id)} className="font-semibold text-navy-800 hover:underline">
                        {a.route}
                      </button>
                    </td>
                    <td className="px-5 py-3">{fmtIndex(a.jevons_index)}</td>
                    <td className="px-5 py-3">+{a.rise_pct.toFixed(1)}%</td>
                    <td className="px-5 py-3">{a.z_score.toFixed(1)}</td>
                    <td className="px-5 py-3">
                      <SeverityBadge severity={a.severity} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Async>
    </Card>
  )
}
