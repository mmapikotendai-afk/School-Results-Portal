import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, Input } from '@/components/ui'

/**
 * Existing Result Detected.
 *
 * Shown when an upload would overwrite marks already on record. Each clash is
 * spelled out - who, what they have, what the file would give them - because
 * replacing a mark is not something anyone should do by accident, and the
 * difference between 80 and 85 is invisible in a row count.
 *
 * The reason typed here lands on the audit entry for every mark replaced.
 */
export function ReplaceConfirmation({ rows, reason, onReasonChange }) {
  const clashes = rows.filter((r) => r.is_overwrite)
  if (!clashes.length) return null

  return (
    <div className="mt-4">
      <Alert
        tone="warning"
        title={`Existing result${clashes.length === 1 ? '' : 's'} detected`}
      >
        {clashes.length === 1
          ? 'One student already has a mark for this subject and examination.'
          : `${clashes.length} students already have a mark for this subject and examination.`}{' '}
        Nothing is replaced unless you confirm it below. No duplicate row is ever
        created — the existing mark is updated, and the change is recorded against
        your name.
      </Alert>

      <div className="border-warning-200 mt-3 overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-warning-50">
            <tr>
              <th scope="col" className="text-warning-800 px-3 py-2 text-left text-xs font-semibold uppercase">
                Student
              </th>
              <th scope="col" className="text-warning-800 px-3 py-2 text-right text-xs font-semibold uppercase">
                Existing mark
              </th>
              <th scope="col" className="px-3 py-2" aria-hidden="true" />
              <th scope="col" className="text-warning-800 px-3 py-2 text-right text-xs font-semibold uppercase">
                New mark
              </th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {clashes.map((row) => {
              const before = Number(row.existing_marks)
              const after = Number(row.marks)
              return (
                <tr key={row.row}>
                  <td className="px-3 py-2">
                    <p className="text-ink-900 font-medium">{row.student_name}</p>
                    <p className="text-ink-400 font-mono text-xs">{row.student_number}</p>
                  </td>
                  <td className="text-ink-500 px-3 py-2 text-right font-semibold tabular-nums line-through">
                    {before.toFixed(0)}
                  </td>
                  <td className="text-ink-400 px-1 py-2 text-center">
                    <FontAwesomeIcon icon="arrow-right" className="text-xs" aria-hidden="true" />
                  </td>
                  <td
                    className={cxMark(after, before)}
                  >
                    {after.toFixed(0)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Input
        label="Reason for replacing these marks"
        value={reason}
        onChange={(e) => onReasonChange(e.target.value)}
        placeholder="e.g. Re-marked after a script was found"
        hint="Recorded on the audit trail against every mark you replace."
        className="mt-4"
      />
    </div>
  )
}

/** Up in green, down in red, unchanged in grey - the direction matters. */
function cxMark(after, before) {
  const base = 'px-3 py-2 text-right font-semibold tabular-nums '
  if (after > before) return base + 'text-success-700'
  if (after < before) return base + 'text-danger-700'
  return base + 'text-ink-500'
}

export default ReplaceConfirmation
