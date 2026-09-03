import { useEffect, useState } from 'react'

/**
 * Delay a fast-changing value.
 *
 * Used for search boxes, so typing a name fires one request when the user
 * pauses rather than one per keystroke.
 */
export function useDebounced(value, delay = 300) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(id)
  }, [value, delay])

  return debounced
}

export default useDebounced
