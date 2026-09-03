import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, Button, Card, CardBody, CardHeader } from '@/components/ui'
import useAuth from '@/hooks/useAuth'
import { formatDateTime } from '@/utils/format'

function Row({ icon, label, value, hint }) {
  return (
    <div className="border-ink-100 flex items-start gap-3 border-b py-3.5 last:border-b-0">
      <span className="bg-ink-100 text-ink-500 mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg">
        <FontAwesomeIcon icon={icon} className="text-xs" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-ink-800 text-sm font-medium">{label}</p>
        <p className="text-ink-500 mt-0.5 text-sm">{value}</p>
        {hint && <p className="text-ink-400 mt-1 text-xs">{hint}</p>}
      </div>
    </div>
  )
}

/**
 * Security overview.
 *
 * This is the only place the must_change_password flag surfaces. Nagging on
 * every sign-in would train people to dismiss it without reading; the prompt
 * belongs where the action can actually be taken.
 */
export function SecurityPanel({ onChangePassword }) {
  const { user } = useAuth()
  if (!user) return null

  return (
    <div className="space-y-5">
      {user.must_change_password && (
        <Alert tone="warning" title="Your password was issued by an administrator">
          Set a password of your own so that nobody else knows how to sign in as you.
        </Alert>
      )}

      <Card>
        <CardHeader
          icon="shield-halved"
          title="Security"
          description="How your account is protected and when it was last used."
        />
        <CardBody>
          <div>
            <Row
              icon="lock"
              label="Password"
              value={
                user.password_changed_at
                  ? `Last changed ${formatDateTime(user.password_changed_at)}`
                  : 'Never changed since the account was created'
              }
              hint="Stored as a bcrypt hash. Nobody at the school can read your password."
            />
            <Row
              icon="clock"
              label="Last sign-in"
              value={formatDateTime(user.last_login_at)}
            />
            <Row
              icon="arrow-right-from-bracket"
              label="Sessions"
              value="Changing your password signs you out everywhere."
              hint="Any device still signed in with the old password is disconnected immediately."
            />
          </div>

          <div className="border-ink-200 mt-5 border-t pt-5">
            <Button icon="lock" onClick={onChangePassword}>
              Change password
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  )
}

export default SecurityPanel
