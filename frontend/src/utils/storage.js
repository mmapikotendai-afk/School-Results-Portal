/**
 * Thin localStorage wrapper. Access can throw in private browsing modes, so
 * every call is guarded and degrades to an in-memory-free no-op.
 */

export function readItem(key) {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

export function writeItem(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    /* storage unavailable - the session simply will not survive a reload */
  }
}

export function removeItem(key) {
  try {
    window.localStorage.removeItem(key)
  } catch {
    /* nothing to do */
  }
}
