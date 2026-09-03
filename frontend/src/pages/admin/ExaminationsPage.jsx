import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import SubmissionMonitor from '@/components/admin/SubmissionMonitor'
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  Input,
  Modal,
  RowAction,
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { academicService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'
import { statusLabel } from '@/utils/constants'
import { cx, formatDateTime } from '@/utils/format'

/** Plain-language description of each step, shown on the status buttons. */
const TRANSITION_COPY = {
  SUBMISSION_OPEN: { label: 'Open for submission', icon: 'cloud-arrow-up', variant: 'primary' },
  SUBMISSION_COMPLETE: { label: 'Close submissions', icon: 'check', variant: 'secondary' },
  UNDER_REVIEW: { label: 'Send for review', icon: 'pen-to-square', variant: 'secondary' },
  PUBLISHED: { label: 'Publish results', icon: 'circle-check', variant: 'accent' },
  DRAFT: { label: 'Return to draft', icon: 'rotate', variant: 'secondary' },
}

function ExaminationForm({ open, exam, terms, onClose, onSaved }) {
  const isEdit = Boolean(exam)
  const activeTerm = terms.find((t) => t.is_active)
  const [form, setForm] = useState({
    term_id: exam?.term_id ?? activeTerm?.id ?? '',
    name: exam?.name ?? '',
    // datetime-local wants "YYYY-MM-DDTHH:mm"; trim any seconds the API sends.
    submission_deadline: exam?.submission_deadline?.slice(0, 16) ?? '',
  })
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const change = (e) => {
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }))
    setFieldErrors((p) => ({ ...p, [e.target.name]: undefined }))
  }

  async function submit(event) {
    event.preventDefault()
    const errors = {}
    if (!form.name.trim()) errors.name = 'Enter an examination name.'
    if (!isEdit && !form.term_id) errors.term_id = 'Choose a term.'
    setFieldErrors(errors)
    if (Object.keys(errors).length) return

    setSaving(true)
    setError(null)
    try {
      const payload = {
        name: form.name.trim(),
        submission_deadline: form.submission_deadline || null,
      }
      if (isEdit) {
        await academicService.updateExamination(exam.id, payload)
        onSaved(`${payload.name} has been updated.`)
      } else {
        await academicService.createExamination({ ...payload, term_id: Number(form.term_id) })
        onSaved(`${payload.name} has been created.`)
      }
    } catch (err) {
      setError(getErrorMessage(err))
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit examination' : 'Create examination'}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving} icon="check">
            {isEdit ? 'Save changes' : 'Create examination'}
          </Button>
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-4" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}
      <form onSubmit={submit} noValidate className="space-y-4">
        {!isEdit && (
          <Select
            label="Term"
            name="term_id"
            value={form.term_id}
            onChange={change}
            error={fieldErrors.term_id}
            placeholder="Choose a term"
            options={terms.map((t) => ({
              value: t.id,
              label: `${t.name}${t.academic_year_name ? ` · ${t.academic_year_name}` : ''}`,
            }))}
            disabled={saving}
          />
        )}
        <Input
          label="Examination name"
          name="name"
          value={form.name}
          onChange={change}
          error={fieldErrors.name}
          placeholder="End of Term 1 Examination"
          disabled={saving}
          required
        />
        <Input
          label="Submission deadline"
          name="submission_deadline"
          type="datetime-local"
          value={form.submission_deadline}
          onChange={change}
          hint="Submissions after this are recorded as late."
          disabled={saving}
        />
      </form>
    </Modal>
  )
}

