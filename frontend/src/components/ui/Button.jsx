import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/**
 * Buttons are cut, not moulded: square corners, a flat fill, and a drawn
 * border where the fill is white. No shadow — a control sits on the page
 * rather than hovering above it.
 *
 * `accent` is the crest vermilion and is deliberately scarce. It marks the
 * one institutional action on a screen (issuing or reissuing credentials),
 * never a routine save.
 */
const VARIANTS = {
  primary: 'bg-brand-900 text-white hover:bg-brand-800 active:bg-brand-950 disabled:bg-brand-900/40',
  secondary:
    'bg-white text-ink-900 border border-ink-900 hover:bg-ink-100 active:bg-ink-200 disabled:border-ink-300 disabled:text-ink-400',
  accent: 'bg-accent-500 text-white hover:bg-accent-600 active:bg-accent-700 disabled:bg-accent-200',
  danger: 'bg-danger-600 text-white hover:bg-danger-700 active:bg-danger-700 disabled:bg-danger-100',
  ghost: 'text-ink-700 hover:bg-ink-100 hover:text-ink-900 active:bg-ink-200',
}

const SIZES = {
  sm: 'px-3 py-1.5 text-[13px] gap-1.5',
  md: 'px-5 py-2.5 text-sm gap-2',
  lg: 'px-7 py-3.5 text-base gap-2.5',
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
        'inline-flex items-center justify-center font-semibold transition-colors duration-100',
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
