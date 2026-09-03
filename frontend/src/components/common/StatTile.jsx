import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

/** Compact metric tile used across the three role dashboards. */
export function StatTile({ icon, label, value, hint }) {
  return (
    <div className="surface p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-ink-500 text-sm font-medium">{label}</p>
        <span className="bg-brand-50 text-brand-700 flex size-9 shrink-0 items-center justify-center rounded-lg">
          <FontAwesomeIcon icon={icon} className="text-sm" aria-hidden="true" />
        </span>
      </div>
      <p className="text-ink-900 mt-3 text-3xl font-semibold tracking-tight">{value}</p>
      {hint && <p className="text-ink-400 mt-1 text-xs">{hint}</p>}
    </div>
  )
}

export default StatTile
