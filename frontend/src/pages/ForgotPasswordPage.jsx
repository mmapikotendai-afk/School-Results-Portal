import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import { Alert, Button, Input } from '@/components/ui'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import authService from '@/services/authService'
import { getErrorMessage } from '@/services/apiClient'

/**
 * Ask the school office to reissue your password.
 *
 * This screen sends a request; it does not reset anything. Accounts here are
 * issued by the school rather than registered, and a learner may have no
 * mailbox of their own, so a self-service reset link would assume an inbox
 * that many users do not have. Somebody in the office decides instead.
 *
 * The confirmation is deliberately the same whether or not the account exists.
 * Saying "no such account" would let anyone use this form to find out who
 * holds one.
 */
export function ForgotPasswordPage() {
  useDocumentTitle('Forgot password')

  const [identifier, setIdentifier] = useState('')
  const [message, setMessage] = useState('')
  const [fieldError, setFieldError] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)

    if (!identifier.trim()) {
      setFieldError('Enter the username or email address you sign in with.')
      return
    }

    setSubmitting(true)
    try {
      const result = await authService.requestPasswordReset(identifier.trim(), message)
      setSent(result.detail)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not send that request. Please try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  if (sent) {
    return (
      <div>
        <div className="mb-6">
          <span className="bg-success-50 text-success-700 mb-4 flex size-12 items-center justify-center rounded-full">
            <FontAwesomeIcon icon="circle-check" className="text-xl" aria-hidden="true" />
          </span>
          <p className="rule-label mb-3">Request sent</p>
          <h1 className="text-[28px] leading-tight font-bold tracking-tight">
            The office has been notified
          </h1>
        </div>

        <p className="text-ink-600 text-sm">{sent}</p>

        <div className="border-ink-200 mt-6 border-t pt-6">
          <p className="text-ink-500 text-sm">
            Your current password keeps working until the office issues a new one. If you
            remember it in the meantime, you can still sign in as normal.
          </p>
          <Button as={Link} to="/login" variant="secondary" className="mt-4" icon="arrow-left">
            Back to sign in
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-8">
        <p className="rule-label mb-3">Results Portal</p>
        <h1 className="text-[32px] leading-none font-bold tracking-tight">
          Forgot password
        </h1>
        <p className="text-ink-500 mt-3 text-sm">
          The school office issues passwords. Tell them you are locked out and they will
          send you a new one by email.
        </p>
      </div>

      {error && (
        <Alert tone="danger" className="mb-5" onDismiss={() => setError(null)}>
          {error}
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
          hint="Whatever you normally sign in with."
          value={identifier}
          onChange={(e) => {
            setIdentifier(e.target.value)
            setFieldError(null)
          }}
          error={fieldError}
          disabled={submitting}
          autoFocus
          required
        />

        <Input
          label="Anything the office should know"
          name="message"
          type="text"
          placeholder="Optional"
          hint="For example, if your email address has changed."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={submitting}
          maxLength={500}
        />

        <Button
          type="submit"
          size="lg"
          fullWidth
          loading={submitting}
          icon="arrow-right"
          iconPosition="right"
        >
          {submitting ? 'Sending request' : 'Send request'}
        </Button>
      </form>

      <div className="border-ink-200 mt-8 border-t pt-6">
        <Link
          to="/login"
          className="text-brand-700 hover:text-brand-900 inline-flex items-center gap-2 text-sm font-semibold"
        >
          <FontAwesomeIcon icon="arrow-left" aria-hidden="true" />
          Back to sign in
        </Link>
      </div>
    </div>
  )
}

export default ForgotPasswordPage