/** Confirmation before publishing, showing exactly what would be released. */
function PublishDialog({ open, exam, onClose, onConfirm }) {
  const { data: summary, loading } = useAsyncData(
    () => academicService.publicationSummary(exam.id),
    [exam.id],
  )

  return (
    <ConfirmDialog
      open={open}
      onClose={onClose}
      onConfirm={onConfirm}
      title="Publish these results?"
      message={
        loading
          ? 'Checking what this would release…'
          : summary?.can_publish
            ? `${exam.name} will become visible to every student it covers. This can be undone by returning it to review.`
            : 'This examination cannot be published yet.'
      }
      detail={
        summary && (
          <div className="space-y-3">
            <div className="bg-ink-50 grid grid-cols-3 gap-3 rounded-lg px-4 py-3 text-center">
              <div>
                <p className="text-ink-900 text-xl font-semibold">{summary.result_count}</p>
                <p className="text-ink-500 text-xs">Results</p>
              </div>
              <div>
                <p className="text-ink-900 text-xl font-semibold">{summary.student_count}</p>
                <p className="text-ink-500 text-xs">Students</p>
              </div>
              <div>
                <p className="text-ink-900 text-xl font-semibold">{summary.subject_count}</p>
                <p className="text-ink-500 text-xs">Subjects</p>
              </div>
            </div>

            {summary.submissions_outstanding > 0 && (
              <Alert tone="warning">
                {summary.submissions_outstanding} teacher submission
                {summary.submissions_outstanding === 1 ? ' is' : 's are'} still
                outstanding. Publishing now releases what has been collected so far.
              </Alert>
            )}

            {!summary.can_publish && summary.blocking_reason && (
              <Alert tone="danger">{summary.blocking_reason}</Alert>
            )}
          </div>
        )
      }
      confirmLabel="Publish results"
      variant="accent"
      icon="circle-check"
    />
  )
}

