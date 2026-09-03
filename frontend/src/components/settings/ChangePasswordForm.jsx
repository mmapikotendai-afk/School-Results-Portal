import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Alert, Button, Card, CardBody, CardHeader, Input } from '@/components/ui'
import useAuth from '@/hooks/useAuth'
import { getErrorMessage } from '@/services/apiClient'

const MIN_LENGTH = 8

const EMPTY = { currentPassword: '', newPassword: '', confirmPassword: '' }

/**
 * Change password.
 *
 * On success the backend invalidates every token the account holds, so this
 * form does not "save and carry on": it signs the user out and sends them to
 * /login, where they must authenticate with the new password.
 */
export function ChangePasswordForm() {
  const { changePassword } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState(EMPTY)
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function handleChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
    setFieldErrors((previous) => ({ ...previous, [name]: undefined }))
    setError(null)
  }

  /**
   * Client-side checks mirror the API so mistakes are caught before a round
   * trip. They are a convenience, never the enforcement: the same rules are
   * applied again on the server, which is what actually decides.
   */
  function validate() {
    const errors = {}

    if (!form.currentPassword) {
      errors.currentPassword = 'Enter your current password.'
    }
    if (!form.newPassword) {
      errors.newPassword = 'Enter a new password.'
    } else if (form.newPassword.length < MIN_LENGTH) {
      errors.newPassword = `Password must be at least ${MIN_LENGTH} characters long.`
    } else if (!/[A-Za-z]/.test(form.newPassword) || !/\d/.test(form.newPassword)) {
      errors.newPassword = 'Password must contain at least one letter and one number.'
    } else if (form.newPassword === form.currentPassword) {
      errors.newPassword = 'The new password must be different from your current one.'
    }

    if (!form.confirmPassword) {
      errors.confirmPassword = 'Re-enter your new password.'
    } else if (form.confirmPassword !== form.newPassword) {
      errors.confirmPassword = 'The passwords do not match.'
    }

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    if (!validate()) return

    setSubmitting(true)
    try {
      await changePassword(form)
      setForm(EMPTY)
      // The session is already dead. Replace the entry so Back cannot return
      // to a signed-in screen that would only redirect anyway.
      navigate('/login', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to change your password. Please try again.'))
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader
        icon="lock"
        title="Change Password"
        description="You will be signed out and asked to sign in again."
      />
      <CardBody>
        {error && (
          <Alert tone="danger" className="mb-5" onDismiss={() => setError(null)}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit} noValidate className="max-w-md space-y-5">
          <Input
            label="Current password"
            name="currentPassword"
            type="password"
            icon="lock"
            autoComplete="current-password"
            value={form.currentPassword}
            onChange={handleChange}
            error={fieldErrors.currentPassword}
            disabled={submitting}
            required
          />

          <Input
            label="New password"
            name="newPassword"
            type="password"
            icon="lock"
            autoComplete="new-password"
            value={form.newPassword}
            onChange={handleChange}
            error={fieldErrors.newPassword}
            hint={`At least ${MIN_LENGTH} characters, including a letter and a number.`}
            disabled={submitting}
            required
          />

          <Input
            label="Confirm new password"
            name="confirmPassword"
            type="password"
            icon="lock"
            autoComplete="new-password"
            value={form.confirmPassword}
            onChange={handleChange}
            error={fieldErrors.confirmPassword}
            disabled={submitting}
            required
          />

          <div className="border-ink-200 border-t pt-5">
            <Button type="submit" loading={submitting} icon="check">
              {submitting ? 'Changing password' : 'Change password'}
            </Button>
            <p className="text-ink-500 mt-3 text-sm">
              Any other device signed in to your account will be disconnected.
            </p>
          </div>
        </form>
      </CardBody>
    </Card>
  )
}

export default ChangePasswordForm
