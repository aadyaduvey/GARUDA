// Shared chart styling. Categorical slots 1-4 validated on white (dataviz validator: all
// checks pass; aqua/yellow sit below 3:1, so charts carry direct end labels + a table view).

export const C = {
  series: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100'],
  critical: '#d03b3b',
  ink: '#0b0b0b',
  ink2: '#52514e',
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  surface: '#ffffff',
}

export const CHART_HEIGHT = 380

export const axisProps = {
  tick: { fill: C.ink2, fontSize: 15 },
  tickLine: false,
  tickMargin: 8,
  axisLine: { stroke: C.axis },
} as const

export const gridProps = { vertical: false, stroke: C.grid } as const

/** Line `label` renderer that writes a value only at the last point (selective direct labelling). */
export function endLabel(lastIndex: number, text: (value: number) => string) {
  return (props: unknown) => {
    const { x, y, index, value } = props as { x?: number; y?: number; index?: number; value?: number }
    if (index !== lastIndex || x === undefined || y === undefined || value === undefined) return <g />
    return (
      <text x={x + 10} y={y} dy={5} fill={C.ink} fontSize={15} fontWeight={600}>
        {text(value)}
      </text>
    )
  }
}