export function ExaminationsPage() {
  useDocumentTitle('Examinations')

  const [formState, setFormState] = useState(null)
  const [monitoring, setMonitoring] = useState(null)
  const [publishing, setPublishing] = useState(null)
  const [transition, setTransition] = useState(null)
  const { toast, show, clear } = useToast()

  const exams = useAsyncData(() => academicService.listExaminations(), [])
  const { data: terms } = useAsyncData(() => academicService.listTerms(), [])

  async function applyStatus(exam, status) {
    try {
      await academicService.setExaminationStatus(exam.id, status)
      show(
        status === 'PUBLISHED'
          ? `${exam.name} has been published.`
          : `${exam.name} is now ${statusLabel(status).toLowerCase()}.`,
      )
      exams.refresh()
    } catch (err) {
      show(getErrorMessage(err), 'danger')
      throw err
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Examination',
      render: (row) => (
        <div className="min-w-0">
          <p className="text-ink-900 font-medium">{row.name}</p>
          <p className="text-ink-400 text-xs">
            {row.term_name}
            {row.academic_year_name ? ` · ${row.academic_year_name}` : ''}
          </p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <Badge status={row.status}>{statusLabel(row.status)}</Badge>,
    },
    {
      key: 'deadline',
      header: 'Deadline',
      render: (row) =>
        row.submission_deadline ? (
          <span className="text-ink-600 text-sm">{formatDateTime(row.submission_deadline)}</span>
        ) : (
          <span className="text-ink-400">Not set</span>
        ),
    },
    {
      key: 'progress',
      header: 'Submissions',
      render: (row) =>
        row.submission_total ? (
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation()
              setMonitoring(row)
            }}
            className="text-left"
          >
            <span
              className={cx(
                'text-sm font-medium',
                row.submission_overdue > 0 ? 'text-danger-600' : 'text-ink-800',
              )}
            >
              {row.submission_done}/{row.submission_total}
            </span>
            {row.submission_overdue > 0 && (
              <span className="text-danger-600 ml-2 text-xs">
                <FontAwesomeIcon icon="triangle-exclamation" aria-hidden="true" />{' '}
                {row.submission_overdue} overdue
              </span>
            )}
          </button>
        ) : (
          <span className="text-ink-400 text-sm">Not open yet</span>
        ),
    },
    {
      key: 'result_count',
      header: 'Results',
      render: (row) => <span className="text-ink-700">{row.result_count}</span>,
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) => (
        <div className="flex items-center justify-end gap-0.5">
          {row.submission_total > 0 && (
            <RowAction icon="clock" label="Submission monitor" onClick={() => setMonitoring(row)} />
          )}
          <RowAction
            icon="pen-to-square"
            label="Edit"
            tone="brand"
            onClick={() => setFormState({ exam: row })}
          />
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Examinations"
        description="Open submissions, watch them come in, and publish the results."
        actions={
          <Button
            icon="plus"
            onClick={() => setFormState({ exam: null })}
            disabled={!terms?.length}
          >
            Create examination
          </Button>
        }
      />

      {exams.error && (
        <Alert tone="danger" className="mb-5">
          {exams.error}
        </Alert>
      )}

      {terms && terms.length === 0 && (
        <Alert tone="info" title="No terms yet" className="mb-5">
          An examination belongs to a term. Create an academic year and term first.
        </Alert>
      )}

      <Card>
        <DataTable
          columns={columns}
          rows={exams.data ?? []}
          loading={exams.loading && !exams.data}
          empty={
            <EmptyState
              icon="file-lines"
              title="No examinations yet"
              description="Create one to start collecting results from teachers."
              action={
                terms?.length > 0 && (
                  <Button icon="plus" onClick={() => setFormState({ exam: null })}>
                    Create examination
                  </Button>
                )
              }
            />
          }
        />
      </Card>

      {/* Lifecycle controls, one card per examination that can move on. */}
      {(exams.data ?? []).filter((e) => e.allowed_transitions.length > 0).length > 0 && (
        <Card className="mt-5">
          <div className="border-ink-200 border-b px-5 py-4">
            <h3 className="text-base font-semibold">Result publication</h3>
            <p className="text-ink-500 mt-0.5 text-sm">
              An examination moves one step at a time, so results cannot be released
              before they have been collected and reviewed.
            </p>
          </div>
          <div className="divide-ink-100 divide-y">
            {(exams.data ?? [])
              .filter((e) => e.allowed_transitions.length > 0)
              .map((exam) => (
                <div
                  key={exam.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
                >
                  <div className="min-w-0">
                    <p className="text-ink-900 font-medium">{exam.name}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <Badge status={exam.status}>{statusLabel(exam.status)}</Badge>
                      <span className="text-ink-400 text-xs">{exam.result_count} results</span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {exam.allowed_transitions.map((next) => {
                      const copy = TRANSITION_COPY[next] ?? { label: next, variant: 'secondary' }
                      return (
                        <Button
                          key={next}
                          size="sm"
                          variant={copy.variant}
                          icon={copy.icon}
                          onClick={() =>
                            next === 'PUBLISHED'
                              ? setPublishing(exam)
                              : setTransition({ exam, status: next, copy })
                          }
                        >
                          {copy.label}
                        </Button>
                      )
                    })}
                  </div>
                </div>
              ))}
          </div>
        </Card>
      )}

      {formState && (
        <ExaminationForm
          open
          exam={formState.exam}
          terms={terms ?? []}
          onClose={() => setFormState(null)}
          onSaved={(message) => {
            setFormState(null)
            show(message)
            exams.refresh()
          }}
        />
      )}

      {monitoring && (
        <SubmissionMonitor
          open
          exam={monitoring}
          onClose={() => setMonitoring(null)}
          onSynced={(message) => {
            show(message)
            exams.refresh()
          }}
        />
      )}

      {publishing && (
        <PublishDialog
          open
          exam={publishing}
          onClose={() => setPublishing(null)}
          onConfirm={() => applyStatus(publishing, 'PUBLISHED')}
        />
      )}

      <ConfirmDialog
        open={Boolean(transition)}
        onClose={() => setTransition(null)}
        onConfirm={() => applyStatus(transition.exam, transition.status)}
        title={`${transition?.copy.label}?`}
        message={
          transition?.status === 'SUBMISSION_OPEN'
            ? `Teachers assigned to subjects will be able to upload results for ${transition?.exam.name}, and submission tracking will be created for each of them.`
            : transition?.status === 'UNDER_REVIEW'
              ? `${transition?.exam.name} moves to review, where results can be corrected before they are published.`
              : `${transition?.exam.name} will move to ${statusLabel(transition?.status).toLowerCase()}.`
        }
        confirmLabel={transition?.copy.label}
        icon={transition?.copy.icon}
      />

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default ExaminationsPage
