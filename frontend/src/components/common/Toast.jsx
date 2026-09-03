import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

const TONES = {
  success: { wrap: 'bg-success-600 text-white', icon: 'circle-check' },
  danger: { wrap: 'bg-danger-600 text-white', icon: 'circle-exclamation' },
  info: { wrap: 'bg-brand-900 text-white', icon: 'circle-info' },
}

/**
 * Transient confirmation after an admin action.
 *
 * aria-live so the change is announced to a screen reader, since the visual
 * feedback sits away from wherever the user was working.
 */
export function Toast({ toast, onDismiss }) {
  if (!toast) return null
  const { wrap, icon } = TONES[toast.tone] ?? TONES.info

  return (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-6"
      role="status"
      aria-live="polite"
    >
      <div
        className={cx(
          'shadow-overlay pointer-events-auto flex max-w-lg items-start gap-3 rounded-xl px-4 py-3 text-sm',
          wrap,
        )}
      >
        <FontAwesomeIcon icon={icon} className="mt-0.5 shrink-0" aria-hidden="true" />
        <p className="min-w-0 flex-1">{toast.message}</p>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="shrink-0 rounded p-0.5 opacity-70 transition-opacity hover:opacity-100"
        >
          <FontAwesomeIcon icon="xmark" />
        </button>
      </div>
    </div>
  )
}

export default Toast
