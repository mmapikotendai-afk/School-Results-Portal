import { cx } from '@/utils/format'
import { statusLabel } from '@/utils/constants'

const TONES = {
  neutral: 'bg-ink-100 text-ink-700 ring-ink-200',
  brand: 'bg-brand-50 text-brand-700 ring-brand-200',
  success: 'bg-success-50 text-success-700 ring-success-100',
  warning: 'bg-warning-50 text-warning-700 ring-warning-100',
  danger: 'bg-danger-50 text-danger-700 ring-danger-100',
}

/**
 * Maps every backend status value onto one colour, so an examination, a
 * submission and an enrollment all read consistently across the portal.
 */
const STATUS_TONES = {
  // Examination lifecycle
  DRAFT: 'neutral',
  SUBMISSION_OPEN: 'brand',
  SUBMISSION_COMPLETE: 'brand',
  UNDER_REVIEW: 'warning',
  PUBLISHED: 'success',
  // Submission tracking. OVERDUE is the one that needs chasing, so it takes
  // the strongest colour; LATE did arrive, so it is only a warning.
  PENDING: 'neutral',
  PARTIAL: 'brand',
  OVERDUE: 'danger',
  SUBMITTED: 'success',
  LATE: 'warning',
  // Subject enrollment
  ACTIVE: 'success',
  INACTIVE: 'neutral',
  // Education level
  O_LEVEL: 'brand',
  A_LEVEL: 'brand',
}

export function Badge({ tone = 'neutral', status, className, children }) {
  const resolved = status ? (STATUS_TONES[status] ?? 'neutral') : tone

  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset',
        TONES[resolved],
        className,
      )}
    >
      {children ?? statusLabel(status)}
    </span>
  )
}

export default Badge
