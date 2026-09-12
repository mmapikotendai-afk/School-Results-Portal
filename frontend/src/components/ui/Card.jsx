import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/** Standard content surface: a rule and a white ground, nothing more. */
export function Card({ className, children, ...props }) {
  return (
    <div className={cx('surface', className)} {...props}>
      {children}
    </div>
  )
}

/**
 * The tinted rounded chip that used to sit behind the header icon is gone.
 * It was the Material-era "card with a coloured accent" pattern, and with a
 * heading beside it the icon was never doing the identifying work anyway.
 * The icon now sits in the ink of the heading, at the heading's weight.
 */
export function CardHeader({ title, description, icon, action, className }) {
  return (
    <div className={cx('border-ink-200 flex items-start gap-3 border-b px-5 py-4', className)}>
      {icon && (
        <FontAwesomeIcon
          icon={icon}
          className="text-brand-800 mt-1 w-4 shrink-0"
          aria-hidden="true"
        />
      )}
      <div className="min-w-0 flex-1">
        <h3 className="text-base font-semibold">{title}</h3>
        {description && <p className="text-ink-500 mt-0.5 text-sm">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function CardBody({ className, children }) {
  return <div className={cx('px-5 py-4', className)}>{children}</div>
}

export default Card
