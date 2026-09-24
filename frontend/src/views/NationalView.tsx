import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { type Anomaly, api } from '../api'
import { TooltipCard } from '../components/chart'
import { C, CHART_HEIGHT, axisProps, endLabel, gridProps } from '../components/chartTheme'
import { Async, Card, DataTable, StatTile } from '../components/ui'
import { fmtDate, fmtDay, fmtIndex, fmtSigned, niceScale } from '../format'
import { useApi } from '../useApi'

export function NationalView({ anomalies }: { anomalies: Anomaly[] | undefined }) {
  const national = useApi(api.national, [])

  return (
    <Async state={national} isEmpty={(d) => d.series.length === 0} empty="No index values yet. Seed the database: uv run python -m app.seed">
      {({ series, latest, base_period }) => {
        const last = latest!
        const prev = series.at(-2)
        const peak = series.reduce((a, b) => (b.national_index > a.national_index ? b : a))
        const baseLabel = base_period ? `${fmtDay(base_period.start)} – ${fmtDate(base_period.end)}` : '—'
        return (
          <div className="space-y-6">
            <section className="rounded-lg border border-line bg-wash px-8 py-6">
              <div className="text-lg text-ink-2">National domestic airfare index</div>
              <div className="mt-1 text-7xl font-semibold text-navy-900">{fmtIndex(last.national_index)}</div>
              <div className="mt-2 text-lg text-ink-2">
                on {fmtDate(last.period)} · base period {baseLabel} = 100
              </div>
            </section>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatTile
                label="Change vs previous day"
                value={prev ? fmtSigned(last.national_index - prev.national_index) : '—'}
                sub={prev ? `from ${fmtIndex(prev.national_index)} on ${fmtDay(prev.period)}` : undefined}
              />
              <StatTile label="Highest in period" value={fmtIndex(peak.national_index)} sub={`on ${fmtDate(peak.period)}`} />
              <StatTile
                label="Route anomaly alerts"
                value={anomalies ? anomalies.length : '—'}
                sub={anomalies?.[0] ? `latest: ${anomalies[0].route} on ${fmtDay(anomalies[0].period)}` : 'none flagged'}
              />
            </div>

            <Card
              title="National index over time"
              subtitle="Weighted by DGCA passenger traffic across the 10-route basket (Jevons within each route)"
            >
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <LineChart data={series} margin={{ top: 12, right: 72, bottom: 4, left: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="period" tickFormatter={fmtDay} {...axisProps} minTickGap={24} />
                  <YAxis {...axisProps} width={56} {...niceScale(series.map((p) => p.national_index), 100)} />
                  <ReferenceLine
                    y={100}
                    stroke={C.axis}
                    label={{ value: 'Base = 100', position: 'insideBottomLeft', fill: C.ink2, fontSize: 14 }}
                  />
                  <Tooltip
                    cursor={{ stroke: C.axis }}
                    content={({ active, payload, label }) =>
                      active && payload?.length ? (
                        <TooltipCard
                          title={fmtDate(String(label))}
                          rows={[{ name: 'National index', value: fmtIndex(Number(payload[0].value)), color: C.series[0] }]}
                        />
                      ) : null
                    }
                  />
                  <Line
                    dataKey="national_index"
                    name="National index"
                    stroke={C.series[0]}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6, stroke: C.surface, strokeWidth: 2 }}
                    label={endLabel(series.length - 1, fmtIndex)}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
              <DataTable
                columns={['Date', 'National index']}
                rows={series.map((p) => [fmtDate(p.period), fmtIndex(p.national_index)])}
              />
            </Card>
          </div>
        )
      }}
    </Async>
  )
}
