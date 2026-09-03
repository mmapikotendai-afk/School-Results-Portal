import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/**
 * Submission progress as a single bar plus a three-way breakdown.
 *
 * The bar is stacked rather than one filled track: submitted, pending and
 * overdue are three different situations, and a single percentage hides which
 * of the remainder still has time and which does not.
 */
export function SubmissionProgress({ submitted, pending, overdue, total, progress }) {
  const pct = (n) => (total ? (n / total) * 100 : 0)

  const segments = [
    { key: 'submitted', value: submitted, className: 'bg-success-600' },
    { key: 'pending', value: pending - overdue, className: 'bg-warning-400' },
    { key: 'overdue', value: overdue, className: 'bg-danger-500' },
  ].filter((s) => s.value > 0)

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-ink-900 text-2xl font-semibold">
          {submitted} / {total}
          <span className="text-ink-500 ml-2 text-sm font-normal">subjects submitted</span>
        </p>
        <p
          className={cx(
            'text-2xl font-semibold tabular-nums',
            progress === 100 ? 'text-success-700' : overdue > 0 ? 'text-danger-600' : 'text-brand-700',
          )}
        >
          {progress}%
          <span className="text-ink-500 ml-1.5 text-sm font-normal">complete</span>
        </p>
      </div>

      <div
        className="bg-ink-100 flex h-3 w-full overflow-hidden rounded-full"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${submitted} of ${total} subjects submitted`}
      >
        {segments.map((s) => (
          <div
            key={s.key}
            className={cx('h-full transition-all duration-500', s.className)}
            style={{ width: `${pct(s.value)}%` }}
          />
        ))}
      </div>

      <div className="mt-5 grid grid-cols-3 gap-4">
        <Breakdown
          icon="circle-check"
          tone="success"
          label="Submitted"
          value={submitted}
        />
        <Breakdown
          icon="clock"
          tone="warning"
          label="Pending"
          value={Math.max(0, pending - overdue)}
        />
        <Breakdown
          icon="triangle-exclamation"
          tone="danger"
          label="Overdue"
          value={overdue}
        />
      </div>
    </div>
  )
}

function Breakdown({ icon, tone, label, value }) {
  const TONES = {
    success: 'bg-success-50 text-success-700',
    warning: 'bg-warning-50 text-warning-700',
    danger: 'bg-danger-50 text-danger-700',
  }
  return (
    <div className="flex items-center gap-3">
      <span
        className={cx(
          'flex size-9 shrink-0 items-center justify-center rounded-lg',
          value > 0 ? TONES[tone] : 'bg-ink-100 text-ink-300',
        )}
      >
        <FontAwesomeIcon icon={icon} className="text-sm" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className={cx('text-xl font-semibold', value > 0 ? 'text-ink-900' : 'text-ink-300')}>
          {value}
        </p>
        <p className="text-ink-500 text-xs">{label}</p>
      </div>
    </div>
  )
}

export default SubmissionProgress
