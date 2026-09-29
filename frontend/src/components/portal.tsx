// Government-portal chrome in the style of Indian government sites (GIGW conventions: skip link,
// text resizing, bilingual title, news ticker, dark footer). GARUDA is a prototype, not an official
// site, so it carries no State Emblem or ministry logos and says so in the top strip and footer.
import { type CSSProperties, type ReactNode, useEffect, useState } from 'react'
import type { Official, Status } from '../api'
import { fmtDate, fmtIndex, fmtMonth, fmtSigned, fmtTimeIST } from '../format'

const REPO_URL = 'https://github.com/aadyaduvey/GARUDA'
const TEXT_SIZE_KEY = 'garuda.textSize'
type TextSize = 'small' | 'normal' | 'large'

function useTextSize(): [TextSize, (s: TextSize) => void] {
  const [size, setSize] = useState<TextSize>(() => {
    try {
      const saved = localStorage.getItem(TEXT_SIZE_KEY)
      return saved === 'small' || saved === 'large' ? saved : 'normal'
    } catch {
      return 'normal'
    }
  })
  useEffect(() => {
    if (size === 'normal') delete document.documentElement.dataset.textSize
    else document.documentElement.dataset.textSize = size
    try {
      localStorage.setItem(TEXT_SIZE_KEY, size)
    } catch {
      /* the choice just won't persist */
    }
  }, [size])
  return [size, setSize]
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = () => setReduced(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return reduced
}

/** Thin top strip: who this is for, skip link, text size. */
export function TopStrip() {
  const [size, setSize] = useTextSize()
  const sizes: { id: TextSize; label: string; name: string }[] = [
    { id: 'small', label: 'A−', name: 'Smaller text' },
    { id: 'normal', label: 'A', name: 'Normal text' },
    { id: 'large', label: 'A+', name: 'Larger text' },
  ]
  return (
    <div className="bg-navy-900 text-sm text-white">
      <div className="tricolour h-1" aria-hidden />
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-x-6 gap-y-1 px-6 py-1.5">
        <p className="font-medium tracking-wide">
          PROTOTYPE FOR THE MINISTRY OF STATISTICS &amp; PROGRAMME IMPLEMENTATION <span className="text-white/70">(MoSPI)</span>
        </p>
        <div className="flex items-center gap-4">
          <a
            href="#main"
            onClick={(e) => {
              e.preventDefault() // the URL hash selects the view, so move focus instead of navigating
              document.getElementById('main')?.focus()
            }}
            className="underline-offset-2 hover:underline focus:underline"
          >
            Skip to main content
          </a>
          <span aria-hidden className="h-4 w-px bg-white/40" />
          <div role="group" aria-label="Text size" className="flex items-center gap-1">
            {sizes.map((s) => (
              <button
                key={s.id}
                onClick={() => setSize(s.id)}
                aria-label={s.name}
                aria-pressed={size === s.id}
                className={`min-w-8 rounded px-1.5 py-0.5 font-semibold ${size === s.id ? 'bg-white text-navy-900' : 'hover:bg-white/15'}`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/** GARUDA's own mark: a stylised bird in a ring (deliberately not a government emblem). */
function GarudaMark() {
  return (
    <svg viewBox="0 0 64 64" className="h-16 w-16 shrink-0" role="img" aria-label="GARUDA logo">
      <circle cx="32" cy="32" r="30" fill="#fff" stroke="var(--color-navy-900)" strokeWidth="3" />
      <circle cx="32" cy="32" r="24" fill="none" stroke="var(--color-saffron)" strokeWidth="1.5" strokeDasharray="3 3" />
      <path d="M12 30 C 20 22, 27 22, 32 28 C 37 22, 44 22, 52 30 C 44 28, 38 30, 32 38 C 26 30, 20 28, 12 30 Z" fill="var(--color-navy-900)" />
      <path d="M22 36 C 26 34, 29 35, 32 40 C 35 35, 38 34, 42 36 C 38 38, 35 41, 32 46 C 29 41, 26 38, 22 36 Z" fill="var(--color-india-green)" />
      <circle cx="32" cy="24" r="3" fill="var(--color-saffron)" />
    </svg>
  )
}

/** White identity band: mark, bilingual name, and the controls passed in (dataset switch). */
export function SiteHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-x-8 gap-y-3 px-6 py-4">
        <a href="#national" className="flex items-center gap-4">
          <GarudaMark />
          <div>
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-bold tracking-wide text-navy-900">GARUDA</span>
              <span lang="hi" className="text-2xl font-semibold text-navy-800">
                गरुड़
              </span>
            </div>
            <div className="text-ink-2">
              Real-time Airfare Price Index <span aria-hidden>·</span>{' '}
              <span lang="hi">वास्तविक समय हवाई किराया मूल्य सूचकांक</span>
            </div>
            <div className="text-sm text-ink-2">Domestic sub-index for CPI Division 07 (Transport)</div>
          </div>
        </a>
        <div className="flex flex-col items-end gap-2">
          <span className="rounded-full border border-navy-800/30 bg-wash px-3 py-1 text-sm font-medium text-navy-900">
            Smart India Hackathon 2026 · Problem SIH26056
          </span>
          {children}
        </div>
      </div>
    </header>
  )
}

/** Primary navigation bar. */
export function MainNav<Id extends string>({
  items,
  current,
  onSelect,
}: {
  items: readonly { id: Id; label: string; badge?: number }[]
  current: Id
  onSelect: (id: Id) => void
}) {
  return (
    <nav aria-label="Main" className="bg-navy-800 text-white">
      <ul className="mx-auto flex max-w-[1400px] flex-wrap px-6">
        {items.map((v) => (
          <li key={v.id}>
            <button
              onClick={() => onSelect(v.id)}
              aria-current={current === v.id ? 'page' : undefined}
              className={`border-b-4 px-5 py-3 text-lg font-medium transition-colors ${
                current === v.id ? 'border-saffron bg-navy-900' : 'border-transparent hover:bg-navy-700'
              }`}
            >
              {v.label}
              {!!v.badge && <span className="ml-2 rounded-full bg-critical px-2 py-0.5 text-sm font-semibold text-white">{v.badge}</span>}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}

/** Scrolling "What's new" bar built only from real data; pausable, and still for reduced-motion users. */
export function NewsTicker({ status, official, dataset }: { status: Status | undefined; official: Official | undefined; dataset: string }) {
  const [paused, setPaused] = useState(false)
  const reduced = usePrefersReducedMotion()
  const items: string[] = []
  const latestOfficial = official?.available ? official.series.at(-1) : undefined
  if (latestOfficial) {
    items.push(
      `Official CPI Airfare (MoSPI, base 2024 = 100): ${fmtMonth(latestOfficial.month)} = ${fmtIndex(latestOfficial.index)}` +
        (latestOfficial.inflation !== null ? `, ${fmtSigned(latestOfficial.inflation)}% year on year` : ''),
    )
  }
  if (status?.last_run) {
    const ok = status.last_run.sources.filter((s) => s.status === 'ok').map((s) => s.name)
    items.push(`Last live collection ${fmtTimeIST(status.last_run.run_at)}${ok.length ? `: ${ok.join(', ')}` : ''}`)
  }
  if (status?.latest_period) items.push(`${dataset === 'live' ? 'Live' : 'Demo'} index calculated through ${fmtDate(status.latest_period)}`)
  items.push('Live fares are collected on every start and every 6 hours: Akasa Air and SpiceJet')
  items.push('Method: Jevons index within routes, DGCA passenger weights across routes (Aug 2026 shares)')
  if (official?.link) items.push(`GARUDA on the official 2024 = 100 scale: ${fmtIndex(official.link.latest_value)}`)

  const list = (copy: number) =>
    items.map((text, i) => (
      <li key={`${copy}-${i}`} aria-hidden={copy > 0 || undefined} className="flex shrink-0 items-center gap-4 pr-4">
        <span>{text}</span>
        <span aria-hidden className="h-4 w-px bg-navy-800/40" />
      </li>
    ))

  return (
    <section aria-label="Latest updates" className="border-b border-navy-800/20 bg-ticker text-navy-900">
      <div className="mx-auto flex max-w-[1400px] items-center gap-3 px-6 py-2">
        <span className="shrink-0 rounded bg-navy-900 px-2 py-0.5 text-sm font-semibold tracking-wide text-white">UPDATES</span>
        {!reduced && (
          <button
            onClick={() => setPaused((p) => !p)}
            aria-label={paused ? 'Resume updates' : 'Pause updates'}
            className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-navy-900 text-xs text-white"
          >
            {paused ? '▶' : '❚❚'}
          </button>
        )}
        <div className="ticker-viewport min-w-0 flex-1 overflow-hidden">
          {reduced ? (
            <ul className="flex flex-wrap gap-y-1">{list(0)}</ul>
          ) : (
            <ul
              className="ticker-track flex w-max"
              data-paused={paused}
              style={{ '--ticker-duration': `${items.length * 12}s` } as CSSProperties}
            >
              {list(0)}
              {list(1)}
            </ul>
          )}
        </div>
      </div>
    </section>
  )
}

/** Inner-page title band with breadcrumb, as on government portals. */
export function PageTitle({ title, description, onHome }: { title: string; description: string; onHome?: () => void }) {
  return (
    <div className="border-b border-line bg-wash">
      <div className="mx-auto max-w-[1400px] px-6 py-5">
        <nav aria-label="Breadcrumb" className="text-sm text-ink-2">
          <ol className="flex items-center gap-2">
            <li>
              {onHome ? (
                <button onClick={onHome} className="text-navy-800 underline-offset-2 hover:underline">
                  Home
                </button>
              ) : (
                'Home'
              )}
            </li>
            <li aria-hidden>›</li>
            <li aria-current="page" className="font-medium text-ink">
              {title}
            </li>
          </ol>
        </nav>
        <h1 className="mt-1 text-3xl font-semibold text-navy-900">{title}</h1>
        <p className="mt-1 text-lg text-ink-2">{description}</p>
      </div>
    </div>
  )
}

/** Headline counters card (like the participation counters on MyGov), all from real data. */
export function Counters({ items }: { items: { value: ReactNode; label: string; sub?: string }[] }) {
  return (
    <section aria-label="Key figures" className="rounded-xl border border-line bg-white px-4 py-5 shadow-md">
      <ul className="grid grid-cols-2 gap-y-4 md:grid-cols-4">
        {items.map((it, i) => (
          <li key={it.label} className={`px-4 text-center ${i % 4 ? 'md:border-l md:border-line' : ''}`}>
            <div className="tnum text-3xl font-bold text-accent">{it.value}</div>
            <div className="mt-1 text-sm font-semibold tracking-wide text-ink uppercase">{it.label}</div>
            {it.sub && <div className="text-sm text-ink-2">{it.sub}</div>}
          </li>
        ))}
      </ul>
    </section>
  )
}

function FooterColumn({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-white">{title}</h2>
      <ul className="space-y-2 text-white/80">{children}</ul>
    </div>
  )
}

function ExtLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <li>
      <a href={href} target="_blank" rel="noreferrer" className="hover:text-white hover:underline">
        {children}
        <span className="sr-only"> (opens in a new tab)</span>
      </a>
    </li>
  )
}

/** Dark footer: about, method, sources, developer links, and the honest ownership line. */
export function SiteFooter({ lastUpdated }: { lastUpdated: string | null }) {
  return (
    <footer className="mt-12 bg-footer text-white">
      <div className="tricolour h-1" aria-hidden />
      <div className="mx-auto grid max-w-[1400px] gap-10 px-6 py-10 sm:grid-cols-2 lg:grid-cols-4">
        <FooterColumn title="About GARUDA">
          <li>
            A CPI-methodology-aligned daily index of Indian domestic airfares, designed so MoSPI could plug it into CPI Division 07
            (Transport).
          </li>
        </FooterColumn>
        <FooterColumn title="Methodology">
          <li>Jevons (geometric mean) index within each route</li>
          <li>DGCA passenger-traffic weights across routes</li>
          <li>Carry-forward imputation, flagged</li>
          <li>Outliers outside ₹500 – ₹50,000 dropped</li>
          <li>BLS-style plan: 1/7/14/30 days ahead, Tue and Sat</li>
        </FooterColumn>
        <FooterColumn title="Data sources">
          <ExtLink href="https://esankhyiki.mospi.gov.in/macroindicators?product=cpi">MoSPI eSankhyiki: CPI (base 2024)</ExtLink>
          <ExtLink href="https://www.dgca.gov.in/">DGCA: domestic traffic and market share</ExtLink>
          <ExtLink href="https://www.akasaair.com/">Akasa Air: public fare calendar</ExtLink>
          <ExtLink href="https://www.spicejet.com/">SpiceJet: public fare calendar</ExtLink>
        </FooterColumn>
        <FooterColumn title="Developers">
          <ExtLink href="/docs">API documentation</ExtLink>
          <li>
            <a href="#export" className="hover:text-white hover:underline">
              CPI export (CSV)
            </a>
          </li>
          <ExtLink href={REPO_URL}>Source code on GitHub</ExtLink>
        </FooterColumn>
      </div>
      <div className="border-t border-white/15">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-4 text-sm text-white/75">
          <p>
            Prototype built for Smart India Hackathon 2026, problem SIH26056 (MoSPI). Not an official Government of India website. Figures
            under “Demo data” are synthetic.
          </p>
          <p className="tnum">Last updated: {lastUpdated ? fmtDate(lastUpdated) : '—'} · refreshed every 6 hours while running</p>
        </div>
      </div>
    </footer>
  )
}
