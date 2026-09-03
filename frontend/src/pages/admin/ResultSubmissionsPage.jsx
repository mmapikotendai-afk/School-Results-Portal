import { useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import SubmissionProgress from '@/components/admin/SubmissionProgress'
import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  DataTable,
  PageLoader,
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { academicService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'
import { statusLabel } from '@/utils/constants'
import { cx, formatDateTime } from '@/utils/format'

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'outstanding', label: 'Outstanding' },
  { id: 'overdue', label: 'Overdue' },
  { id: 'submitted', label: 'Submitted' },
]

/**
 * Who owes results, for one examination.
 *
 * Overdue is derived on the server from the examination deadline rather than
 * stored, so nothing here can go stale between page loads and no one has to
 * mark a teacher late by hand.
 */
export function ResultSubmissionsPage() {
  useDocumentTitle('Result Submissions')

  const [examId, setExamId] = useState('')
  const [filter, setFilter] = useState('all')
  const [syncing, setSyncing] = useState(false)
  const { toast, show, clear } = useToast()

  const exams = useAsyncData(() => academicService.listExaminations(), [])
  const examList = useMemo(() => exams.data ?? [], [exams.data])

  // Open on the examination the school is actually working on. Derived during
  // render rather than assigned from an effect, so the first paint is correct.
  const effectiveExamId =
    examId ||
    String(
      (
        examList.find((e) => e.status === 'SUBMISSION_OPEN') ??
        examList.find((e) => e.status !== 'PUBLISHED') ??
        examList[0]
      )?.id ?? '',
    )

  const submissions = useAsyncData(
    () =>
      effectiveExamId
        ? academicService.submissions(Number(effectiveExamId))
        : Promise.resolve([]),
    [effectiveExamId],
  )
  const publication = useAsyncData(
    () =>
      effectiveExamId
        ? academicService.publicationSummary(Number(effectiveExamId))
        : Promise.resolve(null),
    [effectiveExamId],
  )

  const rows = useMemo(() => submissions.data ?? [], [submissions.data])
  const exam = examList.find((e) => String(e.id) === String(effectiveExamId))

  const counts = useMemo(() => {
    const done = rows.filter((r) => r.status === 'SUBMITTED' || r.status === 'LATE').length
    const overdue = rows.filter((r) => r.is_overdue).length
    return {
      total: rows.length,
      done,
      overdue,
      outstanding: rows.length - done,
      progress: rows.length ? Math.round((done / rows.length) * 100) : 0,
    }
  }, [rows])

  const visible = useMemo(() => {
    if (filter === 'outstanding') {
      return rows.filter((r) => r.status !== 'SUBMITTED' && r.status !== 'LATE')
    }
    if (filter === 'overdue') return rows.filter((r) => r.is_overdue)
    if (filter === 'submitted') {
      return rows.filter((r) => r.status === 'SUBMITTED' || r.status === 'LATE')
    }
    return rows
  }, [rows, filter])

  async function sync() {
    setSyncing(true)
    try {
      const result = await academicService.syncSubmissions(Number(effectiveExamId))
      submissions.refresh()
      show(
        result.created
          ? `Added ${result.created} tracking row${result.created === 1 ? '' : 's'}.`
          : 'Tracking is already up to date.',
      )
    } catch (err) {
      show(getErrorMessage(err), 'danger')
    } finally {
      setSyncing(false)
    }
  }

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
      render: (row) => {
        const pct = row.expected_count
          ? Math.round((row.submitted_count / row.expected_count) * 100)
          : 0
        return (
          <div className="min-w-[7rem]">
            <p className="text-ink-700 mb-1 text-sm tabular-nums">
              {row.submitted_count} of {row.expected_count}
            </p>
            <div className="bg-ink-100 h-1.5 w-full overflow-hidden rounded-full">
              <div
                className={cx(
                  'h-full rounded-full',
                  pct === 100 ? 'bg-success-500' : row.is_overdue ? 'bg-danger-500' : 'bg-warning-400',
                )}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )
      },
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <div className="flex flex-wrap items-center gap-2">
          <Badge status={row.status}>{statusLabel(row.status)}</Badge>
          {row.is_overdue && (
            <span className="text-danger-600 text-xs font-semibold whitespace-nowrap">
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
            <p className="text-ink-700 text-sm whitespace-nowrap">
              {formatDateTime(row.submitted_at)}
            </p>
            {row.submitted_by && (
              <p className="text-ink-400 text-xs">by {row.submitted_by}</p>
            )}
          </div>
        ) : (
          <span className="text-ink-400 text-sm">Not yet</span>
        ),
    },
  ]

  if (exams.loading && !exams.data) return <PageLoader label="Loading examinations" />

  return (
    <div>
      <PageHeader
        title="Result Submissions"
        description="Which teachers have delivered marks, and who is still outstanding."
        actions={
          effectiveExamId && (
            <Button variant="secondary" icon="rotate" onClick={sync} loading={syncing}>
              Sync assignments
            </Button>
          )
        }
      />

      {(exams.error || submissions.error) && (
        <Alert tone="danger" title="Could not load submissions" className="mb-5">
          {exams.error || submissions.error}
        </Alert>
      )}

      {examList.length === 0 ? (
        <Card>
          <CardBody className="p-0">
            <EmptyState
              icon="file-lines"
              title="No examinations yet"
              description="Submissions are tracked per examination. Create one to begin."
              action={
                <Button as={Link} to="/admin/examinations" icon="arrow-right">
                  Go to Examinations
                </Button>
              }
            />
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-5">
          <Card>
            <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <Select
                label="Examination"
                value={effectiveExamId}
                onChange={(e) => setExamId(e.target.value)}
                options={examList.map((e) => ({
                  value: e.id,
                  label: `${e.name}${e.term_name ? ` · ${e.term_name}` : ''}`,
                }))}
                className="sm:max-w-md"
              />
              {exam && (
                <div className="flex flex-wrap items-center gap-2 pb-0.5">
                  <Badge status={exam.status}>{statusLabel(exam.status)}</Badge>
                  {exam.submission_deadline && (
                    <span className="text-ink-500 text-sm">
                      Deadline {formatDateTime(exam.submission_deadline)}
                    </span>
                  )}
                </div>
              )}
            </CardBody>
          </Card>

          {counts.total > 0 && (
            <Card>
              <CardHeader
                icon="list-check"
                title="Submission progress"
                description={exam?.name}
              />
              <CardBody>
                <SubmissionProgress
                  submitted={counts.done}
                  pending={counts.outstanding}
                  overdue={counts.overdue}
                  total={counts.total}
                  progress={counts.progress}
                />
              </CardBody>
            </Card>
          )}

          {publication.data && !publication.data.can_publish && counts.total > 0 && (
            <Alert tone="warning" title="Not ready to publish">
              {counts.outstanding === 0
                ? 'All marks are in. Move the examination through review to publish it.'
                : `${counts.outstanding} subject${counts.outstanding === 1 ? '' : 's'} still to be submitted before results can be published.`}
            </Alert>
          )}

          <Card>
            <div className="border-ink-200 flex flex-wrap items-center gap-2 border-b px-5 py-3">
              <div className="flex flex-wrap gap-1" role="group" aria-label="Filter submissions">
                {FILTERS.map((f) => {
                  const count =
                    f.id === 'all'
                      ? counts.total
                      : f.id === 'overdue'
                        ? counts.overdue
                        : f.id === 'submitted'
                          ? counts.done
                          : counts.outstanding
                  return (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => setFilter(f.id)}
                      aria-pressed={filter === f.id}
                      className={cx(
                        'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                        filter === f.id
                          ? 'bg-brand-50 text-brand-800'
                          : 'text-ink-600 hover:bg-ink-100 hover:text-ink-900',
                      )}
                    >
                      {f.label}
                      <span className="text-ink-400 ml-1.5 tabular-nums">{count}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            <DataTable
              columns={columns}
              rows={visible}
              loading={submissions.loading && !submissions.data}
              empty={
                <EmptyState
                  icon={filter === 'overdue' ? 'circle-check' : 'inbox'}
                  title={
                    rows.length === 0
                      ? 'No submissions are being tracked'
                      : filter === 'overdue'
                        ? 'Nothing is overdue'
                        : 'Nothing matches this filter'
                  }
                  description={
                    rows.length === 0
                      ? 'Tracking rows are created when the examination opens for submission. If teachers were assigned since then, use Sync assignments.'
                      : filter === 'overdue'
                        ? 'Every teacher is either inside the deadline or already done.'
                        : 'Try a different filter.'
                  }
                  action={
                    rows.length > 0 &&
                    filter !== 'all' && (
                      <Button variant="secondary" onClick={() => setFilter('all')}>
                        Show all
                      </Button>
                    )
                  }
                />
              }
            />
          </Card>
        </div>
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default ResultSubmissionsPage
