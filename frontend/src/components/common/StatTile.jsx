import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/**
 * Compact metric tile used across the three role dashboards.
 *
 * The tinted icon chip that used to sit opposite the label has gone. A
 * figure set at 44px is already the loudest thing in the tile — an ornament
 * beside it competes for the eye without helping anyone find the number
 * faster. The icon stays, at label weight, as a quiet category marker.
 */
export function StatTile({ icon, label, value, hint, className }) {
  return (
    <div className={cx('surface p-6', className)}>
      <div className="flex items-center gap-2">
        {icon && (
          <FontAwesomeIcon icon={icon} className="text-ink-400 w-3 text-[11px]" aria-hidden="true" />
        )}
        <p className="rule-label">{label}</p>
      </div>

      <p className="text-ink-900 tabular mt-3 text-[44px] leading-none font-bold tracking-tight">
        {value}
      </p>

      {hint && <p className="text-ink-400 mt-2 text-xs">{hint}</p>}
    </div>
  )
}

export default StatTile
