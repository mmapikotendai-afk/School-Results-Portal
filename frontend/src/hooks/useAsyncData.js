import { useCallback, useEffect, useRef, useState } from 'react'

import { getErrorMessage } from '@/services/apiClient'

/**
 * Load data from the API, with loading and error state.
 *
 * Late responses are discarded: if a second request starts before the first
 * returns, only the newest one is allowed to write to state, so a slow reply
 * to an old search cannot overwrite fresher results.
 */
export function useAsyncData(loader, deps = [], { immediate = true } = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState(null)
  const requestId = useRef(0)

  const run = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    try {
      const result = await loader()
      if (id !== requestId.current) return null
      setData(result)
      setError(null)
      return result
    } catch (err) {
      if (id === requestId.current) {
        setError(getErrorMessage(err))
      }
      return null
    } finally {
      if (id === requestId.current) setLoading(false)
    }
    // The caller controls invalidation through deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    if (!immediate) return
    run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, immediate])

  return { data, loading, error, refresh: run, setData }
}

export default useAsyncData
