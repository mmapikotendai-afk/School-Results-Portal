import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import useApiHealth from '@/hooks/useApiHealth'
import { cx } from '@/utils/format'

/**
 * Live indicator of the frontend -> backend connection.
 *
 * This is the visible proof that React reached FastAPI: it shows whether the
 * API answered and, separately, whether MySQL is reachable behind it.
 */
export function ApiStatusBadge({ className, showDetail = true }) {
  const { health, error, loading, refresh } = useApiHealth({ pollMs: 30000 })

  const state = loading && !health && !error
    ? { tone: 'neutral', dot: 'bg-ink-400 animate-pulse', label: 'Checking API…' }
    : error
      ? { tone: 'danger', dot: 'bg-danger-500', label: 'API unreachable' }
      : health?.database === 'connected'
        ? { tone: 'success', dot: 'bg-success-500', label: 'API connected' }
        : { tone: 'warning', dot: 'bg-warning-500', label: 'API up · database offline' }

  const TONES = {
    neutral: 'bg-ink-100 text-ink-600 ring-ink-200',
    success: 'bg-success-50 text-success-700 ring-success-100',
    warning: 'bg-warning-50 text-warning-700 ring-warning-100',
    danger: 'bg-danger-50 text-danger-700 ring-danger-100',
  }

  return (
    <div className={cx('flex flex-wrap items-center gap-2', className)}>
      <span
        className={cx(
          'inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset',
          TONES[state.tone],
        )}
      >
        <span className={cx('size-1.5 rounded-full', state.dot)} aria-hidden="true" />
        {state.label}
      </span>

      {showDetail && health && (
        <span className="text-ink-500 text-xs">
          {health.service} v{health.version} · {health.environment}
        </span>
      )}

      <button
        type="button"
        onClick={refresh}
        className="text-ink-400 hover:text-ink-700 rounded p-1 text-xs transition-colors"
        aria-label="Re-check API connection"
      >
        <FontAwesomeIcon icon="rotate" className={cx(loading && 'animate-spin')} />
      </button>
    </div>
  )
}

export default ApiStatusBadge
