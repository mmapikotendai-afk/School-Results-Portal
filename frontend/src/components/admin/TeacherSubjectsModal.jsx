import { useEffect, useState } from 'react'

import { Alert, Button, Modal, Spinner, SubjectPicker } from '@/components/ui'
import { teacherService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

/**
 * Assign subjects to a teacher.
 *
 * Unassigning does not delete the assignment: it is deactivated, so the
 * submission records that reference it stay intact.
 */
export function TeacherSubjectsModal({ open, teacher, subjects, onClose, onSaved }) {
  const [selected, setSelected] = useState(null)
  const [original, setOriginal] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    teacherService
      .get(teacher.id)
      .then((data) => {
        if (cancelled) return
        const ids = data.subjects.map((s) => s.id)
        setSelected(ids)
        setOriginal(ids)
      })
      .catch((err) => !cancelled && setError(getErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [teacher.id])

  const current = selected ?? []
  const hasChanges =
    current.length !== original.length || current.some((id) => !original.includes(id))

  async function save() {
    setSaving(true)
    setError(null)
    try {
      const change = await teacherService.setSubjects(teacher.id, current)
      const parts = []
      if (change.added.length) parts.push(`assigned ${change.added.join(', ')}`)
      if (change.reactivated.length) parts.push(`reassigned ${change.reactivated.join(', ')}`)
      if (change.dropped.length) parts.push(`unassigned ${change.dropped.join(', ')}`)
      onSaved(
        parts.length
          ? `${teacher.full_name}: ${parts.join('; ')}.`
          : `No changes for ${teacher.full_name}.`,
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
      title="Assign subjects"
      description={`${teacher.full_name} · ${teacher.employee_number}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={save} loading={saving} disabled={!hasChanges || loading} icon="check">
            Save assignment
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
          <span className="text-ink-500 text-sm">Loading assignments…</span>
        </div>
      ) : (
        <>
          <SubjectPicker
            subjects={subjects}
            selectedIds={current}
            onChange={setSelected}
            disabled={saving}
          />
          <p className="text-ink-500 mt-4 text-sm">
            Unassigning a subject keeps the record of anything this teacher has already
            submitted for it.
          </p>
        </>
      )}
    </Modal>
  )
}

export default TeacherSubjectsModal
