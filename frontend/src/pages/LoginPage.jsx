import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Alert, Button, Input } from '@/components/ui'
import { SIGN_OUT_REASON } from '@/context/authContext'
import useAuth from '@/hooks/useAuth'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import apiClient, { getErrorCode, getErrorMessage } from '@/services/apiClient'
import { homePathForRole } from '@/utils/roles'

/**
 * Why the previous session ended. Shown once, above the form, so the user is
 * told what happened instead of silently finding themselves back at sign-in.
 */
const REASON_NOTICE = {
  [SIGN_OUT_REASON.EXPIRED]: {
    tone: 'warning',
    text: 'Your session expired. Please sign in again.',
  },
  [SIGN_OUT_REASON.REVOKED]: {
    tone: 'warning',
    text: 'Your session ended. Please sign in again.',
  },
  [SIGN_OUT_REASON.INACTIVE]: {
    tone: 'danger',
    text: 'This account has been deactivated. Please contact the school office.',
  },
  [SIGN_OUT_REASON.PASSWORD_CHANGED]: {
    tone: 'success',
    text: 'Your password was changed. Please sign in with your new password.',
  },
}

/**
 * Sign-in screen.
 *
 * Accounts are issued by the school office, so there is no registration link.
 * "Forgot your password?" does not reset anything either: it asks the office to
 * issue a new one, which is how every credential here is handed out.
 */
export function LoginPage() {
  useDocumentTitle('Sign in')

  const { signIn, signOutReason, clearSignOutReason } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({ identifier: '', password: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [warmingServer, setWarmingServer] = useState(true)

  const notice = signOutReason ? REASON_NOTICE[signOutReason] : null

  // The notice belongs to the session that just ended, not to this page.
  // Clear it on unmount so it cannot reappear on a later visit.
  useEffect(() => () => clearSignOutReason(), [clearSignOutReason])

  // Wake a Render Free instance before the user submits credentials. This
  // keeps a cold start from being mistaken for an invalid sign-in attempt.
  useEffect(() => {
    let active = true

    apiClient.get('/health')
      .catch(() => undefined)
      .finally(() => {
        if (active) setWarmingServer(false)
      })

    return () => { active = false }
  }, [])

  function handleChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
    setFieldErrors((previous) => ({ ...previous, [name]: undefined }))
  }

  function validate() {
    const errors = {}
    if (!form.identifier.trim()) errors.identifier = 'Enter your student number, username or email.'
    if (!form.password) errors.password = 'Enter your password.'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    clearSignOutReason()
    if (!validate()) return

    setSubmitting(true)
    try {
      const user = await signIn(form.identifier.trim(), form.password)
      // Always the account's own home, never the page a link pointed at.
      // Portal URLs get forwarded, and sign-in should not deliver whoever
      // uses a forwarded link to the exact screen it was copied from.
      navigate(user.must_change_password ? '/change-password' : homePathForRole(user.role), {
        replace: true,
      })
    } catch (err) {
      setError({
        code: getErrorCode(err),
        message: getErrorMessage(err, 'Unable to sign in. Please try again.'),
      })
      // Never leave a rejected password sitting in the field.
      setForm((previous) => ({ ...previous, password: '' }))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-serif text-[40px] leading-tight font-medium tracking-tight">Sign in</h1>
        <p className="text-ink-500 mt-3 text-sm">
          Use the credentials issued to you by the school office.
        </p>
      </div>

      {notice && !error && (
        <Alert tone={notice.tone} className="mb-5">
          {notice.text}
        </Alert>
      )}

      {error && (
        <Alert
          tone={error.code === 'account_inactive' ? 'warning' : 'danger'}
          className="mb-5"
          onDismiss={() => setError(null)}
        >
          {error.message}
        </Alert>
      )}

      {warmingServer && !error && (
        <Alert tone="info" className="mb-5">
          Starting the secure server. This can take up to a minute after a period of inactivity.
        </Alert>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <Input
          label="Student number or username"
          name="identifier"
          type="text"
          icon="user-graduate"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck="false"
          placeholder="PHS26001"
          value={form.identifier}
          onChange={handleChange}
          error={fieldErrors.identifier}
          disabled={submitting}
          autoFocus
          required
        />

        <div>
          <Input
            label="Password"
            name="password"
            type="password"
            icon="lock"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={form.password}
            onChange={handleChange}
            error={fieldErrors.password}
            disabled={submitting}
            required
          />
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-ink-500">
              Contact the school administration if you cannot log in.
            </p>
            <Link
              to="/forgot-password"
              className="text-ink-500 hover:text-brand-800 text-sm font-medium underline underline-offset-2"
            >
              Forgot your password?
            </Link>
          </div>
        </div>

        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={submitting}
          disabled={warmingServer}
          icon="arrow-right"
          iconPosition="right"
        >
          {submitting ? 'Signing in' : warmingServer ? 'Starting server' : 'Sign in'}
        </Button>
      </form>

    </div>
  )
}

export default LoginPage
