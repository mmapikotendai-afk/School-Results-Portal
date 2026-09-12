import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  Input,
  Modal,
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { resetRequestService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'
import { cx, formatDateTime } from '@/utils/format'
import { roleLabel } from '@/utils/roles'

const STATUS_FILTERS = [
  { value: 'PENDING', label: 'Waiting' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'DECLINED', label: 'Declined' },
  { value: '', label: 'All' },
]

/** Refusing a request needs a reason, so the next person to look knows why. */
function DeclineDialog({ open, request, onClose, onDeclined }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      await resetRequestService.decline(request.id, note)
      onDeclined(`The request from ${request.full_name} was declined.`)
    } catch (err) {
      setError(getErrorMessage(err))
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={busy ? undefined : onClose}
      title="Decline this request?"
      description={`${request.full_name} · ${request.email}`}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" onClick={submit} loading={busy} icon="ban">
            Decline request
          </Button>
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-4" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <p className="text-ink-600 mb-4 text-sm">
        Nothing changes on the account. Their current password keeps working, and they
        can ask again.
      </p>

      <Input
        label="Reason"
        name="note"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Handled by phone; identity not confirmed"
        hint="Recorded against the request."
        maxLength={500}
        disabled={busy}
      />
    </Modal>
  )
}

/**
 * The school office's password reset queue.
 *
 * Approving reissues the password through the same service the Students and
 * Teachers pages use: a generated password nobody sees, emailed to the holder,
 * with every existing session ended. Declining changes nothing.
 */
export function ResetRequestsPage() {
  useDocumentTitle('Password Resets')

  const [status, setStatus] = useState('PENDING')
  const [approving, setApproving] = useState(null)
  const [declining, setDeclining] = useState(null)
  const { toast, show, clear } = useToast()

  const requests = useAsyncData(
    () => resetRequestService.list(status || undefined),
    [status],
  )

  async function approve(request) {
    try {
      const delivery = await resetRequestService.approve(request.id)
      show(delivery.detail, delivery.sent ? 'success' : 'danger')
      requests.refresh()
    } catch (err) {
      show(getErrorMessage(err), 'danger')
    }
  }

  const columns = [
    {
      key: 'who',
      header: 'Account',
      render: (row) => (
        <div className="min-w-0">
          <p className="text-ink-900 font-medium">{row.full_name}</p>
          <p className="text-ink-400 text-xs">
            {row.email}
            {row.username ? ` · ${row.username}` : ''}
          </p>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (row) => <span className="text-ink-600 text-sm">{roleLabel(row.role)}</span>,
    },
    {
      key: 'typed',
      header: 'They typed',
      render: (row) => (
        <div className="min-w-0">
          <span
            className={cx(
              'font-mono text-xs',
              // Worth noticing: they are signing in with something the school
              // does not hold against the account.
              row.submitted_identifier?.toLowerCase() !== row.email?.toLowerCase() &&
                row.submitted_identifier?.toLowerCase() !== row.username?.toLowerCase()
                ? 'text-warning-700'
                : 'text-ink-500',
            )}
          >
            {row.submitted_identifier}
          </span>
          {row.message && <p className="text-ink-500 mt-1 text-xs italic">“{row.message}”</p>}
        </div>
      ),
    },
    {
      key: 'asked',
      header: 'Asked',
      render: (row) => (
        <span className="text-ink-600 text-sm">{formatDateTime(row.created_at)}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <div className="min-w-0">
          <Badge status={row.status}>
            {row.status === 'PENDING' ? 'Waiting' : row.status === 'APPROVED' ? 'Approved' : 'Declined'}
          </Badge>
          {row.resolved_by && (
            <p className="text-ink-400 mt-1 text-xs">
              by {row.resolved_by}
              {row.resolved_at ? ` · ${formatDateTime(row.resolved_at)}` : ''}
            </p>
          )}
          {row.resolution_note && (
            <p className="text-ink-500 mt-0.5 text-xs italic">{row.resolution_note}</p>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) =>
        row.status === 'PENDING' ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button size="sm" icon="key" onClick={() => setApproving(row)}>
              Reissue password
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setDeclining(row)}>
              Decline
            </Button>
          </div>
        ) : (
          <span className="text-ink-300 text-xs">Settled</span>
        ),
    },
  ]

  const rows = requests.data ?? []
  const waiting = rows.filter((r) => r.status === 'PENDING').length

  return (
    <div>
      <PageHeader
        title="Password Resets"
        description="People who cannot sign in and have asked the office for a new password."
        actions={
          <Select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            options={STATUS_FILTERS}
            aria-label="Filter by status"
          />
        }
      />

      {requests.error && (
        <Alert tone="danger" className="mb-5">
          {requests.error}
        </Alert>
      )}

      {status === 'PENDING' && waiting > 0 && (
        <Alert tone="info" className="mb-5">
          <FontAwesomeIcon icon="circle-info" className="mr-2" aria-hidden="true" />
          Reissuing sends a new temporary password by email and signs the person out
          everywhere. Nobody, including you, ever sees the password itself.
        </Alert>
      )}

      <Card>
        <DataTable
          columns={columns}
          rows={rows}
          loading={requests.loading && !requests.data}
          empty={
            <EmptyState
              icon="lock"
              title={status === 'PENDING' ? 'Nothing waiting' : 'No requests here'}
              description={
                status === 'PENDING'
                  ? 'When somebody uses "Forgot your password?" on the sign-in screen, their request appears here.'
                  : 'Try a different status filter.'
              }
            />
          }
        />
      </Card>

      {approving && (
        <ConfirmDialog
          open
          onClose={() => setApproving(null)}
          onConfirm={async () => {
            const row = approving
            setApproving(null)
            await approve(row)
          }}
          title="Reissue this password?"
          message={`A new temporary password will be emailed to ${approving.full_name} at ${approving.email}. Their current password stops working immediately and they will be signed out everywhere.`}
          detail={
            <Alert tone="warning">
              Check you know who asked. Anyone who can reach the sign-in page can raise a
              request, so the name on the request is not proof of identity.
            </Alert>
          }
          confirmLabel="Reissue password"
          icon="key"
        />
      )}

      {declining && (
        <DeclineDialog
          open
          request={declining}
          onClose={() => setDeclining(null)}
          onDeclined={(message) => {
            setDeclining(null)
            show(message)
            requests.refresh()
          }}
        />
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default ResetRequestsPage
