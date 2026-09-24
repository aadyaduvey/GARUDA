import { type DependencyList, useCallback, useEffect, useState } from 'react'

export type ApiState<T> = { data?: T; error?: string; loading: boolean; reload: () => void }

/** Fetch on mount and whenever `deps` change. Keeps the previous data while refetching. */
export function useApi<T>(load: () => Promise<T>, deps: DependencyList): ApiState<T> {
  const [data, setData] = useState<T>()
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(undefined)
    load()
      .then((d) => !cancelled && setData(d))
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { data, error, loading, reload }
}
