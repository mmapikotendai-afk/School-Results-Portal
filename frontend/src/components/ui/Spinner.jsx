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
    <div className="min-h-[45vh]" role="status" aria-busy="true" aria-label={label}>
      <span className="sr-only">{label}?</span>
      <div className="mb-7 space-y-3" aria-hidden="true"><div className="h-8 w-52 max-w-full animate-pulse rounded bg-ink-200" /><div className="h-3 w-80 max-w-full animate-pulse rounded bg-ink-100" /></div>
      <div className="surface divide-y divide-ink-200" aria-hidden="true">{[0,1,2,3,4].map(i => <div key={i} className="flex gap-6 px-5 py-6"><div className="h-4 flex-1 animate-pulse rounded bg-ink-100" /><div className="h-4 w-16 animate-pulse rounded bg-ink-100" /><div className="hidden h-4 w-24 animate-pulse rounded bg-ink-100 sm:block" /></div>)}</div>
    </div>
  )
}

export default Spinner
