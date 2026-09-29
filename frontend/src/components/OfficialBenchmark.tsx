import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { fmtDate, fmtIndex, fmtMonth, fmtSigned, fmtTimeIST, niceScale } from '../format'
import { useApi } from '../useApi'
import { TooltipCard } from './chart'
import { C, axisProps, endLabel, gridProps } from './chartTheme'
import { Async, Card, DataTable, StatTile } from './ui'

/** MoSPI's official monthly CPI "Airfare" index (base 2024 = 100), and GARUDA chain-linked to it once they overlap. */
export function OfficialBenchmark() {
  const official = useApi(api.official, [])

  // A failure here must not look like the national index failed: keep it inside a titled card.
  if (official.error) {
    return (
      <Card title="Official benchmark: MoSPI CPI Airfare index">
        <p className="text-ink-2">
          The official series could not be loaded ({official.error}). If GARUDA was just updated, stop{' '}
          <code>pnpm start</code> with Ctrl+C and run it again.
        </p>
        <button onClick={official.reload} className="mt-3 rounded-md bg-navy-900 px-4 py-2 font-medium text-white hover:bg-navy-800">
          Try again
        </button>
      </Card>
    )
  }

  return (
    <Async
      state={official}
      isEmpty={(d) => !d.available || d.series.length === 0}
      empty="The official MoSPI CPI airfare series has not been downloaded yet. It is fetched by `pnpm start` when online."
    >
      {({ series, link, link_min_days, code, area, source_url, fetched_at }) => {
        const latest = series.at(-1)!
        return (
          <Card
            title="Official benchmark: MoSPI CPI Airfare index"
            subtitle={
              <>
                {area}, CPI item {code}, base 2024 = 100, published monthly.{' '}
                <a href={source_url} target="_blank" rel="noreferrer" className="font-medium text-navy-800 underline">
                  Source: MoSPI eSankhyiki
                </a>
                {fetched_at && ` · fetched ${fmtTimeIST(fetched_at)}`}
              </>
            }
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <StatTile
                label={`Official index, ${fmtMonth(latest.month)}`}
                value={fmtIndex(latest.index)}
                sub={latest.inflation !== null ? `${fmtSigned(latest.inflation)}% vs a year earlier` : undefined}
              />
              <StatTile
                label="GARUDA on the official 2024 = 100 scale"
                value={link ? fmtIndex(link.latest_value) : 'Not linked yet'}
                sub={
                  link
                    ? `on ${fmtDate(link.latest_period)}, chain-linked through ${fmtMonth(link.month)} (${link.garuda_days} days overlap)`
                    : `Needs ${link_min_days}+ days of GARUDA data inside a month MoSPI has published (latest: ${fmtMonth(latest.month)}).`
                }
              />
            </div>
            <div className="mt-6">
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={series} margin={{ top: 12, right: 72, bottom: 4, left: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="month" tickFormatter={fmtMonth} {...axisProps} minTickGap={24} />
                  <YAxis {...axisProps} width={68} {...niceScale(series.map((p) => p.index), 100)} />
                  <ReferenceLine y={100} stroke={C.axis} label={{ value: '2024 = 100', position: 'insideBottomLeft', fill: C.ink2, fontSize: 14 }} />
                  <Tooltip
                    cursor={{ stroke: C.axis }}
                    content={({ active, payload, label }) =>
                      active && payload?.length ? (
                        <TooltipCard
                          title={fmtMonth(String(label))}
                          rows={[{ name: 'Official CPI airfare', value: fmtIndex(Number(payload[0].value)), color: C.series[1] }]}
                        />
                      ) : null
                    }
                  />
                  <Line
                    dataKey="index"
                    name="Official CPI airfare"
                    stroke={C.series[1]}
                    strokeWidth={2}
                    dot={{ r: 3, fill: C.series[1] }}
                    label={endLabel(series.length - 1, fmtIndex)}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <DataTable
              columns={['Month', 'Official index', 'Change vs a year earlier']}
              rows={series.map((p) => [fmtMonth(p.month), fmtIndex(p.index), p.inflation !== null ? `${fmtSigned(p.inflation)}%` : '—'])}
            />
          </Card>
        )
      }}
    </Async>
  )
}
