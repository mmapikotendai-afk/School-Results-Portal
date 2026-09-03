import { useMemo, useState } from 'react'

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
  SearchInput,
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDebounced from '@/hooks/useDebounced'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { subjectService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

const LEVELS = [
  { value: 'BOTH', label: 'Both O-Level and A-Level' },
  { value: 'O_LEVEL', label: 'O-Level only' },
  { value: 'A_LEVEL', label: 'A-Level only' },
]

const LEVEL_LABEL = { BOTH: 'O & A', O_LEVEL: 'O-Level', A_LEVEL: 'A-Level' }

function SubjectForm({ open, subject, onClose, onSaved }) {
  const isEdit = Boolean(subject)
  const [form, setForm] = useState({
    name: subject?.name ?? '',
    code: subject?.code ?? '',
    level: subject?.level ?? 'BOTH',
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
    const errors = {}
    if (!form.name.trim()) errors.name = 'Enter a subject name.'
    if (!form.code.trim()) errors.code = 'Enter a subject code.'
    setFieldErrors(errors)
    if (Object.keys(errors).length) return

    setSaving(true)
    setError(null)
    try {
      const payload = { name: form.name.trim(), code: form.code.trim(), level: form.level }
      if (isEdit) {
        await subjectService.update(subject.id, payload)
        onSaved(`${payload.name} has been updated.`)
      } else {
        await subjectService.create(payload)
        onSaved(`${payload.name} has been added.`)
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
      title={isEdit ? 'Edit subject' : 'Add subject'}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={saving} icon="check">
            {isEdit ? 'Save changes' : 'Add subject'}
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
          label="Subject name"
          name="name"
          value={form.name}
          onChange={handleChange}
          error={fieldErrors.name}
          placeholder="Mathematics"
          disabled={saving}
          required
        />
        <Input
          label="Subject code"
          name="code"
          value={form.code}
          onChange={handleChange}
          error={fieldErrors.code}
          hint="Must be unique. Stored in upper case, and used in result uploads."
          placeholder="MATH"
          disabled={saving}
          required
        />
        <Select
          label="Level"
          name="level"
          value={form.level}
          onChange={handleChange}
          options={LEVELS}
          hint="Which half of the school offers this subject."
          disabled={saving}
        />
      </form>
    </Modal>
  )
}

export function SubjectsPage() {
  useDocumentTitle('Subjects')

  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounced(search, 300)
  const [formState, setFormState] = useState(null)
  const [confirming, setConfirming] = useState(null)
  const [usage, setUsage] = useState(null)
  const { toast, show, clear } = useToast()

  const query = useMemo(() => ({ search: debouncedSearch || undefined }), [debouncedSearch])
  const { data, loading, error, refresh } = useAsyncData(() => subjectService.list(query), [query])

  async function openConfirm(subject) {
    setConfirming(subject)
    setUsage(null)
    if (subject.is_active) {
      try {
        setUsage(await subjectService.usage(subject.id))
      } catch {
        // The dialog still works without the usage figures.
      }
    }
  }

  async function toggleActive(subject) {
    try {
      await subjectService.setStatus(subject.id, !subject.is_active)
      show(
        subject.is_active
          ? `${subject.name} has been retired.`
          : `${subject.name} is offered again.`,
      )
      refresh()
    } catch (err) {
      show(getErrorMessage(err), 'danger')
      throw err
    }
  }

  const columns = [
    {
      key: 'code',
      header: 'Code',
      render: (row) => (
        <span className="text-ink-900 font-mono text-xs font-semibold">{row.code}</span>
      ),
    },
    {
      key: 'name',
      header: 'Subject',
      render: (row) => <span className="text-ink-900 font-medium">{row.name}</span>,
    },
    {
      key: 'level',
      header: 'Level',
      render: (row) => <Badge tone="brand">{LEVEL_LABEL[row.level] ?? row.level}</Badge>,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (row) => (
        <Badge tone={row.is_active ? 'success' : 'neutral'}>
          {row.is_active ? 'Offered' : 'Retired'}
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
            onClick={() => setFormState({ subject: row })}
          />
          <RowAction
            icon={row.is_active ? 'ban' : 'circle-check'}
            label={row.is_active ? 'Retire' : 'Offer again'}
            tone={row.is_active ? 'danger' : 'neutral'}
            onClick={() => openConfirm(row)}
          />
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Subjects"
        description="The subjects the school examines. Used for enrollment, uploads and report cards."
        actions={
          <Button icon="plus" onClick={() => setFormState({ subject: null })}>
            Add subject
          </Button>
        }
      />

      {error && (
        <Alert tone="danger" className="mb-5">
          {error}
        </Alert>
      )}

      <Card>
        <div className="border-ink-200 border-b px-5 py-4">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search by name or code"
            className="max-w-md"
          />
        </div>

        <DataTable
          columns={columns}
          rows={data ?? []}
          loading={loading && !data}
          empty={
            <EmptyState
              icon="book"
              title={search ? 'No subjects match that search' : 'No subjects yet'}
              description={
                search
                  ? 'Try a different name or code.'
                  : 'Add the subjects your school examines.'
              }
              action={
                !search && (
                  <Button icon="plus" onClick={() => setFormState({ subject: null })}>
                    Add subject
                  </Button>
                )
              }
            />
          }
        />
      </Card>

      {formState && (
        <SubjectForm
          open
          subject={formState.subject}
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
        title={confirming?.is_active ? 'Retire this subject?' : 'Offer this subject again?'}
        message={
          confirming?.is_active
            ? `${confirming?.name} will no longer be available for new enrollment or assignment. It is never deleted, because results and enrollment history reference it.`
            : `${confirming?.name} will be available for enrollment again.`
        }
        detail={
          usage && (
            <div className="bg-ink-50 rounded-lg px-4 py-3 text-sm">
              <p className="text-ink-600">
                This subject currently has{' '}
                <strong className="text-ink-900">{usage.enrollments}</strong> enrollment
                records and <strong className="text-ink-900">{usage.results}</strong>{' '}
                recorded results. All of them are kept.
              </p>
            </div>
          )
        }
        confirmLabel={confirming?.is_active ? 'Retire subject' : 'Offer again'}
        variant={confirming?.is_active ? 'danger' : 'primary'}
        icon={confirming?.is_active ? 'ban' : 'circle-check'}
      />

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default SubjectsPage
