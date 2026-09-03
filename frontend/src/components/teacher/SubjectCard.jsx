import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import { Badge, Button } from '@/components/ui'
import { teacherDownloads } from '@/services/teacherService'
import { getErrorMessage } from '@/services/apiClient'
import { statusLabel } from '@/utils/constants'
import { cx, formatDateTime } from '@/utils/format'

/** How the deadline reads, and how loudly. */
function deadlineTone(card) {
  if (card.status === 'SUBMITTED') return { tone: 'text-ink-500', icon: 'clock' }
  if (card.status === 'LATE') return { tone: 'text-warning-700', icon: 'triangle-exclamation' }
  if (card.is_past_deadline) return { tone: 'text-danger-600', icon: 'triangle-exclamation' }
  if (card.days_remaining !== null && card.days_remaining <= 3) {
    return { tone: 'text-warning-700', icon: 'clock' }
  }
  return { tone: 'text-ink-500', icon: 'clock' }
}

/**
 * One assigned subject: what is due, when, and where it stands.
 *
 * This is the teacher's whole job in one card, so the two actions that matter -
 * get the template, put the marks in - are the prominent ones.
 */
export function SubjectCard({ card, onDownloadError }) {
  const [busy, setBusy] = useState(null)

  const isDone = card.status === 'SUBMITTED' || card.status === 'LATE'
  const { tone, icon } = deadlineTone(card)
  const progress = card.expected_count
    ? Math.round((card.submitted_count / card.expected_count) * 100)
    : 0

  async function run(key, action) {
    setBusy(key)
    try {
      await action()
    } catch (err) {
      onDownloadError?.(getErrorMessage(err, 'That download did not work.'))
    } finally {
      setBusy(null)
    }
  }

  return (
    <article className="surface flex flex-col overflow-hidden">
      <div className="border-ink-200 flex items-start justify-between gap-3 border-b px-5 py-4">
        <div className="min-w-0">
          <h3 className="font-serif text-lg font-semibold">{card.subject_name}</h3>
          <p className="text-ink-500 mt-0.5 text-sm">
            {card.term_name} — {card.examination_name}
          </p>
        </div>
        <span className="bg-ink-100 text-ink-600 shrink-0 rounded px-2 py-1 font-mono text-xs font-semibold">
          {card.subject_code}
        </span>
      </div>

      <div className="flex-1 px-5 py-4">
        <dl className="space-y-3">
          <div>
            <dt className="text-ink-400 text-xs font-semibold tracking-wide uppercase">
              Deadline
            </dt>
            <dd className={cx('mt-1 flex items-center gap-2 text-sm font-medium', tone)}>
              <FontAwesomeIcon icon={icon} aria-hidden="true" />
              {card.submission_deadline ? (
                <>
                  {formatDateTime(card.submission_deadline)}
                  {!isDone && card.is_past_deadline && ' · passed'}
                  {!isDone &&
                    !card.is_past_deadline &&
                    card.days_remaining !== null &&
                    ` · ${card.days_remaining} day${card.days_remaining === 1 ? '' : 's'} left`}
                </>
              ) : (
                'No deadline set'
              )}
            </dd>
          </div>

          <div>
            <dt className="text-ink-400 text-xs font-semibold tracking-wide uppercase">
              Status
            </dt>
            <dd className="mt-1.5">
              {isDone ? (
                <div>
                  <p className="text-success-700 flex items-center gap-2 text-sm font-semibold">
                    <FontAwesomeIcon icon="circle-check" aria-hidden="true" />
                    Results submitted
                  </p>
                  {card.submitted_at && (
                    <p className="text-ink-500 mt-1 text-sm">
                      Submitted {formatDateTime(card.submitted_at)}
                      {card.submitted_by ? ` by ${card.submitted_by}` : ''}
                    </p>
                  )}
                  {card.status === 'LATE' && (
                    <p className="text-warning-700 mt-1 text-xs">Received after the deadline.</p>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Badge status={card.status}>
                    {card.status === 'PENDING' ? 'Not submitted' : statusLabel(card.status)}
                  </Badge>
                  {card.status === 'OVERDUE' && (
                    <span className="text-danger-600 text-xs font-semibold">
                      Marks are past due
                    </span>
                  )}
                </div>
              )}
            </dd>
          </div>
        </dl>

        {card.expected_count > 0 && (
          <div className="mt-4">
            <div className="text-ink-500 mb-1.5 flex justify-between text-xs">
              <span>
                {card.submitted_count} of {card.expected_count} students marked
              </span>
              <span>{progress}%</span>
            </div>
            <div className="bg-ink-100 h-1.5 w-full overflow-hidden rounded-full">
              <div
                className={cx(
                  'h-full rounded-full transition-all duration-500',
                  isDone ? 'bg-success-600' : progress > 0 ? 'bg-brand-600' : 'bg-ink-300',
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {!card.can_upload && card.locked_reason && (
          <p className="text-ink-500 bg-ink-50 mt-4 rounded-lg px-3 py-2 text-xs">
            {card.locked_reason}
          </p>
        )}
      </div>

      <div className="border-ink-200 bg-ink-50 flex flex-wrap gap-2 border-t px-5 py-3">
        <Button
          variant="secondary"
          size="sm"
          icon="download"
          loading={busy === 'template'}
          onClick={() =>
            run('template', () =>
              teacherDownloads.template(card.examination_id, card.subject_id, card.subject_code),
            )
          }
        >
          CSV template
        </Button>

        <Button
          as={Link}
          to={`/teacher/examinations/${card.examination_id}/subjects/${card.subject_id}`}
          size="sm"
          icon={card.can_upload ? 'cloud-arrow-up' : 'eye'}
        >
          {card.can_upload ? (isDone ? 'Manage results' : 'Upload results') : 'View results'}
        </Button>

        {card.submitted_count > 0 && (
          <>
            <Button
              variant="ghost"
              size="sm"
              icon="file-csv"
              loading={busy === 'csv'}
              onClick={() =>
                run('csv', () =>
                  teacherDownloads.csv(card.examination_id, card.subject_id, card.subject_code),
                )
              }
            >
              CSV
            </Button>
            <Button
              variant="ghost"
              size="sm"
              icon="file-pdf"
              loading={busy === 'pdf'}
              onClick={() =>
                run('pdf', () =>
                  teacherDownloads.pdf(card.examination_id, card.subject_id, card.subject_code),
                )
              }
            >
              PDF
            </Button>
          </>
        )}
      </div>
    </article>
  )
}

export default SubjectCard
