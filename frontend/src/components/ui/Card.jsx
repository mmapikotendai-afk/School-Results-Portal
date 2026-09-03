import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/** Standard content surface. */
export function Card({ className, children, ...props }) {
  return (
    <div className={cx('surface', className)} {...props}>
      {children}
    </div>
  )
}

export function CardHeader({ title, description, icon, action, className }) {
  return (
    <div
      className={cx('border-ink-200 flex items-start gap-4 border-b px-5 py-4', className)}
    >
      {icon && (
        <span className="bg-brand-50 text-brand-700 flex size-10 shrink-0 items-center justify-center rounded-lg">
          <FontAwesomeIcon icon={icon} aria-hidden="true" />
        </span>
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
