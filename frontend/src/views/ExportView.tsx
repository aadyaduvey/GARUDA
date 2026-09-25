import { useState } from 'react'
import { api, noDataHint } from '../api'
import { Async, Card, ErrorBox, Loading } from '../components/ui'
import { useApi } from '../useApi'

const PREVIEW_ROWS = 25

function parseCsv(text: string): string[][] {
  return text
    .trim()
    .split('\n')
    .filter(Boolean)
    .map((line) => line.split(','))
}

function download(csv: string, filename: string) {
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}

function ExportForm({ minDate, maxDate }: { minDate: string; maxDate: string }) {
  const [start, setStart] = useState(minDate)
  const [end, setEnd] = useState(maxDate)
  const invalid = start > end
  const csv = useApi(() => (invalid ? Promise.resolve('') : api.cpiCsv(start, end)), [start, end])

  const [header, ...rows] = csv.data ? parseCsv(csv.data) : [[]]
  const inputClass = 'rounded-md border border-ink-2/40 bg-white px-3 py-2 text-lg'

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 font-medium">
          From
          <input type="date" value={start} min={minDate} max={maxDate} onChange={(e) => setStart(e.target.value)} className={inputClass} />
        </label>
        <label className="flex flex-col gap-1 font-medium">
          To
          <input type="date" value={end} min={minDate} max={maxDate} onChange={(e) => setEnd(e.target.value)} className={inputClass} />
        </label>
        <button
          disabled={invalid || !csv.data || rows.length === 0}
          onClick={() => csv.data && download(csv.data, `garuda_cpi_${start}_${end}.csv`)}
          className="rounded-md bg-navy-900 px-6 py-2.5 text-lg font-semibold text-white hover:bg-navy-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Download CSV
        </button>
      </div>

      {invalid ? (
        <ErrorBox message="The start date must be on or before the end date." />
      ) : csv.error ? (
        <ErrorBox message={csv.error} onRetry={csv.reload} />
      ) : !csv.data ? (
        <Loading />
      ) : rows.length === 0 ? (
        <p className="text-lg text-ink-2">No index values in this range. The CSV would contain the header row only.</p>
      ) : (
        <div className={csv.loading ? 'opacity-60' : ''}>
          <p className="mb-2 text-ink-2">
            {rows.length} rows · showing the first {Math.min(PREVIEW_ROWS, rows.length)}
          </p>
          <div className="overflow-x-auto rounded-md border border-line">
            <table className="tnum w-full text-left">
              <thead className="bg-wash">
                <tr>
                  {header.map((h) => (
                    <th key={h} className="px-4 py-2 font-mono font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, PREVIEW_ROWS).map((r, i) => (
                  <tr key={i} className={`border-t border-line ${r[0] === 'NATIONAL' ? 'bg-wash font-semibold' : ''}`}>
                    {r.map((cell, j) => (
                      <td key={j} className="px-4 py-2 font-mono">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export function ExportView() {
  const national = useApi(api.national, [])
  return (
    <Card
      title="CPI export"
      subtitle="Route and national index values in MoSPI's CPI format: route, period, index_value, weight, base_period. One NATIONAL row per day follows the route rows."
    >
      <Async state={national} isEmpty={(d) => d.series.length === 0} empty={noDataHint()}>
        {(d) => {
          const [minDate, maxDate] = [d.series[0].period, d.series[d.series.length - 1].period]
          // Keyed on the range so the form resets if the data changes (e.g. after a reseed).
          return <ExportForm key={`${minDate}/${maxDate}`} minDate={minDate} maxDate={maxDate} />
        }}
      </Async>
    </Card>
  )
}
