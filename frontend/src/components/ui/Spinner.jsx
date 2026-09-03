import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

const SIZES = { sm: 'text-sm', md: 'text-xl', lg: 'text-3xl' }

export function Spinner({ size = 'md', className, label = 'Loading' }) {
  return (
    <FontAwesomeIcon
      icon="spinner"
      className={cx('text-brand-600 animate-spin', SIZES[size], className)}
      role="status"
      aria-label={label}
    />
  )
}

/** Full-height centred loader for route-level suspense states. */
export function PageLoader({ label = 'Loading' }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3">
      <Spinner size="lg" label={label} />
      <p className="text-ink-500 text-sm">{label}…</p>
    </div>
  )
}

export default Spinner
