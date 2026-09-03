import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link, useParams } from 'react-router-dom'

import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import UploadDialog from '@/components/teacher/UploadDialog'
import { Alert, Badge, Button, Card, Input, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { getErrorMessage } from '@/services/apiClient'
import { teacherDownloads, teacherPortalService } from '@/services/teacherService'
import { statusLabel } from '@/utils/constants'
import { cx, formatDateTime } from '@/utils/format'

const MIN_MARK = 0
const MAX_MARK = 100

/**
 * The mark sheet for one subject.
 *
 * Two ways in, deliberately: a CSV upload for a whole class at once, and
 * in-place editing for the one mark that needs correcting afterwards.
 */
export function MarkSheetPage() {
  const { examinationId, subjectId } = useParams()
  const [drafts, setDrafts] = useState({})
  const [saving, setSaving] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [busy, setBusy] = useState(null)
  const { toast, show, clear } = useToast()

  const { data: sheet, loading, error, refresh, setData } = useAsyncData(
    () => teacherPortalService.markSheet(examinationId, subjectId),
    [examinationId, subjectId],
  )

  useDocumentTitle(sheet ? `${sheet.subject_name} marks` : 'Mark sheet')

  if (loading && !sheet) return <PageLoader label="Loading the mark sheet" />

  if (error && !sheet) {
    return (
      <div>
        <PageHeader title="Mark sheet" />
        <Alert tone="danger" title="This mark sheet is not available">
          {error}
        </Alert>
        <Button as={Link} to="/teacher/dashboard" className="mt-4" variant="secondary" icon="arrow-right">
          Back to my subjects
        </Button>
      </div>
    )
  }

  const dirty = Object.keys(drafts).length > 0

  function setDraft(studentId, value) {
    setDrafts((previous) => {
      const next = { ...previous }
      const original = sheet.rows.find((r) => r.student_id === studentId)
      const originalValue = original?.marks == null ? '' : String(Number(original.marks))

      if (value === originalValue) {
        delete next[studentId]
      } else {
        next[studentId] = value
      }
      return next
    })
  }

  function invalid(value) {
    if (value === '') return false
    const number = Number(value)
    return Number.isNaN(number) || number < MIN_MARK || number > MAX_MARK
  }

  const hasInvalid = Object.values(drafts).some(invalid)

  async function save() {
    setSaving(true)
    try {
      const entries = Object.entries(drafts)
        .filter(([, value]) => value !== '')
        .map(([studentId, value]) => ({
          student_id: Number(studentId),
          marks: Number(value),
        }))

      if (!entries.length) {
        setDrafts({})
        setSaving(false)
        return
      }

      const updated = await teacherPortalService.saveMarkSheet(
        examinationId,
        subjectId,
        entries,
        'Entered on the mark sheet',
      )
      setData(updated)
      setDrafts({})
      show(`Saved ${entries.length} mark${entries.length === 1 ? '' : 's'}.`)
    } catch (err) {
      show(getErrorMessage(err), 'danger')
    } finally {
      setSaving(false)
    }
  }

  async function download(kind) {
    setBusy(kind)
    try {
      await teacherDownloads[kind](examinationId, subjectId, sheet.subject_code)
    } catch (err) {
      show(getErrorMessage(err, 'That download did not work.'), 'danger')
    } finally {
      setBusy(null)
    }
  }

  const marked = sheet.rows.filter((r) => r.marks !== null).length
  const isDone = sheet.status === 'SUBMITTED' || sheet.status === 'LATE'

  return (
    <div>
      <PageHeader
        title={sheet.subject_name}
        description={`${sheet.subject_code} · ${sheet.examination_name}${sheet.term_name ? ` · ${sheet.term_name}` : ''}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button as={Link} to="/teacher/dashboard" variant="ghost" size="sm">
              My subjects
            </Button>
            <Button
              variant="secondary"
              size="sm"
              icon="download"
              loading={busy === 'template'}
              onClick={() => download('template')}
            >
              Template
            </Button>
            {marked > 0 && (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  icon="file-csv"
                  loading={busy === 'csv'}
                  onClick={() => download('csv')}
                >
                  CSV
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  icon="file-pdf"
                  loading={busy === 'pdf'}
                  onClick={() => download('pdf')}
                >
                  PDF
                </Button>
              </>
            )}
            {sheet.can_edit && (
              <Button size="sm" icon="cloud-arrow-up" onClick={() => setUploadOpen(true)}>
                Upload CSV
              </Button>
            )}
          </div>
        }
      />

      {!sheet.can_edit && sheet.locked_reason && (
        <Alert tone="warning" title="This mark sheet is read-only" className="mb-5">
          {sheet.locked_reason}
        </Alert>
      )}

      {isDone && (
        <Alert tone="success" className="mb-5">
          <span className="font-semibold">Results submitted.</span>{' '}
          {sheet.rows.length} student{sheet.rows.length === 1 ? '' : 's'} on record for this
          subject.
        </Alert>
      )}

      <Card>
        <div className="border-ink-200 flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
          <div className="flex flex-wrap items-center gap-4">
            <Badge status={sheet.status}>
              {sheet.status === 'PENDING' ? 'Not submitted' : statusLabel(sheet.status)}
            </Badge>
            <span className="text-ink-600 text-sm">
              <span className="text-ink-900 font-semibold">{marked}</span> of{' '}
              <span className="text-ink-900 font-semibold">{sheet.rows.length}</span> marked
            </span>
            {sheet.submission_deadline && (
              <span className="text-ink-500 flex items-center gap-1.5 text-sm">
                <FontAwesomeIcon icon="clock" aria-hidden="true" />
                Due {formatDateTime(sheet.submission_deadline)}
              </span>
            )}
          </div>

          {sheet.can_edit && dirty && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setDrafts({})}
                className="text-ink-500 hover:text-ink-800 text-sm underline"
              >
                Discard changes
              </button>
              <Button size="sm" icon="check" onClick={save} loading={saving} disabled={hasInvalid}>
                Save {Object.keys(drafts).length} change
                {Object.keys(drafts).length === 1 ? '' : 's'}
              </Button>
            </div>
          )}
        </div>

        {sheet.rows.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <p className="text-ink-800 font-semibold">Nobody is enrolled in this subject</p>
            <p className="text-ink-500 mt-1 text-sm">
              The school office manages enrolment. Contact them if this looks wrong.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] border-collapse text-sm">
              <thead>
                <tr className="border-ink-200 border-b">
                  <th scope="col" className="text-ink-500 w-12 px-5 py-3 text-left text-xs font-semibold uppercase">
                    #
                  </th>
                  <th scope="col" className="text-ink-500 px-5 py-3 text-left text-xs font-semibold uppercase">
                    Student
                  </th>
                  <th scope="col" className="text-ink-500 w-32 px-5 py-3 text-left text-xs font-semibold uppercase">
                    Mark
                  </th>
                  <th scope="col" className="text-ink-500 w-20 px-5 py-3 text-left text-xs font-semibold uppercase">
                    Grade
                  </th>
                  <th scope="col" className="text-ink-500 px-5 py-3 text-left text-xs font-semibold uppercase">
                    Remark
                  </th>
                </tr>
              </thead>
              <tbody className="divide-ink-100 divide-y">
                {sheet.rows.map((row, index) => {
                  const draft = drafts[row.student_id]
                  const value =
                    draft !== undefined ? draft : row.marks == null ? '' : String(Number(row.marks))
                  const bad = invalid(value)

                  return (
                    <tr key={row.student_id} className={cx(draft !== undefined && 'bg-brand-50/40')}>
                      <td className="text-ink-400 px-5 py-2.5 tabular-nums">{index + 1}</td>
                      <td className="px-5 py-2.5">
                        <p className="text-ink-900 font-medium">{row.student_name}</p>
                        <p className="text-ink-400 font-mono text-xs">{row.student_number}</p>
                      </td>
                      <td className="px-5 py-2.5">
                        {sheet.can_edit ? (
                          <Input
                            type="number"
                            min={MIN_MARK}
                            max={MAX_MARK}
                            step="0.01"
                            value={value}
                            onChange={(e) => setDraft(row.student_id, e.target.value)}
                            error={bad ? 'Enter 0 to 100' : undefined}
                            aria-label={`Mark for ${row.student_name}`}
                            placeholder="—"
                          />
                        ) : (
                          <span className="text-ink-900 font-semibold tabular-nums">
                            {row.marks == null ? '—' : Number(row.marks).toFixed(0)}
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-2.5">
                        {row.grade ? (
                          <Badge tone="brand">{row.grade}</Badge>
                        ) : (
                          <span className="text-ink-400">—</span>
                        )}
                      </td>
                      <td className="text-ink-600 px-5 py-2.5">{row.remarks ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {sheet.can_edit && (
        <p className="text-ink-400 mt-4 flex items-start gap-2 text-xs">
          <FontAwesomeIcon icon="circle-info" className="mt-0.5" aria-hidden="true" />
          Every change is recorded against your name. A blank mark is left unmarked rather
          than saved as zero.
        </p>
      )}

      {uploadOpen && (
        <UploadDialog
          open
          sheet={sheet}
          onClose={() => setUploadOpen(false)}
          onUploaded={(result) => {
            setUploadOpen(false)
            setDrafts({})
            refresh()
            show(result.detail)
          }}
        />
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default MarkSheetPage
