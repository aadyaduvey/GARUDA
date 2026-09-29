import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { type Route, type RoutePoint, api } from '../api'
import { TooltipCard } from '../components/chart'
import { C, CHART_HEIGHT, axisProps, endLabel, gridProps } from '../components/chartTheme'
import { Async, Card, DataTable, RouteSelect, StatTile } from '../components/ui'
import { fmtDate, fmtDay, fmtINR, fmtIndex, fmtPct, niceScale } from '../format'
import { useApi } from '../useApi'

/** Anomaly days get a status-coloured marker plus a text label; ordinary days get no dot. */
function anomalyDot(props: unknown) {
  const { cx, cy, index, payload } = props as { cx?: number; cy?: number; index?: number; payload?: RoutePoint }
  if (!payload?.anomaly_flag || cx === undefined || cy === undefined) return <g key={`d${index}`} />
  return (
    <g key={`d${index}`}>
      <circle cx={cx} cy={cy} r={7} fill={C.critical} stroke={C.surface} strokeWidth={2} />
      <text x={cx} y={cy - 16} textAnchor="middle" fill={C.ink} fontSize={15} fontWeight={600}>
        ▲ Anomaly
      </text>
    </g>
  )
}

export function RouteExplorer({ routes, routeId, onRouteChange }: { routes: Route[]; routeId: number; onRouteChange: (id: number) => void }) {
  const detail = useApi(() => api.routeIndex(routeId), [routeId])

  return (
    <div className="space-y-6">
      <RouteSelect routes={routes} value={routeId} onChange={onRouteChange} />
      <Async state={detail} isEmpty={(d) => d.series.length === 0} empty="No index values for this route yet.">
        {({ route, series, carriers }) => {
          const last = series[series.length - 1]
          const flagged = series.filter((p) => p.anomaly_flag)
          const carrierRows = carriers.map((c) => ({ ...c, name: `${c.airline} · ${fmtPct(c.market_share)} share` }))
          return (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <StatTile label={`${route.label} route index`} value={fmtIndex(last.jevons_index)} sub={`on ${fmtDate(last.period)}`} />
                <StatTile label="Weight in national index" value={fmtPct(route.dgca_weight)} sub="share of basket passenger traffic (DGCA)" />
                <StatTile
                  label="Anomaly days"
                  value={flagged.length}
                  sub={flagged.length ? flagged.map((p) => fmtDay(p.period)).join(', ') : 'none flagged'}
                />
              </div>

              <Card title={`${route.label} index over time`} subtitle="Jevons index: geometric mean of price relatives across carriers, booking windows and days">
                <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                  <LineChart data={series} margin={{ top: 32, right: 72, bottom: 4, left: 0 }}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="period" tickFormatter={fmtDay} {...axisProps} minTickGap={24} />
                    <YAxis {...axisProps} width={68} {...niceScale(series.map((p) => p.jevons_index), 100)} />
                    <ReferenceLine y={100} stroke={C.axis} label={{ value: 'Base = 100', position: 'insideBottomLeft', fill: C.ink2, fontSize: 14 }} />
                    <Tooltip
                      cursor={{ stroke: C.axis }}
                      content={({ active, payload, label }) =>
                        active && payload?.length ? (
                          <TooltipCard
                            title={`${fmtDate(String(label))}${(payload[0].payload as RoutePoint).anomaly_flag ? ' · ▲ Anomaly' : ''}`}
                            rows={[{ name: `${route.label} index`, value: fmtIndex(Number(payload[0].value)), color: C.series[0] }]}
                          />
                        ) : null
                      }
                    />
                    <Line
                      dataKey="jevons_index"
                      stroke={C.series[0]}
                      strokeWidth={2}
                      dot={anomalyDot}
                      activeDot={{ r: 6, stroke: C.surface, strokeWidth: 2 }}
                      label={endLabel(series.length - 1, fmtIndex)}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
                <DataTable
                  columns={['Date', 'Route index', 'Anomaly']}
                  rows={series.map((p) => [fmtDate(p.period), fmtIndex(p.jevons_index), p.anomaly_flag ? '▲ Yes' : '—'])}
                />
              </Card>

              <Card title="Carrier breakdown" subtitle={`Average economy fare on ${route.label}, ${fmtDate(last.period)} (all booking windows)`}>
                {carrierRows.length === 0 ? (
                  <p className="text-ink-2">No fares collected for this route on the latest day.</p>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height={carrierRows.length * 64 + 40}>
                      <BarChart data={carrierRows} layout="vertical" margin={{ top: 4, right: 96, bottom: 4, left: 8 }}>
                        <CartesianGrid horizontal={false} stroke={C.grid} />
                        <XAxis type="number" {...axisProps} tickFormatter={fmtINR} />
                        <YAxis type="category" dataKey="name" {...axisProps} width={230} />
                        <Tooltip
                          cursor={{ fill: C.grid, opacity: 0.4 }}
                          content={({ active, payload }) =>
                            active && payload?.length ? (
                              <TooltipCard
                                title={String(payload[0].payload.name)}
                                rows={[{ name: 'Average fare', value: fmtINR(Number(payload[0].value)), color: C.series[0] }]}
                              />
                            ) : null
                          }
                        />
                        <Bar dataKey="avg_fare" fill={C.series[0]} barSize={24} radius={[0, 4, 4, 0]} isAnimationActive={false}>
                          <LabelList dataKey="avg_fare" position="right" formatter={(v: unknown) => fmtINR(Number(v))} fill={C.ink} fontSize={15} fontWeight={600} />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    <DataTable
                      columns={['Carrier', 'Code', 'Market share', 'Average fare']}
                      rows={carriers.map((c) => [c.airline, c.code, fmtPct(c.market_share), fmtINR(c.avg_fare)])}
                    />
                  </>
                )}
              </Card>
            </div>
          )
        }}
      </Async>
    </div>
  )
}
