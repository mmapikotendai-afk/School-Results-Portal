import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import ApiStatusBadge from '@/components/common/ApiStatusBadge'
import { Alert, Button, Input } from '@/components/ui'
import { SIGN_OUT_REASON } from '@/context/authContext'
import useAuth from '@/hooks/useAuth'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { getErrorCode, getErrorMessage } from '@/services/apiClient'
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
 * Accounts are issued by the school office, so there is no registration link
 * and no self-service password reset - only a route back to the landing page.
 */
export function LoginPage() {
  useDocumentTitle('Sign in')

  const { signIn, signOutReason, clearSignOutReason } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [form, setForm] = useState({ identifier: '', password: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const notice = signOutReason ? REASON_NOTICE[signOutReason] : null

  // The notice belongs to the session that just ended, not to this page.
  // Clear it on unmount so it cannot reappear on a later visit.
  useEffect(() => () => clearSignOutReason(), [clearSignOutReason])

  function handleChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
    setFieldErrors((previous) => ({ ...previous, [name]: undefined }))
  }

  function validate() {
    const errors = {}
    if (!form.identifier.trim()) errors.identifier = 'Enter your username or email address.'
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
      // Send the user back where they were headed before being redirected here.
      const target = location.state?.from?.pathname || homePathForRole(user.role)
      navigate(target, { replace: true })
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
        <h1 className="font-serif text-3xl font-semibold">Sign in</h1>
        <p className="text-ink-500 mt-2 text-sm">
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

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <Input
          label="Username or email"
          name="identifier"
          type="text"
          icon="envelope"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck="false"
          placeholder="you@school.edu"
          value={form.identifier}
          onChange={handleChange}
          error={fieldErrors.identifier}
          disabled={submitting}
          autoFocus
          required
        />

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

        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={submitting}
          icon="arrow-right"
          iconPosition="right"
        >
          {submitting ? 'Signing in' : 'Sign In'}
        </Button>
      </form>

      <div className="border-ink-200 mt-8 border-t pt-6">
        <p className="text-ink-500 text-sm">
          Accounts are created by the school administrator. If you cannot sign in, or you
          have forgotten your password, contact the school office.
        </p>
        <ApiStatusBadge className="mt-4" />
      </div>
    </div>
  )
}

export default LoginPage
