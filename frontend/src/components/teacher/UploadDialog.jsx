import { useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import ReplaceConfirmation from '@/components/teacher/ReplaceConfirmation'
import { Alert, Button, Modal } from '@/components/ui'
import { getErrorMessage } from '@/services/apiClient'
import { teacherDownloads, teacherPortalService } from '@/services/teacherService'
import { cx } from '@/utils/format'

/**
 * Import results from a CSV file.
 *
 * Choose file -> parse and validate -> preview -> confirm -> save.
 *
 * The file is always validated before it can be saved, and the preview shows
 * every row, not just the bad ones. Confirmation is gated on the server's
 * `can_import` flag rather than anything computed here, so the decision is made
 * in one place; the API refuses a file with errors regardless of what the
 * button allows.
 */
export function UploadDialog({ open, sheet, onClose, onUploaded }) {
  const [file, setFile] = useState(null)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [showAll, setShowAll] = useState(false)
  // Replacing an existing mark is opt-in. The server refuses without it, so
  // this cannot be bypassed by poking at the UI.
  const [allowReplace, setAllowReplace] = useState(false)
  const [reason, setReason] = useState('')
  const input = useRef(null)

  const { examination_id: examId, subject_id: subjectId, subject_code: code } = sheet

  function choose(selected) {
    setError(null)
    setReport(null)
    setShowAll(false)
    setAllowReplace(false)
    setReason('')
    if (!selected) return
    if (!selected.name.toLowerCase().endsWith('.csv')) {
      setError('Upload a CSV file. Export your spreadsheet as CSV first.')
      return
    }
    setFile(selected)
  }

  async function validate() {
    setBusy('validate')
    setError(null)
    try {
      setReport(
        await teacherPortalService.upload(examId, subjectId, file, {
          validateOnly: true,
          allowReplace,
        }),
      )
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  async function confirmImport() {
    setBusy('import')
    setError(null)
    try {
      const result = await teacherPortalService.upload(examId, subjectId, file, {
        allowReplace,
        reason: reason.trim() || null,
      })
      if (result.committed) {
        onUploaded(result)
      } else {
        // The roll can change between validating and confirming.
        setReport(result)
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  const rows = report?.rows ?? []
  const invalidRows = rows.filter((r) => !r.valid)
  // Long files collapse to the problems, which is what needs acting on.
  const visible = showAll || rows.length <= 12 || invalidRows.length === 0 ? rows : invalidRows

  return (
    <Modal
      open={open}
      onClose={busy ? undefined : onClose}
      title="Import results"
      description={`${sheet.subject_name} · ${sheet.examination_name}`}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={Boolean(busy)}>
            Cancel
          </Button>
          {!report ? (
            <Button onClick={validate} loading={busy === 'validate'} disabled={!file} icon="check">
              Validate file
            </Button>
          ) : (
            <Button
              onClick={confirmImport}
              loading={busy === 'import'}
              disabled={!report.can_import && !(report.requires_replace_confirmation && allowReplace)}
              variant={report.overwrites > 0 ? 'danger' : 'primary'}
              icon="cloud-arrow-up"
            >
              {report.overwrites > 0
                ? `Replace ${report.overwrites} & import ${report.accepted}`
                : `Confirm & import ${report.accepted} result${report.accepted === 1 ? '' : 's'}`}
            </Button>
          )}
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-4" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {!report && (
        <>
          <div className="bg-brand-50 mb-4 flex items-start gap-3 rounded-lg px-4 py-3">
            <FontAwesomeIcon icon="circle-info" className="text-brand-700 mt-0.5" aria-hidden="true" />
            <div className="min-w-0 flex-1 text-sm">
              <p className="text-brand-900">
                Start from the template: it already contains the student numbers of
                everyone enrolled, so nothing has to be typed by hand.
              </p>
              <button
                type="button"
                onClick={() => teacherDownloads.template(examId, subjectId, code)}
                className="text-brand-800 mt-1.5 font-semibold underline"
              >
                Download CSV template
              </button>
            </div>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              choose(e.dataTransfer.files?.[0])
            }}
            className={cx(
              'rounded-lg border-2 border-dashed px-5 py-8 text-center transition-colors',
              dragging ? 'border-brand-500 bg-brand-50' : 'border-ink-300',
            )}
          >
            <FontAwesomeIcon
              icon={file ? 'file-csv' : 'cloud-arrow-up'}
              className={cx('text-2xl', file ? 'text-success-600' : 'text-ink-400')}
              aria-hidden="true"
            />
            {file ? (
              <div className="mt-2">
                <p className="text-ink-900 text-sm font-medium">{file.name}</p>
                <p className="text-ink-500 text-xs">{(file.size / 1024).toFixed(1)} KB</p>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="text-ink-500 hover:text-ink-800 mt-2 text-xs underline"
                >
                  Choose a different file
                </button>
              </div>
            ) : (
              <div className="mt-2">
                <p className="text-ink-700 text-sm">Drag a CSV file here, or</p>
                <button
                  type="button"
                  onClick={() => input.current?.click()}
                  className="text-brand-700 mt-1 text-sm font-semibold underline"
                >
                  browse for a file
                </button>
              </div>
            )}
            <input
              ref={input}
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              onChange={(e) => {
                choose(e.target.files?.[0])
                e.target.value = ''
              }}
            />
          </div>
        </>
      )}

      {report && (
        <div>
          {/* Headline counts */}
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="bg-success-50 rounded-lg px-4 py-3">
              <p className="text-success-700 text-2xl font-semibold">{report.accepted}</p>
              <p className="text-success-700 text-xs font-medium">Valid records</p>
            </div>
            <div className={cx('rounded-lg px-4 py-3', report.rejected ? 'bg-danger-50' : 'bg-ink-50')}>
              <p className={cx('text-2xl font-semibold', report.rejected ? 'text-danger-700' : 'text-ink-400')}>
                {report.rejected}
              </p>
              <p className={cx('text-xs font-medium', report.rejected ? 'text-danger-700' : 'text-ink-500')}>
                Errors
              </p>
            </div>
            {report.overwrites > 0 && (
              <div className="bg-warning-50 rounded-lg px-4 py-3">
                <p className="text-warning-700 text-2xl font-semibold">{report.overwrites}</p>
                <p className="text-warning-700 text-xs font-medium">Replace existing</p>
              </div>
            )}
          </div>

          {report.can_import ? (
            <Alert tone="success" title="Ready to import">
              {report.detail}
            </Alert>
          ) : (
            <Alert
              tone="danger"
              title={
                report.rejected
                  ? `${report.rejected} row${report.rejected === 1 ? '' : 's'} must be fixed first`
                  : 'This file cannot be imported'
              }
            >
              {report.detail}
            </Alert>
          )}

          {report.requires_replace_confirmation && (
            <>
              <ReplaceConfirmation
                rows={rows}
                reason={reason}
                onReasonChange={setReason}
              />
              <label className="border-warning-300 bg-warning-50 mt-4 flex cursor-pointer items-start gap-3 rounded-lg border p-3">
                <input
                  type="checkbox"
                  checked={allowReplace}
                  onChange={(e) => setAllowReplace(e.target.checked)}
                  className="accent-warning-600 mt-0.5 size-4"
                />
                <span className="text-warning-900 text-sm">
                  <span className="font-semibold">
                    Replace the {report.overwrites} existing mark
                    {report.overwrites === 1 ? '' : 's'}.
                  </span>{' '}
                  The old value, the new value, my name and the reason are recorded
                  against each one.
                </span>
              </label>
            </>
          )}

          {report.warnings?.length > 0 && report.can_import && (
            <Alert tone="warning" className="mt-3">
              {report.warnings.join(' ')}
            </Alert>
          )}

          {/* The preview table */}
          {rows.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-ink-700 text-sm font-medium">
                  {visible === rows ? 'All rows' : `${invalidRows.length} rows with problems`}
                </p>
                {rows.length > 12 && invalidRows.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setShowAll((v) => !v)}
                    className="text-brand-700 text-sm font-medium underline"
                  >
                    {showAll ? 'Show problems only' : `Show all ${rows.length} rows`}
                  </button>
                )}
              </div>

              <div className="border-ink-200 max-h-72 overflow-y-auto rounded-lg border">
                <table className="w-full text-sm">
                  <thead className="bg-ink-50 sticky top-0">
                    <tr>
                      <th scope="col" className="text-ink-500 px-3 py-2 text-left text-xs font-semibold uppercase">
                        Student number
                      </th>
                      <th scope="col" className="text-ink-500 px-3 py-2 text-left text-xs font-semibold uppercase">
                        Student
                      </th>
                      <th scope="col" className="text-ink-500 px-3 py-2 text-right text-xs font-semibold uppercase">
                        Mark
                      </th>
                      <th scope="col" className="text-ink-500 px-3 py-2 text-left text-xs font-semibold uppercase">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-ink-100 divide-y">
                    {visible.map((row) => (
                      <tr key={row.row} className={cx(!row.valid && 'bg-danger-50/40')}>
                        <td className="text-ink-800 px-3 py-2 font-mono text-xs">
                          {row.student_number}
                        </td>
                        <td className="text-ink-700 px-3 py-2">{row.student_name}</td>
                        <td className="text-ink-900 px-3 py-2 text-right font-medium tabular-nums">
                          {row.marks !== null && row.marks !== undefined
                            ? Number(row.marks).toFixed(0)
                            : row.raw_marks || '—'}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={cx(
                              'flex items-start gap-1.5',
                              row.valid
                                ? row.is_overwrite
                                  ? 'text-warning-700'
                                  : 'text-success-700'
                                : 'text-danger-700',
                            )}
                          >
                            <FontAwesomeIcon
                              icon={
                                row.valid
                                  ? row.is_overwrite
                                    ? 'triangle-exclamation'
                                    : 'circle-check'
                                  : 'circle-exclamation'
                              }
                              className="mt-0.5 shrink-0 text-xs"
                              aria-hidden="true"
                            />
                            <span>{row.message}</span>
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => {
                setReport(null)
                setFile(null)
              }}
              className="text-ink-500 hover:text-ink-800 text-sm underline"
            >
              Choose a different file
            </button>
            <p className="text-ink-400 text-xs">
              {report.can_import || (report.requires_replace_confirmation && allowReplace)
                ? 'Nothing has been saved yet.'
                : report.requires_replace_confirmation
                  ? 'Nothing was saved. Confirm the replacements to continue.'
                  : 'Nothing was saved. Fix the file and upload it again.'}
            </p>
          </div>
        </div>
      )}
    </Modal>
  )
}

export default UploadDialog
