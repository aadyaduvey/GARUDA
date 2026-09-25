import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { type Route, type YieldPoint, api } from '../api'
import { Legend, TooltipCard } from '../components/chart'
import { C, CHART_HEIGHT, axisProps, endLabel, gridProps } from '../components/chartTheme'
import { Async, Card, DataTable, RouteSelect, StatTile } from '../components/ui'
import { fmtDate, fmtDay, fmtINR, niceScale } from '../format'
import { useApi } from '../useApi'

// Fixed slot per window, so a colour always means the same booking window. Only the two
// ends of the curve (the premium story) get direct labels; 7d/14d run close together and
// are read from the legend, tooltip and table.
const WINDOWS = [
  { days: 1, name: '1 day ahead', color: C.series[0], endLabel: true },
  { days: 7, name: '7 days ahead', color: C.series[1], endLabel: false },
  { days: 14, name: '14 days ahead', color: C.series[2], endLabel: false },
  { days: 30, name: '30 days ahead', color: C.series[3], endLabel: true },
]
const key = (days: number) => `d${days}`

/** One row per period with a column per booking window: { period, d1, d7, d14, d30 }. */
function toWide(series: YieldPoint[]) {
  const rows = new Map<string, Record<string, number | string>>()
  for (const p of series) {
    const row = rows.get(p.period) ?? { period: p.period }
    row[key(p.advance_days)] = p.avg_fare
    rows.set(p.period, row)
  }
  return [...rows.values()]
}

export function YieldCurveView({ routes, routeId, onRouteChange }: { routes: Route[]; routeId: number; onRouteChange: (id: number) => void }) {
  const curve = useApi(() => api.yieldCurve(routeId), [routeId])

  return (
    <div className="space-y-6">
      <RouteSelect routes={routes} value={routeId} onChange={onRouteChange} />
      <Async state={curve} isEmpty={(d) => d.series.length === 0} empty="No fares collected for this route yet.">
        {({ route, series, premium_1d_vs_30d }) => {
          const wide = toWide(series)
          const latest = wide[wide.length - 1]
          const fare = (days: number) => Number(latest[key(days)])
          const scale = niceScale(series.map((p) => p.avg_fare), 0)
          // End labels only when the 1d and 30d lines end far enough apart not to collide.
          const labelsFit = Math.abs(fare(1) - fare(30)) / (scale.domain[1] - scale.domain[0]) > 0.06
          return (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <StatTile
                  label="Last-minute premium"
                  value={premium_1d_vs_30d ? `${premium_1d_vs_30d.toFixed(2)}×` : '—'}
                  sub="1-day fare vs 30-day fare, whole period"
                />
                <StatTile label="Booked 30 days ahead" value={fmtINR(fare(30))} sub={`average fare, ${fmtDate(String(latest.period))}`} />
                <StatTile label="Booked 1 day ahead" value={fmtINR(fare(1))} sub={`average fare, ${fmtDate(String(latest.period))}`} />
              </div>

              <Card title={`${route.label} fares by booking window`} subtitle="Average economy fare across carriers, by how far ahead the ticket is bought">
                <Legend items={WINDOWS} />
                <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                  <LineChart data={wide} margin={{ top: 12, right: 130, bottom: 4, left: 8 }}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="period" tickFormatter={fmtDay} {...axisProps} minTickGap={24} />
                    <YAxis {...axisProps} width={80} {...scale} tickFormatter={fmtINR} />
                    <Tooltip
                      cursor={{ stroke: C.axis }}
                      content={({ active, payload, label }) =>
                        active && payload?.length ? (
                          <TooltipCard
                            title={fmtDate(String(label))}
                            rows={payload.map((p) => ({ name: String(p.name), value: fmtINR(Number(p.value)), color: String(p.color) }))}
                          />
                        ) : null
                      }
                    />
                    {WINDOWS.map((w) => (
                      <Line
                        key={w.days}
                        dataKey={key(w.days)}
                        name={w.name}
                        stroke={w.color}
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 5, stroke: C.surface, strokeWidth: 2 }}
                        label={w.endLabel && labelsFit ? endLabel(wide.length - 1, (v) => `${w.days}d · ${fmtINR(v)}`) : undefined}
                        isAnimationActive={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
                <DataTable
                  columns={['Date', ...WINDOWS.map((w) => w.name)]}
                  rows={wide.map((r) => [fmtDate(String(r.period)), ...WINDOWS.map((w) => fmtINR(Number(r[key(w.days)])))])}
                />
              </Card>
            </div>
          )
        }}
      </Async>
    </div>
  )
}
