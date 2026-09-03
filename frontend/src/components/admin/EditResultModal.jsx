import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, Button, Input, Modal } from '@/components/ui'
import { getErrorMessage } from '@/services/apiClient'
import { resultsService } from '@/services/adminService'
import { cx } from '@/utils/format'

const MIN = 0
const MAX = 100

/**
 * Correct one mark.
 *
 * The reason is required, not optional politeness: it is what the audit trail
 * records alongside the old and new values, and a correction nobody can
 * explain later is the thing the trail exists to prevent.
 */
export function EditResultModal({ open, subject, student, examination, onClose, onSaved }) {
  const original = Number(subject.marks)
  const [marks, setMarks] = useState(String(original))
  const [reason, setReason] = useState('')
  const [remarks, setRemarks] = useState(subject.remarks ?? '')
  const [errors, setErrors] = useState({})
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const value = Number(marks)
  const changed = marks !== '' && value !== original
  const outOfRange = marks !== '' && (Number.isNaN(value) || value < MIN || value > MAX)

  async function save(event) {
    event.preventDefault()
    const next = {}
    if (marks === '' || outOfRange) next.marks = `Enter a mark between ${MIN} and ${MAX}.`
    if (reason.trim().length < 3) next.reason = 'Give a reason for this correction.'
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    setError(null)
    try {
      await resultsService.editResult(subject.result_id, {
        marks: value,
        remarks: remarks.trim() || null,
        reason: reason.trim(),
      })
      onSaved(
        `${subject.subject_name} corrected from ${original.toFixed(0)} to ${value.toFixed(0)} for ${student.student_name}.`,
      )
    } catch (err) {
      setError(getErrorMessage(err))
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={saving ? undefined : onClose}
      title="Correct a result"
      description={`${student.student_name} · ${subject.subject_name} · ${examination}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            onClick={save}
            loading={saving}
            disabled={!changed || outOfRange}
            variant="danger"
            icon="check"
          >
            Save correction
          </Button>
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-4" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <div className="bg-ink-50 mb-5 flex items-center justify-center gap-6 rounded-lg px-4 py-4">
        <div className="text-center">
          <p className="text-ink-400 text-xs">Current</p>
          <p className="text-ink-500 text-2xl font-semibold tabular-nums">
            {original.toFixed(0)}
          </p>
          <p className="text-ink-400 text-xs">{subject.grade}</p>
        </div>
        <FontAwesomeIcon icon="arrow-right" className="text-ink-300" aria-hidden="true" />
        <div className="text-center">
          <p className="text-ink-400 text-xs">New</p>
          <p
            className={cx(
              'text-2xl font-semibold tabular-nums',
              !changed || outOfRange
                ? 'text-ink-300'
                : value > original
                  ? 'text-success-700'
                  : 'text-danger-700',
            )}
          >
            {marks === '' || outOfRange ? '—' : value.toFixed(0)}
          </p>
          <p className="text-ink-400 text-xs">
            {changed && !outOfRange ? 'grade recalculated on save' : ' '}
          </p>
        </div>
      </div>

      <form onSubmit={save} noValidate className="space-y-4">
        <Input
          label="Mark"
          type="number"
          min={MIN}
          max={MAX}
          step="0.01"
          value={marks}
          onChange={(e) => {
            setMarks(e.target.value)
            setErrors((p) => ({ ...p, marks: undefined }))
          }}
          error={errors.marks}
          hint={`Between ${MIN} and ${MAX}. The grade is derived from the school's grading scale.`}
          disabled={saving}
          autoFocus
          required
        />

        <Input
          label="Reason for the correction"
          value={reason}
          onChange={(e) => {
            setReason(e.target.value)
            setErrors((p) => ({ ...p, reason: undefined }))
          }}
          error={errors.reason}
          placeholder="e.g. Re-marked after the script was found"
          hint="Recorded on the audit trail against your name."
          disabled={saving}
          required
        />

        <Input
          label="Remark (optional)"
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
          hint="Leave blank to use the remark from the grading scale."
          disabled={saving}
        />
      </form>

      <Alert tone="warning" className="mt-5">
        This changes a mark on the student&apos;s record. The old value, the new value,
        your name and the reason are all recorded permanently.
      </Alert>
    </Modal>
  )
}

export default EditResultModal
