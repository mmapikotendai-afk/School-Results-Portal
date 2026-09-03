import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import { Alert, Badge, Button, Card, CardBody, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { teacherPortalService } from '@/services/teacherService'
import { statusLabel } from '@/utils/constants'
import { cx, formatDate } from '@/utils/format'

/**
 * Choose a subject to record marks for.
 *
 * Only subjects assigned to this teacher appear, and a subject that cannot
 * currently accept marks says why rather than failing at the next step. The
 * server enforces both rules again, so nothing here is load-bearing.
 */
export function UploadResultsPage() {
  useDocumentTitle('Upload Results')

  const { data, loading, error } = useAsyncData(() => teacherPortalService.dashboard(), [])
  const cards = data?.subjects ?? []

  const open = cards.filter((c) => c.can_upload)
  const closed = cards.filter((c) => !c.can_upload)

  if (loading && !data) return <PageLoader label="Loading your subjects" />

  return (
    <div>
      <PageHeader
        title="Upload Results"
        description="Choose a subject to enter marks by hand or import a CSV."
        actions={
          <Button as={Link} to="/teacher/downloads" variant="secondary" icon="download">
            Get a template
          </Button>
        }
      />

      {error && (
        <Alert tone="danger" title="Could not load your subjects" className="mb-5">
          {error}
        </Alert>
      )}

      {data?.overdue_subjects > 0 && (
        <Alert tone="danger" title="Marks are past due" className="mb-5">
          {data.overdue_subjects === 1
            ? 'One of your subjects is past its submission deadline.'
            : `${data.overdue_subjects} of your subjects are past their submission deadline.`}{' '}
          Upload the outstanding marks as soon as you can.
        </Alert>
      )}

      {cards.length === 0 ? (
        <Card>
          <CardBody className="p-0">
            <EmptyState
              icon="cloud-arrow-up"
              title={
                data?.current_examination
                  ? 'No subjects assigned to you'
                  : 'No examination is open'
              }
              description={
                data?.current_examination
                  ? 'The school office assigns subjects to teachers. Contact them if this looks wrong.'
                  : 'Once the school opens an examination for submission, your subjects will appear here.'
              }
            />
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-6">
          {open.length > 0 && (
            <section>
              <h2 className="text-ink-500 mb-3 text-xs font-semibold tracking-wider uppercase">
                Open for marks
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {open.map((card) => (
                  <SubjectChoice key={`${card.examination_id}-${card.subject_id}`} card={card} />
                ))}
              </div>
            </section>
          )}

          {closed.length > 0 && (
            <section>
              <h2 className="text-ink-500 mb-3 text-xs font-semibold tracking-wider uppercase">
                Closed
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {closed.map((card) => (
                  <SubjectChoice
                    key={`${card.examination_id}-${card.subject_id}`}
                    card={card}
                    disabled
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}

/** One subject, as a large target that says what state it is in. */
function SubjectChoice({ card, disabled = false }) {
  const complete = card.expected_count > 0 && card.submitted_count >= card.expected_count
  const pct = card.expected_count
    ? Math.round((card.submitted_count / card.expected_count) * 100)
    : 0

  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-ink-900 truncate font-semibold">{card.subject_name}</p>
          <p className="text-ink-400 font-mono text-xs">{card.subject_code}</p>
        </div>
        <Badge status={card.status}>{statusLabel(card.status)}</Badge>
      </div>

      <p className="text-ink-500 mt-3 truncate text-sm">{card.examination_name}</p>

      <div className="mt-4">
        <div className="text-ink-600 mb-1.5 flex items-baseline justify-between text-sm">
          <span className="tabular-nums">
            {card.submitted_count} of {card.expected_count} marked
          </span>
          <span className="tabular-nums">{pct}%</span>
        </div>
        <div className="bg-ink-100 h-1.5 w-full overflow-hidden rounded-full">
          <div
            className={cx(
              'h-full rounded-full transition-all',
              complete ? 'bg-success-500' : card.is_past_deadline ? 'bg-danger-500' : 'bg-brand-500',
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="text-ink-500 mt-4 flex items-center gap-2 text-xs">
        {disabled ? (
          <>
            <FontAwesomeIcon icon="lock" aria-hidden="true" />
            <span className="truncate">{card.locked_reason ?? 'Closed for changes'}</span>
          </>
        ) : card.submission_deadline ? (
          <>
            <FontAwesomeIcon
              icon={card.is_past_deadline ? 'triangle-exclamation' : 'clock'}
              className={card.is_past_deadline ? 'text-danger-500' : undefined}
              aria-hidden="true"
            />
            <span className={card.is_past_deadline ? 'text-danger-600 font-medium' : undefined}>
              {card.is_past_deadline
                ? `Overdue since ${formatDate(card.submission_deadline)}`
                : `Due ${formatDate(card.submission_deadline)}`}
            </span>
          </>
        ) : (
          <>
            <FontAwesomeIcon icon="clock" aria-hidden="true" />
            <span>No deadline set</span>
          </>
        )}
      </div>
    </>
  )

  if (disabled) {
    return (
      <div className="surface border-ink-200 bg-ink-50/60 p-5 opacity-75">{body}</div>
    )
  }

  return (
    <Link
      to={`/teacher/examinations/${card.examination_id}/subjects/${card.subject_id}`}
      className={cx(
        'surface hover:border-brand-300 hover:shadow-raised block p-5 transition-all',
        'focus-visible:border-brand-400',
      )}
    >
      {body}
      <span className="text-brand-700 mt-4 inline-flex items-center gap-2 text-sm font-semibold">
        Enter marks
        <FontAwesomeIcon icon="arrow-right" aria-hidden="true" />
      </span>
    </Link>
  )
}

export default UploadResultsPage
