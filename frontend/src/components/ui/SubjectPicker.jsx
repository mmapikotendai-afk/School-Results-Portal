import { useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

/**
 * Multi-select for subject enrollment and teacher assignment.
 *
 * Rendered as a checkbox list rather than a multi-select, because the point of
 * the screen is to see at a glance which subjects are ticked and which are not:
 *
 *   Tendai Mapiko - Form 4A
 *     [x] Mathematics   [x] English   [x] Geography
 *     [x] Science       [ ] Accounts
 */
export function SubjectPicker({
  subjects = [],
  selectedIds = [],
  onChange,
  disabled = false,
  emptyMessage = 'No subjects have been created yet.',
}) {
  const [filter, setFilter] = useState('')
  const selected = useMemo(() => new Set(selectedIds), [selectedIds])

  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    if (!needle) return subjects
    return subjects.filter(
      (s) =>
        s.name.toLowerCase().includes(needle) || s.code.toLowerCase().includes(needle),
    )
  }, [subjects, filter])

  function toggle(id) {
    if (disabled) return
    const next = new Set(selected)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    onChange?.([...next])
  }

  if (subjects.length === 0) {
    return (
      <p className="text-ink-500 border-ink-200 rounded-lg border border-dashed px-4 py-6 text-center text-sm">
        {emptyMessage}
      </p>
    )
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-ink-600 text-sm">
          <span className="text-ink-900 font-semibold">{selected.size}</span> selected
        </p>
        <div className="flex items-center gap-2">
          {subjects.length > 6 && (
            <input
              type="search"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              placeholder="Filter subjects"
              className="border-ink-300 focus:border-brand-500 w-40 rounded-lg border px-3 py-1.5 text-sm"
            />
          )}
          <button
            type="button"
            onClick={() => onChange?.(selected.size === subjects.length ? [] : subjects.map((s) => s.id))}
            disabled={disabled}
            className="text-brand-700 hover:bg-brand-50 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {selected.size === subjects.length ? 'Clear all' : 'Select all'}
          </button>
        </div>
      </div>

      <div className="border-ink-200 max-h-64 overflow-y-auto rounded-lg border">
        <ul className="divide-ink-100 divide-y">
          {visible.map((subject) => {
            const isSelected = selected.has(subject.id)
            return (
              <li key={subject.id}>
                <label
                  className={cx(
                    'flex cursor-pointer items-center gap-3 px-3.5 py-2.5 transition-colors',
                    disabled ? 'cursor-not-allowed opacity-60' : 'hover:bg-ink-50',
                  )}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggle(subject.id)}
                    disabled={disabled}
                    className="sr-only"
                  />
                  <span
                    aria-hidden="true"
                    className={cx(
                      'flex size-5 shrink-0 items-center justify-center rounded border transition-colors',
                      isSelected
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-ink-300 bg-white',
                    )}
                  >
                    {isSelected && <FontAwesomeIcon icon="check" className="text-[10px]" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="text-ink-900 text-sm font-medium">{subject.name}</span>
                    <span className="text-ink-400 ml-2 text-xs">{subject.code}</span>
                  </span>
                  {subject.level && subject.level !== 'BOTH' && (
                    <span className="bg-ink-100 text-ink-600 rounded px-1.5 py-0.5 text-[10px] font-semibold">
                      {subject.level === 'O_LEVEL' ? 'O' : 'A'}
                    </span>
                  )}
                </label>
              </li>
            )
          })}
          {visible.length === 0 && (
            <li className="text-ink-500 px-3.5 py-6 text-center text-sm">
              No subjects match {filter}.
            </li>
          )}
        </ul>
      </div>
    </div>
  )
}

export default SubjectPicker
