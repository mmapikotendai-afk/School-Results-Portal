/**
 * Authentication state for the whole app.
 *
 * The session itself is an httpOnly cookie held by the browser. This file
 * never sees it, cannot read it, and has nothing to store: script on the page
 * is unable to reach the credential, and the cookie is discarded when the
 * browser closes rather than outliving the person who signed in - which is
 * what left the next user of a shared staff-room machine signed in as the
 * last one.
 *
 * What is kept here is the expiry timestamp, so the app can sign out on time
 * instead of waiting for the next request to fail. It is a time, not a
 * credential, and is worthless to anyone who reads it.
 *
 * On boot the profile is re-fetched from /auth/me rather than trusted from
 * cache, so a session that has been revoked, has expired, or belongs to a
 * deactivated account is discovered immediately.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { AuthContext, SIGN_OUT_REASON } from '@/context/authContext'
import { setUnauthorizedHandler } from '@/services/apiClient'
import authService from '@/services/authService'
import { SESSION_EXPIRY_STORAGE_KEY } from '@/utils/constants'
import { readItem, removeItem, writeItem } from '@/utils/storage'

function storedExpiry() {
  const raw = readItem(SESSION_EXPIRY_STORAGE_KEY)
  const value = raw ? Number(raw) : NaN
  return Number.isFinite(value) ? value : null
}

/**
 * Whether a session might still be live.
 *
 * Only ever a hint. The cookie cannot be read from here, so this says "it is
 * worth asking the server", never "the user is signed in". The answer that
 * counts comes from /auth/me.
 */
function mightBeSignedIn() {
  const expiry = storedExpiry()
  return expiry !== null && expiry > Date.now()
}

function clearStoredSession() {
  removeItem(SESSION_EXPIRY_STORAGE_KEY)
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // `initialising` covers the first /auth/me round-trip, so route guards do not
  // bounce a signed-in user to /login before we know the token is good.
  const [initialising, setInitialising] = useState(true)
  const [signOutReason, setSignOutReason] = useState(null)

  const expiryTimer = useRef(null)

  const clearSession = useCallback((reason = SIGN_OUT_REASON.USER) => {
    clearStoredSession()
    window.clearTimeout(expiryTimer.current)
    setUser(null)
    setSignOutReason(reason)
  }, [])

  /** Sign out locally and revoke the token on the server. */
  const signOut = useCallback(
    async (reason = SIGN_OUT_REASON.USER) => {
      // Only worth a round-trip while the token could still be accepted.
      if (reason === SIGN_OUT_REASON.USER && mightBeSignedIn()) {
        await authService.logout()
      }
      clearSession(reason)
    },
    [clearSession],
  )

  // Sign out automatically the moment the token expires, rather than waiting
  // for the next request to fail.
  const scheduleExpiry = useCallback(
    (expiresAt) => {
      window.clearTimeout(expiryTimer.current)
      if (!expiresAt) return

      const delay = expiresAt - Date.now()
      if (delay <= 0) {
        clearSession(SIGN_OUT_REASON.EXPIRED)
        return
      }
      // setTimeout caps out around 24.8 days; our tokens are far shorter.
      expiryTimer.current = window.setTimeout(
        () => clearSession(SIGN_OUT_REASON.EXPIRED),
        delay,
      )
    },
    [clearSession],
  )

  // A 401 from any request means the session is already dead server-side.
  useEffect(() => {
    setUnauthorizedHandler((code) => {
      clearSession(code || SIGN_OUT_REASON.EXPIRED)
    })
    return () => setUnauthorizedHandler(null)
  }, [clearSession])

  // Restore the session on first load.
  useEffect(() => {
    let cancelled = false

    async function restore() {
      if (!mightBeSignedIn()) {
        clearStoredSession()
        if (!cancelled) setInitialising(false)
        return
      }

      try {
        const profile = await authService.me()
        if (cancelled) return
        setUser(profile)
        scheduleExpiry(storedExpiry())
      } catch {
        // The 401 interceptor has already cleared state and set the reason.
        if (!cancelled) clearStoredSession()
      } finally {
        if (!cancelled) setInitialising(false)
      }
    }

    restore()
    return () => {
      cancelled = true
    }
    // Runs once on mount; the callbacks it uses are stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => () => window.clearTimeout(expiryTimer.current), [])

  const signIn = useCallback(
    async (identifier, password) => {
      const data = await authService.login(identifier, password)
      const expiresAt = Date.now() + data.expires_in * 1000

      // The session cookie arrived with this response; only the expiry is
      // ours to keep.
      writeItem(SESSION_EXPIRY_STORAGE_KEY, String(expiresAt))
      setUser(data.user)
      setSignOutReason(null)
      scheduleExpiry(expiresAt)

      return data.user
    },
    [scheduleExpiry],
  )

  /**
   * Change the password, then end the session.
   *
   * The backend invalidates every token on success, so staying signed in is not
   * an option: the current token is already dead by the time this resolves.
   */
  const changePassword = useCallback(
    async (payload) => {
      const result = await authService.changePassword(payload)
      clearSession(SIGN_OUT_REASON.PASSWORD_CHANGED)
      return result
    },
    [clearSession],
  )

  /** Let a screen refresh the profile after it changes something. */
  const refreshProfile = useCallback(async () => {
    const profile = await authService.me()
    setUser(profile)
    return profile
  }, [])

  const value = useMemo(
    () => ({
      user,
      initialising,
      isAuthenticated: Boolean(user),
      signOutReason,
      clearSignOutReason: () => setSignOutReason(null),
      signIn,
      signOut,
      changePassword,
      refreshProfile,
    }),
    [user, initialising, signOutReason, signIn, signOut, changePassword, refreshProfile],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
