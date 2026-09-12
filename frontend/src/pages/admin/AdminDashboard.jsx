import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import PageHeader from '@/components/common/PageHeader'
import StatTile from '@/components/common/StatTile'
import SubmissionProgress from '@/components/admin/SubmissionProgress'
import { Alert, Badge, Button, Card, CardBody, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useAuth from '@/hooks/useAuth'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { dashboardService } from '@/services/adminService'
import { statusLabel } from '@/utils/constants'
import { cx, formatDate, formatDateTime } from '@/utils/format'

/** The three publication states, each with its own colour and icon. */
const PUBLICATION = {
  published: {
    tone: 'bg-success-50 border-success-100 text-success-800',
    badge: 'success',
    icon: 'circle-check',
  },
  awaiting_review: {
    tone: 'bg-warning-50 border-warning-100 text-warning-800',
    badge: 'warning',
    icon: 'pen-to-square',
  },
  awaiting_submissions: {
    tone: 'bg-brand-50 border-brand-200 text-brand-900',
    badge: 'brand',
    icon: 'clock',
  },
}

const QUICK_ACTIONS = [
  { to: '/admin/students', label: 'Add Student', icon: 'user-graduate' },
  { to: '/admin/teachers', label: 'Add Teacher', icon: 'users' },
  { to: '/admin/subjects', label: 'Add Subject', icon: 'book' },
  { to: '/admin/examinations', label: 'Create Examination', icon: 'file-lines' },
  { to: '/admin/examinations', label: 'Monitor Submissions', icon: 'clock' },
  { to: '/admin/results', label: 'View Results', icon: 'table-list' },
]

/** A responsive table of teachers who still owe results. */
function OutstandingTable({ rows, showDaysOverdue }) {
  return (
    <div className="overflow-x-auto">
      <table className="tabular w-full min-w-[30rem] border-collapse text-sm">
        <thead>
          <tr className="border-ink-900 border-b-2">
            <th scope="col" className="rule-label px-5 py-2.5 text-left">
              Teacher
            </th>
            <th scope="col" className="rule-label px-5 py-2.5 text-left">
              Subject
            </th>
            <th scope="col" className="rule-label px-5 py-2.5 text-left">
              Deadline
            </th>
            {showDaysOverdue && (
              <th scope="col" className="rule-label px-5 py-2.5 text-right">
                Days overdue
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-ink-200 divide-y">
          {rows.map((row) => (
            <tr key={row.submission_id}>
              <td className="text-ink-900 px-5 py-2.5 font-medium">{row.teacher_name}</td>
              <td className="px-5 py-2.5">
                <span className="text-ink-800">{row.subject_name}</span>
                <span className="text-ink-400 ml-2 font-mono text-xs">{row.subject_code}</span>
                {row.expected_count > 0 && (
                  <span className="text-ink-400 ml-2 text-xs">
                    {row.submitted_count}/{row.expected_count} marked
                  </span>
                )}
              </td>
              <td className="text-ink-600 px-5 py-2.5">{formatDate(row.deadline)}</td>
              {showDaysOverdue && (
                <td className="px-5 py-2.5 text-right">
                  <span className="text-danger-700 font-semibold tabular-nums">
                    {row.days_overdue ?? 0}
                  </span>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Administrator dashboard.
 *
 * Answers one question: where has this examination got to, and who is holding
 * it up. Deliberately narrow - nothing here reports on anything but results
 * collection and publication.
 */
export function AdminDashboard() {
  useDocumentTitle('Dashboard')
  const { user } = useAuth()
  const { data, loading, error, refresh } = useAsyncData(() => dashboardService.stats(), [])

  if (loading && !data) return <PageLoader label="Loading dashboard" />

  const exam = data?.current_examination
  const publication = data?.publication
  const style = PUBLICATION[publication?.state] ?? PUBLICATION.awaiting_submissions

  return (
    <div>
      <PageHeader
        eyebrow="Administration"
        title={`Welcome back, ${user?.full_name?.split(' ')[0] ?? 'Administrator'}`}
        description={
          data?.active_year_name
            ? `${data.active_year_name}${data.active_term_name ? ` · ${data.active_term_name}` : ''}`
            : 'Set up an academic year to get started.'
        }
        actions={
          <Button variant="secondary" size="sm" icon="rotate" onClick={refresh} loading={loading}>
            Refresh
          </Button>
        }
      />

      {error && (
        <Alert tone="danger" className="mb-6">
          {error}
        </Alert>
      )}

      {!data?.active_year_name && !error && (
        <Alert tone="info" title="No active academic year" className="mb-6">
          Create an academic year and term before adding students, so enrolment and
          results have somewhere to belong.{' '}
          <Link to="/admin/academic" className="font-semibold underline">
            Set up the academic year
          </Link>
        </Alert>
      )}

      {/* OVERVIEW */}
      <div className="grid gap-5 sm:grid-cols-3">
        <StatTile icon="user-graduate" label="Total students" value={data?.total_students ?? 0} hint="Active accounts" />
        <StatTile icon="users" label="Total teachers" value={data?.total_teachers ?? 0} hint="Active accounts" />
        <StatTile icon="book" label="Total subjects" value={data?.total_subjects ?? 0} hint="Currently offered" />
      </div>

      {exam ? (
        <>
          {/* CURRENT EXAMINATION + SUBMISSION PROGRESS */}
          <div className="mt-6 grid gap-5 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <div className="border-ink-200 flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4">
                <div className="min-w-0">
                  <h2 className="font-serif text-lg font-semibold">{exam.name}</h2>
                  <p className="text-ink-500 mt-0.5 text-sm">
                    {exam.term_name}
                    {exam.academic_year_name ? ` · ${exam.academic_year_name}` : ''}
                  </p>
                </div>
                <Badge status={exam.status}>{statusLabel(exam.status)}</Badge>
              </div>

              <CardBody>
                <p
                  className={cx(
                    'mb-5 flex items-center gap-2 text-sm',
                    exam.is_past_deadline ? 'text-danger-600 font-medium' : 'text-ink-500',
                  )}
                >
                  <FontAwesomeIcon
                    icon={exam.is_past_deadline ? 'triangle-exclamation' : 'clock'}
                    aria-hidden="true"
                  />
                  {exam.submission_deadline ? (
                    <>
                      Submission deadline {formatDateTime(exam.submission_deadline)}
                      {exam.is_past_deadline && ' — passed'}
                    </>
                  ) : (
                    'No submission deadline set'
                  )}
                </p>

                <SubmissionProgress
                  submitted={data.submissions_complete}
                  pending={data.submissions_pending}
                  overdue={data.submissions_overdue}
                  total={data.submissions_total}
                  progress={data.submission_progress}
                />
              </CardBody>
            </Card>

            {/* PUBLICATION STATUS */}
            <Card>
              <div className="border-ink-200 border-b px-5 py-4">
                <h2 className="text-base font-semibold">Publication</h2>
              </div>
              <CardBody>
                <div className={cx('border px-4 py-4', style.tone)}>
                  <FontAwesomeIcon icon={style.icon} className="text-xl" aria-hidden="true" />
                  <p className="mt-2 font-semibold">{publication?.label}</p>
                  {publication?.detail && (
                    <p className="mt-1 text-sm opacity-90">{publication.detail}</p>
                  )}
                  {publication?.published_by && (
                    <p className="mt-2 text-xs opacity-80">
                      Published by {publication.published_by}
                      {publication.published_at && ` on ${formatDate(publication.published_at)}`}
                    </p>
                  )}
                </div>

                <dl className="mt-5 space-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <dt className="text-ink-600 flex items-center gap-2">
                      <span className="bg-success-500 size-2 rounded-full" aria-hidden="true" />
                      Results published
                    </dt>
                    <dd className="text-ink-900 font-semibold">{data.results_published}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="text-ink-600 flex items-center gap-2">
                      <span className="bg-ink-300 size-2 rounded-full" aria-hidden="true" />
                      Not yet published
                    </dt>
                    <dd className="text-ink-900 font-semibold">{data.results_unpublished}</dd>
                  </div>
                </dl>

                <Button
                  as={Link}
                  to="/admin/examinations"
                  variant="secondary"
                  size="sm"
                  className="mt-5"
                  icon="arrow-right"
                  iconPosition="right"
                  fullWidth
                >
                  Manage publication
                </Button>
              </CardBody>
            </Card>
          </div>

          {/* OVERDUE RESULTS */}
          {data.overdue_submissions?.length > 0 && (
            <Card className="mt-5">
              <div className="border-danger-100 bg-danger-50 flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
                <div className="flex items-center gap-3">
                  <span className="bg-danger-600 flex size-9 items-center justify-center text-white">
                    <FontAwesomeIcon icon="triangle-exclamation" aria-hidden="true" />
                  </span>
                  <div>
                    <h2 className="text-danger-800 text-base font-semibold">Overdue results</h2>
                    <p className="text-danger-700 mt-0.5 text-sm">
                      {data.overdue_submissions.length} subject
                      {data.overdue_submissions.length === 1 ? '' : 's'} past the deadline.
                    </p>
                  </div>
                </div>
                <Button as={Link} to="/admin/examinations" size="sm" variant="secondary">
                  Chase up
                </Button>
              </div>
              <OutstandingTable rows={data.overdue_submissions} showDaysOverdue />
            </Card>
          )}

          {/* PENDING RESULTS */}
          {data.pending_submissions?.length > 0 && (
            <Card className="mt-5">
              <div className="border-ink-200 flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
                <div className="flex items-center gap-3">
                  <span className="bg-warning-600 flex size-9 items-center justify-center text-white">
                    <FontAwesomeIcon icon="clock" aria-hidden="true" />
                  </span>
                  <div>
                    <h2 className="text-base font-semibold">Pending results</h2>
                    <p className="text-ink-500 mt-0.5 text-sm">
                      Still within the deadline.
                    </p>
                  </div>
                </div>
              </div>
              <OutstandingTable rows={data.pending_submissions} />
            </Card>
          )}

          {data.submissions_total > 0 &&
            !data.pending_submissions?.length &&
            !data.overdue_submissions?.length && (
              <Alert tone="success" title="All required results submitted" className="mt-5">
                Every teacher has submitted results for this examination.
              </Alert>
            )}
        </>
      ) : (
        !error && (
          <Card className="mt-6">
            <CardBody>
              <div className="py-8 text-center">
                <span className="bg-ink-100 text-ink-400 mx-auto mb-4 flex size-12 items-center justify-center rounded-full">
                  <FontAwesomeIcon icon="file-lines" className="text-lg" aria-hidden="true" />
                </span>
                <p className="text-ink-800 font-semibold">No examination set up</p>
                <p className="text-ink-500 mt-1 text-sm">
                  Create an examination to start collecting results from teachers.
                </p>
                <Button as={Link} to="/admin/examinations" className="mt-5" icon="plus">
                  Create an examination
                </Button>
              </div>
            </CardBody>
          </Card>
        )
      )}

      {/* QUICK ACTIONS */}
      <Card className="mt-5">
        <div className="border-ink-200 border-b px-5 py-4">
          <h2 className="text-base font-semibold">Quick actions</h2>
        </div>
        <CardBody>
          <div className="border-ink-200 grid grid-cols-2 gap-px border bg-ink-200 sm:grid-cols-3 lg:grid-cols-6">
            {QUICK_ACTIONS.map((action) => (
              <Link
                key={action.label}
                to={action.to}
                className="hover:bg-brand-50 group flex flex-col items-center gap-2.5 bg-white px-3 py-5 text-center transition-colors"
              >
                <span className="text-brand-800 flex size-6 items-center justify-center">
                  <FontAwesomeIcon icon={action.icon} aria-hidden="true" />
                </span>
                <span className="text-ink-700 group-hover:text-brand-900 text-[11px] font-semibold tracking-wide">
                  {action.label}
                </span>
              </Link>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  )
}

export default AdminDashboard
