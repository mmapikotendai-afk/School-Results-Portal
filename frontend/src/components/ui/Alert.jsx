import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

const TONES = {
  info: { wrap: 'bg-brand-50 border-brand-200 text-brand-900', icon: 'circle-info' },
  success: {
    wrap: 'bg-success-50 border-success-100 text-success-700',
    icon: 'circle-check',
  },
  warning: {
    wrap: 'bg-warning-50 border-warning-100 text-warning-700',
    icon: 'triangle-exclamation',
  },
  danger: {
    wrap: 'bg-danger-50 border-danger-100 text-danger-700',
    icon: 'circle-exclamation',
  },
}

/** Inline feedback banner. `role="alert"` so screen readers announce errors. */
export function Alert({ tone = 'info', title, children, onDismiss, className }) {
  const { wrap, icon } = TONES[tone] ?? TONES.info

  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={cx('flex items-start gap-3 rounded-lg border px-4 py-3 text-sm', wrap, className)}
    >
      <FontAwesomeIcon icon={icon} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={cx(title && 'mt-0.5')}>{children}</div>}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded p-0.5 opacity-60 transition-opacity hover:opacity-100"
          aria-label="Dismiss"
        >
          <FontAwesomeIcon icon="xmark" />
        </button>
      )}
    </div>
  )
}

export default Alert
