import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, Badge, Button, DataTable, Modal } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import { academicService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'
import { statusLabel } from '@/utils/constants'
import { formatDateTime } from '@/utils/format'

/**
 * Who owes results for an examination, and who has delivered.
 *
 * Overdue is derived on the server from the examination deadline rather than
 * stored, so it cannot go stale between page loads.
 */
export function SubmissionMonitor({ open, exam, onClose, onSynced }) {
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState(null)
  const { data, loading, refresh } = useAsyncData(
    () => academicService.submissions(exam.id),
    [exam.id],
  )

  async function sync() {
    setSyncing(true)
    setError(null)
    try {
      const result = await academicService.syncSubmissions(exam.id)
      refresh()
      onSynced?.(
        result.created
          ? `Added ${result.created} tracking row${result.created === 1 ? '' : 's'}.`
          : 'Tracking is already up to date.',
      )
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSyncing(false)
    }
  }

  const rows = data ?? []
  const done = rows.filter((r) => r.status === 'SUBMITTED' || r.status === 'LATE').length
  const overdue = rows.filter((r) => r.is_overdue).length

  const columns = [
    {
      key: 'teacher',
      header: 'Teacher',
      render: (row) => (
        <div className="min-w-0">
          <p className="text-ink-900 font-medium">{row.teacher_name}</p>
          <p className="text-ink-400 font-mono text-xs">{row.employee_number}</p>
        </div>
      ),
    },
    {
      key: 'subject',
      header: 'Subject',
      render: (row) => (
        <div className="min-w-0">
          <p className="text-ink-800">{row.subject_name}</p>
          <p className="text-ink-400 font-mono text-xs">{row.subject_code}</p>
        </div>
      ),
    },
    {
      key: 'progress',
      header: 'Marks in',
      render: (row) => (
        <span className="text-ink-700 text-sm">
          {row.submitted_count} of {row.expected_count}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <div className="flex items-center gap-2">
          <Badge status={row.status}>{statusLabel(row.status)}</Badge>
          {row.is_overdue && (
            <span className="text-danger-600 text-xs font-semibold">
              <FontAwesomeIcon icon="triangle-exclamation" aria-hidden="true" /> Overdue
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'submitted_at',
      header: 'Submitted',
      render: (row) =>
        row.submitted_at ? (
          <div className="min-w-0">
            <p className="text-ink-700 text-sm">{formatDateTime(row.submitted_at)}</p>
            {row.submitted_by && <p className="text-ink-400 text-xs">by {row.submitted_by}</p>}
          </div>
        ) : (
          <span className="text-ink-400 text-sm">Not yet</span>
        ),
    },
  ]

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Submission monitor"
      description={exam.name}
      size="lg"
      footer={
        <>
          <Button variant="secondary" icon="rotate" onClick={sync} loading={syncing}>
            Sync assignments
          </Button>
          <Button onClick={onClose}>Close</Button>
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-4" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {rows.length > 0 && (
        <div className="bg-ink-50 mb-4 grid grid-cols-3 gap-3 rounded-lg px-4 py-3 text-center">
          <div>
            <p className="text-ink-900 text-xl font-semibold">{rows.length}</p>
            <p className="text-ink-500 text-xs">Expected</p>
          </div>
          <div>
            <p className="text-success-700 text-xl font-semibold">{done}</p>
            <p className="text-ink-500 text-xs">Submitted</p>
          </div>
          <div>
            <p className="text-danger-600 text-xl font-semibold">{overdue}</p>
            <p className="text-ink-500 text-xs">Overdue</p>
          </div>
        </div>
      )}

      <div className="border-ink-200 overflow-hidden rounded-lg border">
        <DataTable
          columns={columns}
          rows={rows}
          loading={loading && !data}
          empty={
            <div className="px-4 py-8 text-center">
              <p className="text-ink-700 font-medium">No submissions are being tracked</p>
              <p className="text-ink-500 mt-1 text-sm">
                Tracking rows are created when the examination is opened for submission.
                If you have assigned teachers since then, use Sync assignments.
              </p>
            </div>
          }
        />
      </div>

      <p className="text-ink-400 mt-3 text-xs">
        Syncing adds tracking for assignments made after submissions opened. It never
        resets a submission that has already been recorded.
      </p>
    </Modal>
  )
}

export default SubmissionMonitor
