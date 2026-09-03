import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/**
 * Table used across the portal.
 *
 * Columns declare their own cell renderer, so each screen describes what it
 * shows rather than repeating table markup.
 *
 * Two presentations, one column definition. On a laptop it is a table. Below
 * `md` a table would either overflow the screen or squeeze columns until the
 * text wraps one letter at a time, so each row becomes a stacked card with the
 * column headers as labels. Nothing is dropped between the two - a phone shows
 * the same fields as a desktop, in a shape that fits.
 *
 * Column options:
 *   header        column heading, and the field label on mobile
 *   render(row)   cell content; falls back to row[key]
 *   align         'right' to right-align in the table
 *   primary       show as the card's heading on mobile (defaults to column 1)
 *   hideOnMobile  omit from the card, for detail that only earns its space wide
 */
export function DataTable({
  columns,
  rows,
  rowKey = (row) => row.id,
  loading = false,
  empty,
  onRowClick,
}) {
  if (loading) {
    return <TableSkeleton columns={columns.length} />
  }

  if (!rows.length) {
    return <div className="py-4">{empty}</div>
  }

  const primaryIndex = Math.max(
    0,
    columns.findIndex((c) => c.primary),
  )
  // A column with no heading is an action cluster: it gets no label on mobile.
  const isActions = (column) => !column.header

  return (
    <>
      {/* Wide: a real table. */}
      <div className="hidden overflow-x-auto md:block">
        {/* A floor on the width so a wide table scrolls inside its own card
            rather than squeezing columns down to one word per line. */}
        <table className="w-full min-w-[38rem] border-collapse text-sm">
          <thead>
            <tr className="border-ink-200 border-b">
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={cx(
                    'text-ink-500 px-5 py-3 text-left text-xs font-semibold tracking-wide uppercase',
                    column.align === 'right' && 'text-right',
                    column.className,
                  )}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cx(
                  'transition-colors',
                  onRowClick ? 'hover:bg-ink-50 cursor-pointer' : 'hover:bg-ink-50/60',
                )}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cx(
                      'px-5 py-3 align-middle',
                      column.align === 'right' && 'text-right',
                      column.cellClassName,
                    )}
                  >
                    {column.render ? column.render(row) : row[column.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Narrow: one card per row, labelled. */}
      <ul className="divide-ink-100 divide-y md:hidden">
        {rows.map((row) => {
          const primary = columns[primaryIndex]
          const rest = columns.filter(
            (c, i) => i !== primaryIndex && !c.hideOnMobile && !isActions(c),
          )
          const actions = columns.filter(isActions)

          return (
            <li
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cx('px-4 py-4', onRowClick && 'hover:bg-ink-50 cursor-pointer')}
            >
              <div className="text-sm font-medium">
                {primary.render ? primary.render(row) : row[primary.key]}
              </div>

              {rest.length > 0 && (
                <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
                  {rest.map((column) => (
                    <div key={column.key} className="min-w-0">
                      <dt className="text-ink-500 text-[11px] font-semibold tracking-wide uppercase">
                        {column.header}
                      </dt>
                      <dd className="text-ink-800 mt-0.5 text-sm">
                        {column.render ? column.render(row) : row[column.key]}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}

              {actions.length > 0 && (
                <div className="border-ink-100 mt-3 flex flex-wrap items-center gap-1 border-t pt-3">
                  {actions.map((column) => (
                    <div key={column.key} className="contents">
                      {column.render ? column.render(row) : row[column.key]}
                    </div>
                  ))}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </>
  )
}

/**
 * Loading placeholder shaped like the table it replaces.
 *
 * A skeleton rather than a spinner, so the page does not jump when the rows
 * arrive and the reader can see what is coming.
 */
function TableSkeleton({ columns = 4, rows = 5 }) {
  return (
    <div aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading…</span>

      <div className="hidden md:block">
        <div className="border-ink-200 flex gap-4 border-b px-5 py-3">
          {Array.from({ length: columns }).map((_, i) => (
            <div key={i} className="bg-ink-100 h-3 flex-1 animate-pulse rounded" />
          ))}
        </div>
        <div className="divide-ink-100 divide-y">
          {Array.from({ length: rows }).map((_, r) => (
            <div key={r} className="flex items-center gap-4 px-5 py-4">
              {Array.from({ length: columns }).map((_, i) => (
                <div
                  key={i}
                  className="bg-ink-100 h-4 flex-1 animate-pulse rounded"
                  style={{ animationDelay: `${r * 60}ms` }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="divide-ink-100 divide-y md:hidden">
        {Array.from({ length: 3 }).map((_, r) => (
          <div key={r} className="space-y-3 px-4 py-4">
            <div className="bg-ink-100 h-4 w-2/5 animate-pulse rounded" />
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-ink-100 h-3 animate-pulse rounded" />
              <div className="bg-ink-100 h-3 animate-pulse rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Row actions, kept visually quiet so the data stays the loudest thing. */
export function RowAction({ icon, label, onClick, tone = 'neutral' }) {
  const TONES = {
    neutral: 'text-ink-500 hover:bg-ink-100 hover:text-ink-900',
    brand: 'text-brand-600 hover:bg-brand-50 hover:text-brand-800',
    danger: 'text-danger-600 hover:bg-danger-50 hover:text-danger-700',
  }
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation()
        onClick()
      }}
      aria-label={label}
      title={label}
      className={cx('rounded-lg p-2 transition-colors', TONES[tone])}
    >
      <FontAwesomeIcon icon={icon} className="text-sm" aria-hidden="true" />
    </button>
  )
}

export { TableSkeleton }
export default DataTable
