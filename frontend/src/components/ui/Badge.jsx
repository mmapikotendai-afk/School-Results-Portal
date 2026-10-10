import { cx } from '@/utils/format'
import { statusLabel } from '@/utils/constants'

const TONES = {
  neutral: 'bg-ink-100 text-ink-600',
  brand: 'bg-brand-50 text-brand-800',
  success: 'bg-success-50 text-success-700',
  warning: 'bg-warning-50 text-warning-700',
  danger: 'bg-danger-50 text-danger-700',
}

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
    <span className={cx('status-chip', TONES[resolved], className)}>
      {children ?? statusLabel(status)}
    </span>
  )
}

export default Badge
