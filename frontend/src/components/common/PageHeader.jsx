import { cx } from '@/utils/format'

export function PageHeader({ title, description, actions, className }) {
  return <div className={cx('mb-7 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between', className)}>
    <div className="min-w-0">
      <h1 className="font-serif text-[30px] leading-tight font-medium tracking-[-0.025em] sm:text-[34px]">{title}</h1>
      {description && <p className="mt-2 max-w-[68ch] text-sm leading-relaxed text-ink-500">{description}</p>}
    </div>
    {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
  </div>
}
export default PageHeader
