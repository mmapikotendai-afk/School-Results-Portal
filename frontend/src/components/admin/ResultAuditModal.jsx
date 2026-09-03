import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, Badge, Button, Modal, Spinner } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import { resultsService } from '@/services/adminService'
import { cx, formatDateTime } from '@/utils/format'

/**
 * The full provenance of one mark.
 *
 * Answers the questions an audit exists for: who put the mark there, who has
 * changed it since, from what to what, why, and when.
 */
export function ResultAuditModal({ open, resultId, onClose }) {
  const { data, loading, error } = useAsyncData(
    () => resultsService.resultAudit(resultId),
    [resultId],
  )

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Result history"
      description={data ? `${data.student_name} · ${data.subject_name}` : undefined}
      size="lg"
      footer={<Button onClick={onClose}>Close</Button>}
    >
      {loading && !data && (
        <div className="flex items-center justify-center gap-3 py-10">
          <Spinner />
          <span className="text-ink-500 text-sm">Loading history…</span>
        </div>
      )}

      {error && <Alert tone="danger">{error}</Alert>}

      {data && (
        <div className="space-y-5">
          <div className="bg-ink-50 rounded-lg px-4 py-3">
            <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
              <div>
                <p className="text-ink-400 text-xs">Current mark</p>
                <p className="text-ink-900 text-xl font-semibold tabular-nums">
                  {Number(data.current_marks).toFixed(0)}
                  <span className="text-ink-500 ml-2 text-sm">{data.current_grade}</span>
                </p>
              </div>
              <div>
                <p className="text-ink-400 text-xs">Student</p>
                <p className="text-ink-800 text-sm font-medium">
                  {data.student_name}{' '}
                  <span className="text-ink-400 font-mono text-xs">
                    {data.student_number}
                  </span>
                </p>
              </div>
              <div>
                <p className="text-ink-400 text-xs">Examination</p>
                <p className="text-ink-800 text-sm font-medium">{data.examination_name}</p>
              </div>
            </div>
            {data.current_remarks && (
              <p className="text-ink-500 mt-3 text-sm">Remark: {data.current_remarks}</p>
            )}
          </div>

          {/* Where the mark originally came from. */}
          <div className="border-ink-200 flex items-start gap-3 rounded-lg border px-4 py-3">
            <span className="bg-brand-50 text-brand-700 mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg">
              <FontAwesomeIcon icon="cloud-arrow-up" className="text-xs" aria-hidden="true" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-ink-800 text-sm font-medium">
                Uploaded by {data.uploaded_by ?? 'an account since removed'}
              </p>
              <p className="text-ink-400 text-xs">{formatDateTime(data.created_at)}</p>
            </div>
          </div>

          <div>
            <p className="text-ink-700 mb-2 text-sm font-medium">
              {data.changes.length === 0
                ? 'No changes since it was uploaded'
                : `${data.changes.length} change${data.changes.length === 1 ? '' : 's'} since`}
            </p>

            {data.changes.length > 0 && (
              <div className="border-ink-200 overflow-hidden rounded-lg border">
                <table className="w-full text-sm">
                  <thead className="bg-ink-50">
                    <tr>
                      <th scope="col" className="text-ink-500 px-3 py-2 text-left text-xs font-semibold uppercase">
                        When
                      </th>
                      <th scope="col" className="text-ink-500 px-3 py-2 text-left text-xs font-semibold uppercase">
                        Changed by
                      </th>
                      <th scope="col" className="text-ink-500 px-3 py-2 text-center text-xs font-semibold uppercase">
                        Mark
                      </th>
                      <th scope="col" className="text-ink-500 px-3 py-2 text-left text-xs font-semibold uppercase">
                        Reason
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-ink-100 divide-y">
                    {data.changes.map((change) => {
                      const before = Number(change.old_marks)
                      const after = Number(change.new_marks)
                      return (
                        <tr key={change.id}>
                          <td className="text-ink-600 px-3 py-2.5 text-xs whitespace-nowrap">
                            {formatDateTime(change.changed_at)}
                          </td>
                          <td className="px-3 py-2.5">
                            <p className="text-ink-900 text-sm font-medium">
                              {change.changed_by ?? '—'}
                            </p>
                            {change.changed_by_role && (
                              <Badge tone="neutral" className="mt-0.5">
                                {change.changed_by_role}
                              </Badge>
                            )}
                          </td>
                          <td className="px-3 py-2.5 text-center whitespace-nowrap">
                            <span className="text-ink-500 tabular-nums line-through">
                              {before.toFixed(0)} {change.old_grade}
                            </span>
                            <FontAwesomeIcon
                              icon="arrow-right"
                              className="text-ink-300 mx-2 text-[10px]"
                              aria-hidden="true"
                            />
                            <span
                              className={cx(
                                'font-semibold tabular-nums',
                                after > before ? 'text-success-700' : 'text-danger-700',
                              )}
                            >
                              {after.toFixed(0)} {change.new_grade}
                            </span>
                          </td>
                          <td className="text-ink-600 px-3 py-2.5">{change.reason ?? '—'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <p className="text-ink-400 text-xs">
            Every correction is recorded here permanently. Entries cannot be edited or
            removed.
          </p>
        </div>
      )}
    </Modal>
  )
}

export default ResultAuditModal
