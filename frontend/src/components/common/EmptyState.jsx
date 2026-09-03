import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

/** Placeholder for sections whose features arrive in a later stage. */
export function EmptyState({ icon = 'file-lines', title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <span className="bg-ink-100 text-ink-400 mb-4 flex size-12 items-center justify-center rounded-full">
        <FontAwesomeIcon icon={icon} className="text-lg" aria-hidden="true" />
      </span>
      <p className="text-ink-800 font-semibold">{title}</p>
      {description && <p className="text-ink-500 mt-1 max-w-sm text-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export default EmptyState
