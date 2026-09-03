import { useId, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/**
 * Labelled text field with optional leading icon, error state and a
 * show/hide toggle for passwords.
 */
export function Input({
  label,
  type = 'text',
  icon,
  error,
  hint,
  className,
  id: providedId,
  ...props
}) {
  const generatedId = useId()
  const id = providedId || generatedId
  const [revealed, setRevealed] = useState(false)

  const isPassword = type === 'password'
  const inputType = isPassword && revealed ? 'text' : type
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined

  return (
    <div className={cx('w-full', className)}>
      {label && (
        <label htmlFor={id} className="text-ink-700 mb-1.5 block text-sm font-medium">
          {label}
        </label>
      )}

      <div className="relative">
        {icon && (
          <FontAwesomeIcon
            icon={icon}
            className="text-ink-400 pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sm"
            aria-hidden="true"
          />
        )}

        <input
          id={id}
          type={inputType}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedBy}
          className={cx(
            'w-full rounded-lg border bg-white py-2.5 text-sm transition-colors',
            'placeholder:text-ink-400 text-ink-900',
            'disabled:bg-ink-100 disabled:text-ink-400 disabled:cursor-not-allowed',
            icon ? 'pl-10' : 'pl-3.5',
            isPassword ? 'pr-11' : 'pr-3.5',
            error
              ? 'border-danger-500 focus:border-danger-500'
              : 'border-ink-300 focus:border-brand-500',
          )}
          {...props}
        />

        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealed((value) => !value)}
            className="text-ink-400 hover:text-ink-700 absolute top-1/2 right-3 -translate-y-1/2 rounded p-1 transition-colors"
            aria-label={revealed ? 'Hide password' : 'Show password'}
          >
            <FontAwesomeIcon icon={revealed ? 'eye-slash' : 'eye'} />
          </button>
        )}
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

export default Input
