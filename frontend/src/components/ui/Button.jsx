import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

const VARIANTS = {
  primary:
    'bg-brand-900 text-white hover:bg-brand-800 active:bg-brand-950 shadow-card disabled:bg-brand-900/50',
  secondary:
    'bg-white text-ink-700 border border-ink-300 hover:bg-ink-50 active:bg-ink-100 shadow-card disabled:text-ink-400',
  accent:
    'bg-accent-400 text-brand-950 hover:bg-accent-300 active:bg-accent-500 shadow-card disabled:bg-accent-200',
  danger: 'bg-danger-600 text-white hover:bg-danger-700 active:bg-danger-700 shadow-card',
  ghost: 'text-ink-600 hover:bg-ink-100 hover:text-ink-900 active:bg-ink-200',
}

const SIZES = {
  sm: 'px-3 py-1.5 text-sm gap-1.5 rounded-lg',
  md: 'px-4 py-2.5 text-sm gap-2 rounded-lg',
  lg: 'px-6 py-3 text-base gap-2.5 rounded-xl',
}

/** The single button primitive used across the portal. */
export function Button({
  as: Component = 'button',
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  loading = false,
  fullWidth = false,
  disabled = false,
  className,
  children,
  ...props
}) {
  const isDisabled = disabled || loading

  return (
    <Component
      className={cx(
        'inline-flex items-center justify-center font-semibold transition-colors duration-150',
        'disabled:cursor-not-allowed',
        VARIANTS[variant],
        SIZES[size],
        fullWidth && 'w-full',
        className,
      )}
      disabled={Component === 'button' ? isDisabled : undefined}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? (
        <FontAwesomeIcon icon="spinner" className="animate-spin" aria-hidden="true" />
      ) : (
        icon && iconPosition === 'left' && <FontAwesomeIcon icon={icon} aria-hidden="true" />
      )}
      {children}
      {!loading && icon && iconPosition === 'right' && (
        <FontAwesomeIcon icon={icon} aria-hidden="true" />
      )}
    </Component>
  )
}

export default Button
