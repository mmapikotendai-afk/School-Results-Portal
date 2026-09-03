import { useState } from 'react'

import { Alert, Button, Input, Modal, SubjectPicker } from '@/components/ui'
import { teacherService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

function initialForm(teacher) {
  return {
    employee_number: teacher?.employee_number ?? '',
    first_name: teacher?.first_name ?? '',
    last_name: teacher?.last_name ?? '',
    email: teacher?.email ?? '',
    department: teacher?.department ?? '',
    phone: teacher?.phone ?? '',
  }
}

/** Add or edit a teacher, with subject assignment on creation. */
export function TeacherFormModal({ open, mode, teacher, subjects, onClose, onSaved }) {
  const isEdit = mode === 'edit'

  const [form, setForm] = useState(() => initialForm(teacher))
  const [selectedSubjects, setSelectedSubjects] = useState([])
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [created, setCreated] = useState(null)

  function handleChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
    setFieldErrors((previous) => ({ ...previous, [name]: undefined }))
  }

  function validate() {
    const errors = {}
    if (!form.employee_number.trim()) errors.employee_number = 'An employee number is required.'
    if (!form.first_name.trim()) errors.first_name = 'Enter a first name.'
    if (!form.last_name.trim()) errors.last_name = 'Enter a last name.'
    if (!form.email.trim()) {
      errors.email = 'An email address is required.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      errors.email = 'Enter a valid email address.'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    if (!validate()) return

    const payload = {
      employee_number: form.employee_number.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      department: form.department.trim() || null,
      phone: form.phone.trim() || null,
    }

    setSaving(true)
    try {
      if (isEdit) {
        await teacherService.update(teacher.id, payload)
        onSaved(`${payload.first_name} ${payload.last_name} has been updated.`)
      } else {
        const result = await teacherService.create({
          ...payload,
          subject_ids: selectedSubjects,
        })
        // The password is shown once; the dialog stays open until it is copied.
        setCreated(result)
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  if (created) {
    const done = () => onSaved(`${created.full_name} has been added.`)
    return (
      <Modal
        open={open}
        onClose={done}
        title="Teacher added"
        description={`${created.full_name} · ${created.employee_number}`}
        footer={
          <Button onClick={done} icon="check">
            Done
          </Button>
        }
      >
        <Alert tone="warning" title="Copy these sign-in details now">
          This password is shown once and cannot be retrieved later.
        </Alert>

        <dl className="border-ink-200 divide-ink-100 mt-4 divide-y rounded-lg border">
          <div className="flex items-center justify-between gap-4 px-4 py-3">
            <dt className="text-ink-500 text-sm">Email</dt>
            <dd className="text-ink-900 font-mono text-sm">{created.email}</dd>
          </div>
          <div className="flex items-center justify-between gap-4 px-4 py-3">
            <dt className="text-ink-500 text-sm">Temporary password</dt>
            <dd className="text-brand-800 bg-brand-50 rounded px-2 py-1 font-mono text-sm font-semibold">
              {created.initial_password}
            </dd>
          </div>
        </dl>

        <p className="text-ink-500 mt-4 text-sm">
          They will be asked to set their own password from Settings after signing in.
        </p>
      </Modal>
    )
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit teacher' : 'Add teacher'}
      description={isEdit ? teacher.full_name : 'Creates the staff record and their portal account.'}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={saving} icon="check">
            {isEdit ? 'Save changes' : 'Add teacher'}
          </Button>
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-5" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Employee number"
            name="employee_number"
            value={form.employee_number}
            onChange={handleChange}
            error={fieldErrors.employee_number}
            hint="Must be unique."
            placeholder="EMP-0001"
            disabled={saving}
            required
          />
          <Input
            label="Department"
            name="department"
            value={form.department}
            onChange={handleChange}
            placeholder="Sciences"
            disabled={saving}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="First name"
            name="first_name"
            value={form.first_name}
            onChange={handleChange}
            error={fieldErrors.first_name}
            disabled={saving}
            required
          />
          <Input
            label="Last name"
            name="last_name"
            value={form.last_name}
            onChange={handleChange}
            error={fieldErrors.last_name}
            disabled={saving}
            required
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Email address"
            name="email"
            type="email"
            icon="envelope"
            value={form.email}
            onChange={handleChange}
            error={fieldErrors.email}
            hint="Used to sign in."
            disabled={saving}
            required
          />
          <Input
            label="Phone"
            name="phone"
            value={form.phone}
            onChange={handleChange}
            disabled={saving}
          />
        </div>

        {!isEdit && (
          <div className="border-ink-200 border-t pt-5">
            <p className="text-ink-700 mb-1 text-sm font-medium">Subjects taught</p>
            <p className="text-ink-500 mb-3 text-sm">
              Assigning a subject makes this teacher responsible for submitting its
              results, and adds them to the submission monitor.
            </p>
            <SubjectPicker
              subjects={subjects}
              selectedIds={selectedSubjects}
              onChange={setSelectedSubjects}
              disabled={saving}
            />
          </div>
        )}
      </form>
    </Modal>
  )
}

export default TeacherFormModal
