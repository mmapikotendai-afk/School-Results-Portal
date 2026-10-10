import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link, useParams } from 'react-router-dom'

import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import UploadDialog from '@/components/teacher/UploadDialog'
import { DataTable, Alert, Badge, Button, Card, Input, Modal, PageLoader, Select } from '@/components/ui'
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
  const [search, setSearch] = useState('')
  const [classFilter, setClassFilter] = useState('')
  const [formFilter, setFormFilter] = useState('')
  const [sort, setSort] = useState('student_number')
  const [review, setReview] = useState(null)
  const { toast, show, clear } = useToast()

  const { data: sheet, loading, error, refresh, setData } = useAsyncData(
    () => teacherPortalService.markSheet(examinationId, subjectId),
    [examinationId, subjectId],
  )

  useDocumentTitle(sheet ? `${sheet.subject_name} marks` : 'Mark sheet')

  const dirty = Object.keys(drafts).length > 0

  useEffect(() => {
    const warn = event => {
      if (!dirty) return
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

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

  async function openReview() {
    if (dirty) {
      show('Save the draft before reviewing it.', 'warning')
      return
    }
    setBusy('review')
    try { setReview(await teacherPortalService.reviewMarkSheet(examinationId, subjectId)) }
    catch (err) { show(getErrorMessage(err), 'danger') }
    finally { setBusy(null) }
  }

  async function submit() {
    setSaving(true)
    try {
      const updated = await teacherPortalService.submitMarkSheet(examinationId, subjectId)
      setData(updated); setReview(null)
      show('Results submitted. The school can now include them in its review process.')
    } catch (err) { show(getErrorMessage(err), 'danger') }
    finally { setSaving(false) }
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
  const classOptions = [...new Map(sheet.rows.filter(row => row.class_name).map(row => [row.class_name, { value: row.class_name, label: row.class_name }])).values()]
  const formOptions = [...new Set(sheet.rows.map(row => row.form_level).filter(Boolean))].map(value => ({ value, label: value.replaceAll('_', ' ') }))
  const visibleRows = (() => {
    const needle = search.trim().toLowerCase()
    const rows = sheet.rows.filter(row =>
      (!needle || row.student_name.toLowerCase().includes(needle) || row.student_number.toLowerCase().includes(needle))
      && (!classFilter || row.class_name === classFilter)
      && (!formFilter || row.form_level === formFilter),
    )
    return rows.sort((a, b) => {
      if (sort === 'marks') return (a.marks ?? -1) - (b.marks ?? -1)
      return String(a[sort] ?? '').localeCompare(String(b[sort] ?? ''), undefined, { numeric: true })
    })
  })()

  function pasteMarks(rowIndex, event) {
    const raw = event.clipboardData?.getData('text/plain')
    if (!raw || !/[\r\n\t]/.test(raw)) return
    event.preventDefault()
    const values = raw.split(/[\r\n\t]+/).filter(value => value.trim() !== '')
    values.forEach((value, index) => {
      const row = visibleRows[rowIndex + index]
      if (row) setDraft(row.student_id, value.trim())
    })
  }

  function navigateMark(event, rowIndex) {
    if (!['ArrowUp', 'ArrowDown', 'Enter'].includes(event.key)) return
    event.preventDefault()
    const next = event.key === 'ArrowUp' ? rowIndex - 1 : rowIndex + 1
    document.querySelector(`[data-mark-row="${next}"]`)?.focus()
  }

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

          {sheet.can_edit && (
            <div className="flex items-center gap-2">
              {dirty && <button
                type="button"
                onClick={() => setDrafts({})}
                className="text-ink-500 hover:text-ink-800 text-sm underline"
              >
                Discard changes
              </button>}
              <Button size="sm" variant="secondary" icon="check" onClick={save} loading={saving} disabled={!dirty || hasInvalid}>
                Save draft{dirty ? ` (${Object.keys(drafts).length})` : ''}
              </Button>
              <Button size="sm" icon="arrow-right" onClick={openReview} loading={busy === 'review'}>Review & submit</Button>
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
          <><div className="grid gap-3 border-b border-ink-200 px-5 py-4 md:grid-cols-4"><Input label="Find student" value={search} onChange={event => setSearch(event.target.value)} placeholder="Name or student number" /><Select label="Form" value={formFilter} onChange={event => setFormFilter(event.target.value)} options={formOptions} placeholder="All forms" /><Select label="Class" value={classFilter} onChange={event => setClassFilter(event.target.value)} options={classOptions} placeholder="All classes" /><Select label="Sort by" value={sort} onChange={event => setSort(event.target.value)} options={[{ value: 'student_number', label: 'Student number' }, { value: 'student_name', label: 'Student name' }, { value: 'class_name', label: 'Class' }, { value: 'marks', label: 'Mark' }]} /></div>
          <DataTable
            rows={visibleRows}
            rowKey={row => row.student_id}
            columns={[
              { key: 'student_name', header: 'Student', primary: true, render: row => <div><p className="font-medium text-ink-900">{row.student_name}</p><p className="mt-1 text-xs text-ink-500">{row.student_number} · {row.class_name ?? 'No class'}</p></div> },
              { key: 'marks', header: 'Mark /100', render: row => {
                const draft = drafts[row.student_id]
                const value = draft !== undefined ? draft : row.marks == null ? '' : String(Number(row.marks))
                const rowIndex = visibleRows.findIndex(item => item.student_id === row.student_id)
                return sheet.can_edit ? <Input data-mark-row={rowIndex} type="number" min={MIN_MARK} max={MAX_MARK} step="0.01" value={value} onChange={e => setDraft(row.student_id, e.target.value)} onPaste={event => pasteMarks(rowIndex, event)} onKeyDown={event => navigateMark(event, rowIndex)} error={invalid(value) ? 'Enter 0 to 100' : undefined} aria-label={'Mark for ' + row.student_name} placeholder="?" className={cx('max-w-28', draft !== undefined && 'bg-brand-50')} /> : <span className="font-semibold tabular-nums">{row.marks == null ? '?' : Number(row.marks).toFixed(0)}</span>
              } },
              { key: 'grade', header: 'Grade', render: row => row.grade ? <Badge tone="brand">{row.grade}</Badge> : '?' },
              { key: 'remarks', header: 'Remark', render: row => row.remarks ?? '?' },
            ]}
          /></>
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

      <Modal open={Boolean(review)} onClose={() => setReview(null)} title="Submission review" description={`${sheet.subject_name} · ${sheet.examination_name}`} footer={<><Button variant="secondary" onClick={() => setReview(null)}>Back to editing</Button><Button onClick={submit} loading={saving} disabled={!review?.can_submit} icon="check">Submit results</Button></>}>
        {review && <div className="space-y-3 text-sm"><dl className="divide-y divide-ink-200 border-y border-ink-200"><div className="flex justify-between py-3"><dt>Expected students</dt><dd className="font-semibold">{review.expected_students}</dd></div><div className="flex justify-between py-3"><dt>Marks entered</dt><dd className="font-semibold">{review.marks_entered}</dd></div><div className="flex justify-between py-3"><dt>Missing marks</dt><dd className="font-semibold">{review.missing_marks}</dd></div></dl><Alert tone={review.can_submit ? 'success' : 'warning'}>{review.detail}</Alert></div>}
      </Modal>

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default MarkSheetPage
