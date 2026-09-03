import { cx } from '@/utils/format'

/** Consistent page title block for every screen inside the portal. */
export function PageHeader({ title, description, actions, className }) {
  return (
    <div
      className={cx(
        'mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between',
        className,
      )}
    >
      <div className="min-w-0">
        <h1 className="text-xl font-semibold sm:text-2xl">{title}</h1>
        {description && <p className="text-ink-500 mt-1 text-sm">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export default PageHeader
