import { useState } from 'react'

import { Alert, Button, Input, Modal, Select, SubjectPicker } from '@/components/ui'
import { studentService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

const GENDERS = [
  { value: 'MALE', label: 'Male' },
  { value: 'FEMALE', label: 'Female' },
  { value: 'OTHER', label: 'Other' },
]

function initialForm(student) {
  return {
    student_number: student?.student_number ?? '',
    first_name: student?.first_name ?? '',
    last_name: student?.last_name ?? '',
    date_of_birth: student?.date_of_birth ?? '',
    gender: student?.gender ?? '',
    class_id: student?.school_class?.id ?? '',
    email: student?.email ?? '',
  }
}

/**
 * Add or edit a student.
 *
 * On create, subjects are chosen here too, so a learner is enrolled in one
 * step. On edit the subject picker is left out: enrollment changes are
 * consequential (they can drop a subject) and belong in their own dialog with
 * their own confirmation.
 */
export function StudentFormModal({ open, mode, student, classes, subjects, onClose, onSaved }) {
  const isEdit = mode === 'edit'

  const [form, setForm] = useState(() => initialForm(student))
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
    if (!form.student_number.trim()) errors.student_number = 'A student number is required.'
    if (!form.first_name.trim()) errors.first_name = 'Enter a first name.'
    if (!form.last_name.trim()) errors.last_name = 'Enter a last name.'
    if (form.date_of_birth && form.date_of_birth > new Date().toISOString().slice(0, 10)) {
      errors.date_of_birth = 'Date of birth cannot be in the future.'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    if (!validate()) return

    // Empty strings mean "not provided", which is not the same as clearing a
    // value, so they are stripped rather than sent as null.
    const payload = {
      student_number: form.student_number.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      date_of_birth: form.date_of_birth || null,
      gender: form.gender || null,
      class_id: form.class_id ? Number(form.class_id) : null,
    }
    if (form.email.trim()) payload.email = form.email.trim()

    setSaving(true)
    try {
      if (isEdit) {
        await studentService.update(student.id, payload)
        onSaved(`${payload.first_name} ${payload.last_name} has been updated.`)
      } else {
        const result = await studentService.create({
          ...payload,
          subject_ids: selectedSubjects,
        })
        // The initial password is shown once and never retrievable again, so
        // the dialog stays open until the office has copied it.
        setCreated(result)
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  if (created) {
    return (
      <Modal
        open={open}
        onClose={() => onSaved(`${created.full_name} has been added.`)}
        title="Student added"
        description={`${created.full_name} · ${created.student_number}`}
        footer={
          <Button onClick={() => onSaved(`${created.full_name} has been added.`)} icon="check">
            Done
          </Button>
        }
      >
        <Alert tone="warning" title="Copy these sign-in details now">
          This password is shown once and cannot be retrieved later. If it is lost, issue
          a new one from the account settings.
        </Alert>

        <dl className="border-ink-200 mt-4 divide-y divide-ink-100 rounded-lg border">
          <div className="flex items-center justify-between gap-4 px-4 py-3">
            <dt className="text-ink-500 text-sm">Username</dt>
            <dd className="text-ink-900 font-mono text-sm font-semibold">
              {created.student_number.toLowerCase()}
            </dd>
          </div>
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
      title={isEdit ? 'Edit student' : 'Add student'}
      description={
        isEdit ? student.full_name : 'Creates the learner record and their portal account.'
      }
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={saving} icon="check">
            {isEdit ? 'Save changes' : 'Add student'}
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
            label="Student number"
            name="student_number"
            value={form.student_number}
            onChange={handleChange}
            error={fieldErrors.student_number}
            hint="Must be unique. Used to match uploaded results."
            placeholder="STU-0001"
            disabled={saving}
            required
          />
          <Select
            label="Class"
            name="class_id"
            value={form.class_id}
            onChange={handleChange}
            placeholder="Not assigned"
            disabled={saving}
            options={classes.map((c) => ({
              value: c.id,
              label: `${c.name} (${c.level === 'O_LEVEL' ? 'O-Level' : 'A-Level'})`,
            }))}
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
            label="Date of birth"
            name="date_of_birth"
            type="date"
            value={form.date_of_birth ?? ''}
            onChange={handleChange}
            error={fieldErrors.date_of_birth}
            disabled={saving}
          />
          <Select
            label="Gender"
            name="gender"
            value={form.gender ?? ''}
            onChange={handleChange}
            placeholder="Not recorded"
            options={GENDERS}
            disabled={saving}
          />
        </div>

        <Input
          label="Email address"
          name="email"
          type="email"
          value={form.email}
          onChange={handleChange}
          hint={
            isEdit
              ? 'Used to sign in.'
              : 'Optional. Left blank, one is derived from the student number.'
          }
          disabled={saving}
        />

        {!isEdit && (
          <div className="border-ink-200 border-t pt-5">
            <p className="text-ink-700 mb-1 text-sm font-medium">Subjects</p>
            <p className="text-ink-500 mb-3 text-sm">
              Tick everything this student studies. Results can only be recorded for
              subjects they are enrolled in.
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

export default StudentFormModal
