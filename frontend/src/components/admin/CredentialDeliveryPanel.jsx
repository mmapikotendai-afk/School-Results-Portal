import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, Button } from '@/components/ui'
import { getErrorMessage } from '@/services/apiClient'
import { cx } from '@/utils/format'

/**
 * What happened to the credential email for a newly provisioned account.
 *
 * There is deliberately no password on this panel. The temporary password is
 * generated on the server, hashed, emailed, and dropped - the browser never
 * receives it, so there is nothing here to display or to copy. When delivery
 * fails the remedy is Resend, which issues a *new* password rather than
 * revealing one that no longer exists in readable form anywhere.
 */

const CHECK = 'circle-check'

function Line({ ok, children }) {
  return (
    <li className="flex items-start gap-2.5">
      <FontAwesomeIcon
        icon={ok ? CHECK : 'circle-exclamation'}
        className={cx('mt-0.5 shrink-0 text-sm', ok ? 'text-success-600' : 'text-warning-600')}
        aria-hidden="true"
      />
      <span className="text-ink-700 text-sm">{children}</span>
    </li>
  )
}

export function CredentialDeliveryPanel({ delivery, accountType, onResend, onDeliveryChange }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [resent, setResent] = useState(null)

  // A resend replaces the outcome shown, so the panel always reflects the
  // most recent attempt rather than the one from account creation.
  const current = resent ?? delivery
  const sent = current?.sent
  const skipped = current?.status === 'SKIPPED'

  // No delivery record at all means the API answered in a shape this build
  // does not understand - typically a server running older code. Say that,
  // rather than guessing at a reason: claiming "no mailbox" here would be an
  // assertion the panel has no evidence for.
  const unknown = !current

  async function handleResend() {
    setBusy(true)
    setError(null)
    try {
      const next = await onResend()
      setResent(next)
      onDeliveryChange?.(next)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      {error && (
        <Alert tone="danger" className="mb-4" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {unknown ? (
        <Alert tone="warning" title="Account created, delivery status unknown">
          The account was created, but the server did not report whether the credentials
          were emailed. Reload the page and use Resend login credentials from the list.
        </Alert>
      ) : sent ? (
        <Alert tone="success" title="Account created successfully">
          {resent
            ? 'A new temporary password has been sent. The previous one no longer works.'
            : current.detail}
        </Alert>
      ) : (
        <Alert
          tone={skipped ? 'warning' : 'danger'}
          title={skipped ? 'Account created, no email sent' : 'Account created, email not delivered'}
        >
          {current.detail}
        </Alert>
      )}

      <ul className="mt-4 space-y-2.5">
        <Line ok>{accountType} account created</Line>
        <Line ok>Email address verified for format</Line>
        <Line ok={sent}>
          {sent ? 'Login credentials sent' : 'Login credentials not delivered'}
        </Line>
      </ul>

      {current?.email && (
        <dl className="border-ink-200 mt-4 rounded-lg border px-4 py-3">
          <dt className="text-ink-500 text-xs font-semibold tracking-wide uppercase">Email</dt>
          <dd className="text-ink-900 mt-1 font-mono text-sm break-all">{current.email}</dd>
        </dl>
      )}

      {sent ? (
        <p className="text-ink-500 mt-4 text-sm">
          The user must change their temporary password after their first login. Doing so
          signs them out, and they sign in again with the password they chose.
        </p>
      ) : (
        <div className="border-warning-300 bg-warning-50 mt-4 rounded-lg border p-4">
          <p className="text-warning-900 text-sm">
            {current?.can_resend
              ? 'Resending issues a new temporary password and emails it. The password set a moment ago stops working immediately.'
              : unknown
                ? 'Find the account in the list and use Resend login credentials there.'
                : 'This account has no real mailbox, so credentials cannot be emailed. Give it a real email address, then resend.'}
          </p>
          {current?.can_resend && (
            <Button
              className="mt-3"
              variant="secondary"
              icon="paper-plane"
              loading={busy}
              onClick={handleResend}
            >
              Resend credentials
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

export default CredentialDeliveryPanel
