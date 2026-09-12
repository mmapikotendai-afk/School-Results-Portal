import { cx } from '@/utils/format'
import { statusLabel } from '@/utils/constants'

/**
 * A status is letterspaced type sitting on a 2px rule, not a filled pill.
 *
 * Three reasons it is drawn this way. Report cards and marksheets get
 * printed, and a tinted pill either eats toner or vanishes; a rule survives
 * both. A screen listing forty submissions turns forty pills into confetti,
 * where forty short rules stay quiet. And the colour is carried by the text
 * itself, so the status is still readable in greyscale — the meaning never
 * depends on the colour alone.
 */
const TONES = {
  neutral: 'text-ink-400',
  brand: 'text-brand-800',
  success: 'text-success-600',
  warning: 'text-warning-600',
  danger: 'text-danger-600',
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
    <span className={cx('status-chip', TONES[resolved], className)}>
      {children ?? statusLabel(status)}
    </span>
  )
}

export default Badge
