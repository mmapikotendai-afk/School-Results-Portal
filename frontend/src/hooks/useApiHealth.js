import { useCallback, useEffect, useState } from 'react'

import systemService from '@/services/systemService'
import { getErrorMessage } from '@/services/apiClient'

/**
 * Polls the backend health endpoint.
 *
 * Used by the landing and login pages to prove - visibly - that the React app
 * and the FastAPI service are talking to each other.
 */
export function useApiHealth({ pollMs = 0 } = {}) {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const check = useCallback(async () => {
    setLoading(true)
    try {
      const data = await systemService.health()
      setHealth(data)
      setError(null)
    } catch (err) {
      setHealth(null)
      setError(getErrorMessage(err, 'Unable to reach the API.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // Fetching from the API is exactly the external-system synchronisation an
    // effect is for; the loading flag it sets is part of that request.
    // eslint-disable-next-line react/set-state-in-effect
    check()
    if (!pollMs) return undefined

    const id = window.setInterval(check, pollMs)
    return () => window.clearInterval(id)
  }, [check, pollMs])

  return { health, error, loading, refresh: check }
}

export default useApiHealth
