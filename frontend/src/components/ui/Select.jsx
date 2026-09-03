import { useId } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/**
 * Labelled native select, styled to match Input.
 *
 * Native on purpose: on a phone this opens the platform picker, which is far
 * easier to use one-handed than any custom listbox. The default arrow is
 * removed so the control matches Input, and replaced with our own so it still
 * reads as a dropdown.
 */
export function Select({
  label,
  options = [],
  placeholder,
  error,
  hint,
  className,
  id: providedId,
  disabled,
  ...props
}) {
  const generatedId = useId()
  const id = providedId || generatedId
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined

  return (
    <div className={cx('w-full', className)}>
      {label && (
        <label htmlFor={id} className="text-ink-700 mb-1.5 block text-sm font-medium">
          {label}
        </label>
      )}

      <div className="relative">
        <select
          id={id}
          disabled={disabled}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedBy}
          className={cx(
            'w-full appearance-none rounded-lg border bg-white py-2.5 pr-10 pl-3.5 text-sm transition-colors',
            'text-ink-900 disabled:bg-ink-100 disabled:text-ink-400 disabled:cursor-not-allowed',
            error
              ? 'border-danger-500 focus:border-danger-500'
              : 'border-ink-300 focus:border-brand-500',
          )}
          {...props}
        >
          {placeholder && <option value="">{placeholder}</option>}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <FontAwesomeIcon
          icon="chevron-down"
          className={cx(
            'pointer-events-none absolute top-1/2 right-3.5 -translate-y-1/2 text-xs',
            disabled ? 'text-ink-300' : 'text-ink-400',
          )}
          aria-hidden="true"
        />
      </div>

      {error && (
        <p id={`${id}-error`} className="text-danger-600 mt-1.5 text-sm">
          {error}
        </p>
      )}
      {!error && hint && (
        <p id={`${id}-hint`} className="text-ink-500 mt-1.5 text-sm">
          {hint}
        </p>
      )}
    </div>
  )
}

export default Select
