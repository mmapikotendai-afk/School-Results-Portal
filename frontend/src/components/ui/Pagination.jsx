import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/** Page controls for the admin tables. Hidden when everything fits on one page. */
export function Pagination({ page, pageSize, total, onPageChange }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (total === 0) return null

  const first = (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, total)

  return (
    <div className="border-ink-200 flex flex-wrap items-center justify-between gap-3 border-t px-5 py-3">
      <p className="text-ink-500 text-sm">
        Showing <span className="text-ink-800 font-medium">{first}</span> to{' '}
        <span className="text-ink-800 font-medium">{last}</span> of{' '}
        <span className="text-ink-800 font-medium">{total}</span>
      </p>

      {pages > 1 && (
        <div className="flex items-center gap-1">
          <PageButton
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            label="Previous page"
            icon="arrow-right"
            flip
          />
          <span className="text-ink-600 px-3 text-sm font-medium">
            Page {page} of {pages}
          </span>
          <PageButton
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pages}
            label="Next page"
            icon="arrow-right"
          />
        </div>
      )}
    </div>
  )
}

function PageButton({ onClick, disabled, label, icon, flip }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className={cx(
        'border-ink-300 text-ink-600 rounded-lg border px-2.5 py-1.5 transition-colors',
        'hover:bg-ink-100 hover:text-ink-900 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent',
      )}
    >
      <FontAwesomeIcon icon={icon} className={cx('text-xs', flip && 'rotate-180')} />
    </button>
  )
}

export default Pagination
