import { useState } from 'react'

import { Alert, Button, Input, Modal } from '@/components/ui'
import { academicService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

/**
 * Create or edit an academic year.
 *
 * Validation runs before the request so an obvious mistake is answered
 * immediately, beside the field it belongs to, rather than after a round trip.
 */
export function AcademicYearFormModal({ open, year, onClose, onSaved }) {
  const isEdit = Boolean(year)
  const [form, setForm] = useState({
    name: year?.name ?? '',
    start_date: year?.start_date ?? '',
    end_date: year?.end_date ?? '',
  })
  const [error, setError] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const change = (e) => {
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }))
    setFieldErrors((p) => ({ ...p, [e.target.name]: undefined }))
  }

  async function submit(event) {
    event.preventDefault()
    const errors = {}
    if (!form.name.trim()) errors.name = 'Enter a name, for example 2026.'
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      errors.end_date = 'The end date must fall on or after the start date.'
    }
    setFieldErrors(errors)
    if (Object.keys(errors).length) return

    setSaving(true)
    setError(null)
    try {
      const payload = {
        name: form.name.trim(),
        start_date: form.start_date || null,
        end_date: form.end_date || null,
      }
      if (isEdit) {
        await academicService.updateYear(year.id, payload)
        onSaved(`${payload.name} has been updated.`)
      } else {
        await academicService.createYear(payload)
        onSaved(`Academic year ${payload.name} has been created.`)
      }
    } catch (err) {
      setError(getErrorMessage(err))
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit academic year' : 'Create academic year'}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving} icon="check">
            {isEdit ? 'Save changes' : 'Create year'}
          </Button>
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-4" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}
      <form onSubmit={submit} noValidate className="space-y-4">
        <Input
          label="Name"
          name="name"
          value={form.name}
          onChange={change}
          error={fieldErrors.name}
          placeholder="2026"
          hint="However your school writes it — 2026, or 2026/2027."
          disabled={saving}
          required
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Starts"
            name="start_date"
            type="date"
            value={form.start_date ?? ''}
            onChange={change}
            disabled={saving}
          />
          <Input
            label="Ends"
            name="end_date"
            type="date"
            value={form.end_date ?? ''}
            onChange={change}
            error={fieldErrors.end_date}
            disabled={saving}
          />
        </div>
      </form>
    </Modal>
  )
}

export default AcademicYearFormModal
