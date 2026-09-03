import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, Button, Modal, Spinner, SubjectPicker } from '@/components/ui'
import { studentService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

/**
 * Manage which subjects a student studies.
 *
 * Removing a subject is a drop, not a deletion: the enrollment is marked
 * INACTIVE and stamped, so the record and any results already attached to it
 * survive. Because that is easy to do by accident, dropping is confirmed by
 * name before anything is sent.
 */
export function StudentSubjectsModal({ open, student, subjects, onClose, onSaved }) {
  const [selected, setSelected] = useState(null)
  const [original, setOriginal] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [confirmingDrops, setConfirmingDrops] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const rows = await studentService.getSubjects(student.id)
        if (cancelled) return
        const ids = rows.map((s) => s.id)
        setSelected(ids)
        setOriginal(ids)
        setError(null)
      } catch (err) {
        if (!cancelled) setError(getErrorMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [student.id])

  const current = selected ?? []
  const dropped = original.filter((id) => !current.includes(id))
  const added = current.filter((id) => !original.includes(id))
  const hasChanges = dropped.length > 0 || added.length > 0

  const nameOf = (id) => subjects.find((s) => s.id === id)?.name ?? `Subject ${id}`

  async function save() {
    setSaving(true)
    setError(null)
    try {
      const change = await studentService.setSubjects(student.id, current)
      const parts = []
      if (change.added.length) parts.push(`added ${change.added.join(', ')}`)
      if (change.reactivated.length) parts.push(`re-enrolled ${change.reactivated.join(', ')}`)
      if (change.dropped.length) parts.push(`dropped ${change.dropped.join(', ')}`)
      onSaved(
        parts.length
          ? `${student.full_name}: ${parts.join('; ')}.`
          : `No changes for ${student.full_name}.`,
      )
    } catch (err) {
      setError(getErrorMessage(err))
      setSaving(false)
      setConfirmingDrops(false)
    }
  }

  function handleSave() {
    // Dropping loses nothing permanently, but it does remove the student from
    // future mark sheets, so it gets a second look.
    if (dropped.length > 0 && !confirmingDrops) {
      setConfirmingDrops(true)
      return
    }
    save()
  }

  return (
    <Modal
      open={open}
      onClose={saving ? undefined : onClose}
      title="Manage subjects"
      description={`${student.full_name} · ${student.school_class?.name ?? 'No class'}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            loading={saving}
            disabled={!hasChanges || loading}
            icon={confirmingDrops ? 'triangle-exclamation' : 'check'}
            variant={confirmingDrops ? 'danger' : 'primary'}
          >
            {confirmingDrops ? 'Yes, drop and save' : 'Save enrollment'}
          </Button>
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-4" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading ? (
        <div className="flex items-center justify-center gap-3 py-10">
          <Spinner />
          <span className="text-ink-500 text-sm">Loading enrollment…</span>
        </div>
      ) : (
        <>
          {confirmingDrops && (
            <Alert tone="warning" title="Confirm dropped subjects" className="mb-4">
              <p>
                {student.full_name} will be dropped from{' '}
                <strong>{dropped.map(nameOf).join(', ')}</strong>.
              </p>
              <p className="mt-1.5">
                Their enrollment history and any results already recorded are kept, but
                they will not appear on future mark sheets for these subjects.
              </p>
            </Alert>
          )}

          <SubjectPicker
            subjects={subjects}
            selectedIds={current}
            onChange={setSelected}
            disabled={saving}
          />

          {hasChanges && !confirmingDrops && (
            <div className="border-ink-200 mt-4 space-y-1.5 rounded-lg border p-3">
              {added.length > 0 && (
                <p className="text-success-700 flex items-start gap-2 text-sm">
                  <FontAwesomeIcon icon="plus" className="mt-1 text-xs" aria-hidden="true" />
                  <span>Enrolling in {added.map(nameOf).join(', ')}</span>
                </p>
              )}
              {dropped.length > 0 && (
                <p className="text-warning-700 flex items-start gap-2 text-sm">
                  <FontAwesomeIcon icon="minus" className="mt-1 text-xs" aria-hidden="true" />
                  <span>Dropping {dropped.map(nameOf).join(', ')}</span>
                </p>
              )}
            </div>
          )}
        </>
      )}
    </Modal>
  )
}

export default StudentSubjectsModal
