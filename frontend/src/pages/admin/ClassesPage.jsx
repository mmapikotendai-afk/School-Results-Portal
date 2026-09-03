import { useState } from 'react'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  Input,
  Modal,
  RowAction,
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { classService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

const LEVELS = [
  { value: 'O_LEVEL', label: 'O-Level (Forms 1 to 4)' },
  { value: 'A_LEVEL', label: 'A-Level (Lower and Upper 6)' },
]

function ClassForm({ open, schoolClass, onClose, onSaved }) {
  const isEdit = Boolean(schoolClass)
  const [form, setForm] = useState({
    name: schoolClass?.name ?? '',
    level: schoolClass?.level ?? 'O_LEVEL',
  })
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  function handleChange(event) {
    const { name, value } = event.target
    setForm((p) => ({ ...p, [name]: value }))
    setFieldErrors((p) => ({ ...p, [name]: undefined }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!form.name.trim()) {
      setFieldErrors({ name: 'Enter a class name.' })
      return
    }

    setSaving(true)
    setError(null)
    try {
      const payload = { name: form.name.trim(), level: form.level }
      if (isEdit) {
        await classService.update(schoolClass.id, payload)
        onSaved(`${payload.name} has been updated.`)
      } else {
        await classService.create(payload)
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
      title={isEdit ? 'Edit class' : 'Create class'}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={saving} icon="check">
            {isEdit ? 'Save changes' : 'Create class'}
          </Button>
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-4" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <Input
          label="Class name"
          name="name"
          value={form.name}
          onChange={handleChange}
          error={fieldErrors.name}
          hint="Any naming convention works, for example 1C, Form 4A or Lower 6 Sciences."
          placeholder="Form 4A"
          disabled={saving}
          required
        />
        <Select
          label="Level"
          name="level"
          value={form.level}
          onChange={handleChange}
          options={LEVELS}
          hint="Decides which grading scale applies to this class."
          disabled={saving}
        />
      </form>
    </Modal>
  )
}

export function ClassesPage() {
  useDocumentTitle('Classes')

  const [formState, setFormState] = useState(null)
  const [confirming, setConfirming] = useState(null)
  const { toast, show, clear } = useToast()

  const { data, loading, error, refresh } = useAsyncData(() => classService.list(), [])

  async function toggleActive(schoolClass) {
    try {
      await classService.setStatus(schoolClass.id, !schoolClass.is_active)
      show(
        schoolClass.is_active
          ? `${schoolClass.name} has been deactivated.`
          : `${schoolClass.name} is active again.`,
      )
      refresh()
    } catch (err) {
      show(getErrorMessage(err), 'danger')
      throw err
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Class',
      render: (row) => <span className="text-ink-900 font-medium">{row.name}</span>,
    },
    {
      key: 'level',
      header: 'Level',
      render: (row) => (
        <Badge tone="brand">{row.level === 'O_LEVEL' ? 'O-Level' : 'A-Level'}</Badge>
      ),
    },
    {
      key: 'student_count',
      header: 'Students',
      render: (row) => (
        <span className="text-ink-700">
          {row.student_count} {row.student_count === 1 ? 'student' : 'students'}
        </span>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (row) => (
        <Badge tone={row.is_active ? 'success' : 'neutral'}>
          {row.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) => (
        <div className="flex items-center justify-end gap-0.5">
          <RowAction
            icon="pen-to-square"
            label="Edit"
            tone="brand"
            onClick={() => setFormState({ schoolClass: row })}
          />
          <RowAction
            icon={row.is_active ? 'ban' : 'circle-check'}
            label={row.is_active ? 'Deactivate' : 'Reactivate'}
            tone={row.is_active ? 'danger' : 'neutral'}
            onClick={() => setConfirming(row)}
          />
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Classes"
        description="Forms and streams. Create whatever names your school uses."
        actions={
          <Button icon="plus" onClick={() => setFormState({ schoolClass: null })}>
            Create class
          </Button>
        }
      />

      {error && (
        <Alert tone="danger" className="mb-5">
          {error}
        </Alert>
      )}

      <Card>
        <DataTable
          columns={columns}
          rows={data ?? []}
          loading={loading && !data}
          empty={
            <EmptyState
              icon="table-list"
              title="No classes yet"
              description="Create the classes your school runs, for example 1C, Form 4A or Upper 6 Sciences."
              action={
                <Button icon="plus" onClick={() => setFormState({ schoolClass: null })}>
                  Create class
                </Button>
              }
            />
          }
        />
      </Card>

      {formState && (
        <ClassForm
          open
          schoolClass={formState.schoolClass}
          onClose={() => setFormState(null)}
          onSaved={(message) => {
            setFormState(null)
            show(message)
            refresh()
          }}
        />
      )}

      <ConfirmDialog
        open={Boolean(confirming)}
        onClose={() => setConfirming(null)}
        onConfirm={() => toggleActive(confirming)}
        title={confirming?.is_active ? 'Deactivate this class?' : 'Reactivate this class?'}
        message={
          confirming?.is_active
            ? `${confirming?.name} will no longer be offered when adding or editing students.`
            : `${confirming?.name} will be available again.`
        }
        detail={
          confirming?.is_active && confirming?.student_count > 0 ? (
            <Alert tone="warning">
              This class still has {confirming.student_count}{' '}
              {confirming.student_count === 1 ? 'student' : 'students'} in it. Move them
              to another class first.
            </Alert>
          ) : null
        }
        confirmLabel={confirming?.is_active ? 'Deactivate' : 'Reactivate'}
        variant={confirming?.is_active ? 'danger' : 'primary'}
        icon={confirming?.is_active ? 'ban' : 'circle-check'}
      />

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default ClassesPage
