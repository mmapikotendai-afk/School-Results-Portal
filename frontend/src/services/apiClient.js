/**
 * Shared Axios instance.
 *
 * - Sends the session cookie with every request.
 * - Normalises backend errors into a predictable { code, message } shape.
 * - Reports 401s to AuthContext so a dead session is cleared everywhere at once.
 */

import axios from 'axios'

import { API_BASE_URL, CSRF_HEADER } from '@/utils/constants'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
  // The session is an httpOnly cookie the browser attaches itself. There is
  // no token here to read or forget, and script on the page cannot reach it.
  withCredentials: true,
})

/** Methods that cannot change anything, and so need no CSRF token. */
const SAFE_METHODS = new Set(['get', 'head', 'options'])

/**
 * The CSRF token, read from the cookie the server set alongside the session.
 *
 * Readable on purpose: a cookie is attached to any request to this origin,
 * including one another site caused, so the server needs something back that
 * only a page on this origin could have read. That is what this echoes.
 */
function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)srp_csrf=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : null
}

apiClient.interceptors.request.use((config) => {
  if (!SAFE_METHODS.has((config.method || 'get').toLowerCase())) {
    const token = csrfToken()
    if (token) config.headers[CSRF_HEADER] = token
  }
  return config
})

/** Registered by AuthContext so a 401 can clear React state, not just storage. */
let onUnauthorized = null

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

/** Requests where a 401 is an expected answer, not a dead session. */
function isAuthAttempt(url = '') {
  return url.includes('/auth/login') || url.includes('/auth/change-password')
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url ?? ''

    if (status === 401 && !isAuthAttempt(url)) {
      // The session is gone, expired or revoked. Nothing to clear here: it
      // lives in an httpOnly cookie the server discards. Telling the app is
      // all that remains, so the sign-in screen can explain what happened
      // rather than simply appearing.
      onUnauthorized?.(getErrorCode(error))
    }

    return Promise.reject(error)
  },
)

/**
 * The machine-readable reason a request failed.
 *
 * The API returns auth failures as { detail: { code, message } }, so the UI can
 * distinguish an expired session from a wrong password without reading prose.
 */
export function getErrorCode(error) {
  const detail = error?.response?.data?.detail
  return detail && typeof detail === 'object' && !Array.isArray(detail)
    ? (detail.code ?? null)
    : null
}

/**
 * Turn any Axios failure into a single readable sentence.
 *
 * FastAPI returns `detail` three ways: a string for simple errors, our
 * { code, message } object for auth errors, and a list for request-validation
 * failures. All three are handled here so callers never format errors themselves.
 */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error) return fallback

  if (error.code === 'ECONNABORTED') {
    return 'The server took too long to respond. Please try again.'
  }

  if (!error.response) {
    // Axios sets `request` when the call went out but nothing came back, which
    // is the only case that genuinely means the server is unreachable. An
    // error without it was raised by our own code - the download helper
    // rejecting an empty or non-file response, say - and its message is
    // already written for the user, so reporting a network fault instead
    // would send them looking for the wrong problem.
    if (!error.request && error.message) return error.message
    return 'Cannot reach the server. Check that the backend is running.'
  }

  const detail = error.response.data?.detail

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail) && detail.length > 0) {
    // Pydantic validation errors. Strip the "Value error, " prefix Pydantic
    // adds to messages raised from custom validators.
    return detail
      .map((item) => String(item?.msg ?? item).replace(/^Value error,\s*/i, ''))
      .join(' ')
  }

  if (detail && typeof detail === 'object' && detail.message) {
    return detail.message
  }

  if (error.response.status >= 500) {
    return 'The server ran into a problem. Please try again shortly.'
  }

  return fallback
}

export default apiClient
