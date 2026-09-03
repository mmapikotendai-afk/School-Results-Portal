import { useState } from 'react'

import { Alert, Button, Input, Modal, Select } from '@/components/ui'
import { academicService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

/**
 * Create or edit a term.
 *
 * A new term needs a year to belong to; an existing one cannot be moved between
 * years, because examinations and results are already attached beneath it.
 */
export function TermFormModal({ open, term, years = [], onClose, onSaved }) {
  const isEdit = Boolean(term)
  const activeYear = years.find((y) => y.is_active)
  const [form, setForm] = useState({
    academic_year_id: term?.academic_year_id ?? activeYear?.id ?? '',
    name: term?.name ?? '',
    start_date: term?.start_date ?? '',
    end_date: term?.end_date ?? '',
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
    if (!form.name.trim()) errors.name = 'Enter a term name.'
    if (!isEdit && !form.academic_year_id) errors.academic_year_id = 'Choose an academic year.'
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
        await academicService.updateTerm(term.id, payload)
        onSaved(`${payload.name} has been updated.`)
      } else {
        await academicService.createTerm({
          ...payload,
          academic_year_id: Number(form.academic_year_id),
        })
        onSaved(`${payload.name} has been created.`)
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
      title={isEdit ? 'Edit term' : 'Create term'}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving} icon="check">
            {isEdit ? 'Save changes' : 'Create term'}
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
        {!isEdit && (
          <Select
            label="Academic year"
            name="academic_year_id"
            value={form.academic_year_id}
            onChange={change}
            error={fieldErrors.academic_year_id}
            placeholder="Choose a year"
            options={years.map((y) => ({ value: y.id, label: y.name }))}
            disabled={saving}
          />
        )}
        <Input
          label="Term name"
          name="name"
          value={form.name}
          onChange={change}
          error={fieldErrors.name}
          placeholder="Term 1"
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

export default TermFormModal
