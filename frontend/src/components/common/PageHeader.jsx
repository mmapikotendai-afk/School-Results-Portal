import { cx } from '@/utils/format'

/**
 * Consistent page title block for every screen inside the portal.
 *
 * The title carries real size now. At the old text-xl it sat only about
 * 2.1x the body text, which is under the threshold where a heading reads as
 * a heading rather than as bold copy; at 32-36px it is unambiguously the
 * first thing on the page. An optional `eyebrow` carries the section it
 * belongs to, in the letterspaced micro-label used throughout the system.
 */
export function PageHeader({ title, description, eyebrow, actions, className }) {
  return (
    <div
      className={cx(
        'border-ink-200 mb-8 flex flex-col gap-4 border-b pb-6',
        'sm:flex-row sm:items-end sm:justify-between',
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow && <p className="rule-label mb-2">{eyebrow}</p>}
        <h1 className="text-[28px] leading-none font-bold tracking-tight sm:text-[36px]">
          {title}
        </h1>
        {description && (
          <p className="text-ink-500 mt-3 max-w-[62ch] text-sm">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export default PageHeader
