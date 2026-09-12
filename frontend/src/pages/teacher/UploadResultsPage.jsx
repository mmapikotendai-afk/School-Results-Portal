import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import UploadDialog from '@/components/teacher/UploadDialog'
import { Alert, Badge, Button, Card, CardBody, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { teacherPortalService } from '@/services/teacherService'
import { statusLabel } from '@/utils/constants'
import { cx, formatDate } from '@/utils/format'

/**
 * Choose a subject to record marks for.
 *
 * Only subjects assigned to this teacher appear, and a subject that cannot
 * currently accept marks says why rather than failing at the next step. The
 * server enforces both rules again, so nothing here is load-bearing.
 *
 * Each open subject offers both ways in from the card itself: the mark sheet
 * for typing marks, and the CSV import for a whole class at once. Reaching the
 * import only through the mark sheet was a dead end - the page named after the
 * task did not perform the task.
 */
export function UploadResultsPage() {
  useDocumentTitle('Upload Results')

  const { data, loading, error, refresh } = useAsyncData(
    () => teacherPortalService.dashboard(),
    [],
  )
  // The subject whose import dialog is open, or null. Holding the card rather
  // than a boolean lets one dialog serve every card on the page.
  const [uploadFor, setUploadFor] = useState(null)
  const { toast, show, clear } = useToast()

  const cards = data?.subjects ?? []

  const open = cards.filter((c) => c.can_upload)
  const closed = cards.filter((c) => !c.can_upload)

  if (loading && !data) return <PageLoader label="Loading your subjects" />

  return (
    <div>
      <PageHeader
        title="Upload Results"
        description="Import a filled-in CSV, or open a subject to type marks by hand."
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
                  <SubjectChoice
                    key={`${card.examination_id}-${card.subject_id}`}
                    card={card}
                    onUpload={() => setUploadFor(card)}
                  />
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

      {uploadFor && (
        <UploadDialog
          open
          sheet={uploadFor}
          onClose={() => setUploadFor(null)}
          onUploaded={(result) => {
            setUploadFor(null)
            // The card carries a progress bar, so it has to be re-read before
            // the teacher can see that their upload landed.
            refresh()
            show(result.detail)
          }}
        />
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

/** One subject, as a card that states where it stands and offers both ways in. */
function SubjectChoice({ card, disabled = false, onUpload }) {
  const complete = card.expected_count > 0 && card.submitted_count >= card.expected_count
  const pct = card.expected_count
    ? Math.round((card.submitted_count / card.expected_count) * 100)
    : 0

  const marksheet = `/teacher/examinations/${card.examination_id}/subjects/${card.subject_id}`

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
    return <div className="surface border-ink-200 bg-ink-50/60 p-5 opacity-75">{body}</div>
  }

  return (
    <div className="surface hover:border-brand-300 hover:shadow-raised flex flex-col p-5 transition-all">
      {/* The body grows so the actions sit on a common baseline across the
          row, however uneven the subject names and deadlines are. */}
      <div className="flex-1">{body}</div>

      <div className="border-ink-200 mt-4 flex gap-2 border-t pt-4">
        <Button
          as={Link}
          to={marksheet}
          variant="secondary"
          size="sm"
          icon="pen-to-square"
          className="flex-1"
        >
          Enter marks
        </Button>
        <Button size="sm" icon="cloud-arrow-up" className="flex-1" onClick={onUpload}>
          Upload CSV
        </Button>
      </div>
    </div>
  )
}

export default UploadResultsPage
