import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import StatTile from '@/components/common/StatTile'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  DataTable,
  PageLoader,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { teacherPortalService } from '@/services/teacherService'
import { statusLabel } from '@/utils/constants'
import { cx, formatDate, formatDateTime } from '@/utils/format'

/**
 * Where each of this teacher's subjects stands against its deadline.
 *
 * Overdue is worked out on the server from the deadline, so this page cannot
 * disagree with what the school office sees.
 */
export function SubmissionStatusPage() {
  useDocumentTitle('Submission Status')

  const { data, loading, error, refresh } = useAsyncData(
    () => teacherPortalService.dashboard(),
    [],
  )
  const cards = data?.subjects ?? []

  const columns = [
    {
      key: 'subject',
      header: 'Subject',
      render: (row) => (
        <div className="min-w-0">
          <p className="text-ink-900 font-medium">{row.subject_name}</p>
          <p className="text-ink-400 font-mono text-xs">{row.subject_code}</p>
        </div>
      ),
    },
    {
      key: 'examination',
      header: 'Examination',
      render: (row) => (
        <div className="min-w-0">
          <p className="text-ink-800">{row.examination_name}</p>
          {row.term_name && <p className="text-ink-400 text-xs">{row.term_name}</p>}
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
        const complete = row.expected_count > 0 && row.submitted_count >= row.expected_count
        return (
          <div className="min-w-[7rem]">
            <p className="text-ink-700 mb-1 text-sm tabular-nums">
              {row.submitted_count} of {row.expected_count}
            </p>
            <div className="bg-ink-100 h-1.5 w-full overflow-hidden rounded-full">
              <div
                className={cx(
                  'h-full rounded-full',
                  complete
                    ? 'bg-success-500'
                    : row.is_past_deadline
                      ? 'bg-danger-500'
                      : 'bg-warning-400',
                )}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )
      },
    },
    {
      key: 'deadline',
      header: 'Deadline',
      render: (row) =>
        row.submission_deadline ? (
          <div className="min-w-0">
            <p
              className={cx(
                'text-sm whitespace-nowrap',
                row.is_past_deadline ? 'text-danger-600 font-medium' : 'text-ink-700',
              )}
            >
              {formatDate(row.submission_deadline)}
            </p>
            {!row.is_past_deadline && row.days_remaining !== null && (
              <p className="text-ink-400 text-xs">
                {row.days_remaining === 0
                  ? 'Due today'
                  : `${row.days_remaining} day${row.days_remaining === 1 ? '' : 's'} left`}
              </p>
            )}
            {row.is_past_deadline && (
              <p className="text-danger-500 text-xs font-medium">Past due</p>
            )}
          </div>
        ) : (
          <span className="text-ink-400 text-sm">Not set</span>
        ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <div className="flex flex-wrap items-center gap-2">
          <Badge status={row.status}>{statusLabel(row.status)}</Badge>
          {row.submitted_at && (
            <span className="text-ink-400 text-xs whitespace-nowrap">
              {formatDateTime(row.submitted_at)}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'action',
      header: '',
      align: 'right',
      render: (row) =>
        row.can_upload ? (
          <Button
            as={Link}
            to={`/teacher/examinations/${row.examination_id}/subjects/${row.subject_id}`}
            variant="secondary"
            size="sm"
            icon="arrow-right"
            iconPosition="right"
          >
            Open
          </Button>
        ) : (
          <span className="text-ink-400 inline-flex items-center gap-1.5 text-xs">
            <FontAwesomeIcon icon="lock" aria-hidden="true" />
            Closed
          </span>
        ),
    },
  ]

  if (loading && !data) return <PageLoader label="Loading your submission status" />

  return (
    <div>
      <PageHeader
        title="Submission Status"
        description="Where each of your subjects stands against its deadline."
        actions={
          <Button variant="secondary" icon="rotate" onClick={refresh}>
            Refresh
          </Button>
        }
      />

      {error && (
        <Alert tone="danger" title="Could not load your status" className="mb-5">
          {error}
        </Alert>
      )}

      {data?.overdue_subjects > 0 && (
        <Alert tone="danger" title="Marks are past due" className="mb-5">
          {data.overdue_subjects === 1
            ? 'One of your subjects is past its submission deadline.'
            : `${data.overdue_subjects} of your subjects are past their submission deadline.`}
        </Alert>
      )}

      {cards.length > 0 && (
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <StatTile
            icon="table-list"
            label="My subjects"
            value={data.total_subjects}
            hint="Assigned this year"
          />
          <StatTile
            icon="circle-check"
            label="Submitted"
            value={data.submitted_subjects}
            hint="Marks delivered"
          />
          <StatTile
            icon="clock"
            label="Outstanding"
            value={data.outstanding_subjects}
            hint={
              data.overdue_subjects > 0
                ? `${data.overdue_subjects} overdue`
                : 'Still to submit'
            }
          />
        </div>
      )}

      <Card>
        {cards.length === 0 ? (
          <CardBody className="p-0">
            <EmptyState
              icon="list-check"
              title={
                data?.current_examination
                  ? 'No subjects assigned to you'
                  : 'No examination is open'
              }
              description={
                data?.current_examination
                  ? 'The school office assigns subjects to teachers.'
                  : 'Your subjects appear here once an examination opens for submission.'
              }
            />
          </CardBody>
        ) : (
          <DataTable
            columns={columns}
            rows={cards}
            rowKey={(row) => `${row.examination_id}-${row.subject_id}`}
          />
        )}
      </Card>
    </div>
  )
}

export default SubmissionStatusPage
