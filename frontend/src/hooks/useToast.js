import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * A single transient confirmation message.
 *
 * Deliberately one at a time: admin actions here are sequential, and a stack
 * of toasts would obscure the table the user just changed.
 *
 * The pending timer is tracked so a second message cancels the first one's
 * countdown. Without that, two actions in quick succession would leave the
 * second toast on screen for only the remainder of the first one's five
 * seconds - occasionally vanishing almost as it appeared.
 */
export function useToast(timeout = 5000) {
  const [toast, setToast] = useState(null)
  const timer = useRef(null)

  const clearTimer = useCallback(() => {
    if (timer.current) {
      window.clearTimeout(timer.current)
      timer.current = null
    }
  }, [])

  const show = useCallback(
    (message, tone = 'success') => {
      clearTimer()
      setToast({ message, tone, id: Date.now() })
      if (timeout) {
        timer.current = window.setTimeout(() => {
          setToast(null)
          timer.current = null
        }, timeout)
      }
    },
    [timeout, clearTimer],
  )

  const clear = useCallback(() => {
    clearTimer()
    setToast(null)
  }, [clearTimer])

  // Never fire a timer into a component that has gone away.
  useEffect(() => clearTimer, [clearTimer])

  return { toast, show, clear }
}

export default useToast
