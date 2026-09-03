import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/** Search box for the admin tables, with a clear button once it has content. */
export function SearchInput({ value, onChange, placeholder = 'Search', className }) {
  return (
    <div className={cx('relative', className)}>
      <FontAwesomeIcon
        icon="magnifying-glass"
        className="text-ink-400 pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm"
        aria-hidden="true"
      />
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="border-ink-300 focus:border-brand-500 placeholder:text-ink-400 w-full rounded-lg border bg-white py-2.5 pr-9 pl-10 text-sm transition-colors"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label="Clear search"
          className="text-ink-400 hover:text-ink-700 absolute top-1/2 right-2.5 -translate-y-1/2 rounded p-1 transition-colors"
        >
          <FontAwesomeIcon icon="xmark" className="text-xs" />
        </button>
      )}
    </div>
  )
}

export default SearchInput
