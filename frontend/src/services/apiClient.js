/**
 * Shared Axios instance.
 *
 * - Attaches the bearer token to every request.
 * - Normalises backend errors into a predictable { code, message } shape.
 * - Reports 401s to AuthContext so a dead session is cleared everywhere at once.
 */

import axios from 'axios'

import { API_BASE_URL, TOKEN_STORAGE_KEY } from '@/utils/constants'
import { readItem, removeItem } from '@/utils/storage'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = readItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
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
      // The token is gone, expired or revoked. Clear it and tell the app why,
      // so the login screen can explain rather than just appearing.
      removeItem(TOKEN_STORAGE_KEY)
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
