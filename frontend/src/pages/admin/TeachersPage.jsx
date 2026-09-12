import { useMemo, useState } from 'react'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import TeacherFormModal from '@/components/admin/TeacherFormModal'
import TeacherSubjectsModal from '@/components/admin/TeacherSubjectsModal'
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  Pagination,
  RowAction,
  SearchInput,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDebounced from '@/hooks/useDebounced'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { subjectService, teacherService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

const PAGE_SIZE = 15

export function TeachersPage() {
  useDocumentTitle('Teachers')

  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(true)
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebounced(search, 350)

  const [formState, setFormState] = useState(null)
  const [subjectsFor, setSubjectsFor] = useState(null)
  const [confirming, setConfirming] = useState(null)
  const [resending, setResending] = useState(null)
  const { toast, show, clear } = useToast()

  const query = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      include_inactive: showInactive,
      page,
      page_size: PAGE_SIZE,
    }),
    [debouncedSearch, showInactive, page],
  )

  const { data, loading, error, refresh } = useAsyncData(() => teacherService.list(query), [query])
  const { data: subjects } = useAsyncData(
    () => subjectService.list({ include_inactive: false }),
    [],
  )

  async function toggleActive(teacher) {
    try {
      await teacherService.setStatus(teacher.id, !teacher.is_active)
      show(
        teacher.is_active
          ? `${teacher.full_name} has been deactivated.`
          : `${teacher.full_name} has been reactivated.`,
      )
      refresh()
    } catch (err) {
      show(getErrorMessage(err), 'danger')
      throw err
    }
  }


  /**
   * Issue a new temporary password and email it.
   *
   * The server generates the password; nothing readable comes back here. The
   * old password stops working at once, so this is a real reset rather than a
   * repeat of the original message.
   */
  async function resendCredentials(row) {
    const result = await teacherService.resendCredentials(row.id)
    show(
      result.sent
        ? `New sign-in details sent to ${result.email}.`
        : `Could not email ${result.email}. ${result.detail}`,
      result.sent ? 'success' : 'danger',
    )
  }

  const columns = [
    {
      key: 'employee_number',
      header: 'Employee number',
      render: (row) => (
        <span className="text-ink-900 font-mono text-xs font-semibold">
          {row.employee_number}
        </span>
      ),
    },
    {
      key: 'full_name',
      header: 'Name',
      render: (row) => (
        <div className="min-w-0">
          <p className="text-ink-900 font-medium">{row.full_name}</p>
          <p className="text-ink-400 truncate text-xs">{row.email}</p>
        </div>
      ),
    },
    {
      key: 'department',
      header: 'Department',
      render: (row) => row.department || <span className="text-ink-400">—</span>,
    },
    {
      key: 'subject_count',
      header: 'Subjects taught',
      render: (row) => (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation()
            setSubjectsFor(row)
          }}
          className="text-brand-700 hover:bg-brand-50 rounded-lg px-2 py-1 text-sm font-medium transition-colors"
        >
          {row.subject_count} assigned
        </button>
      ),
    },
    {
      key: 'status',
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
            onClick={() => setFormState({ mode: 'edit', teacher: row })}
          />
          <RowAction icon="table-list" label="Assign subjects" onClick={() => setSubjectsFor(row)} />
          <RowAction
            icon="paper-plane"
            label="Resend login credentials"
            onClick={() => setResending(row)}
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
        title="Teachers"
        description="Manage teaching staff and the subjects they are responsible for."
        actions={
          <Button icon="plus" onClick={() => setFormState({ mode: 'create', teacher: null })}>
            Add teacher
          </Button>
        }
      />

      {error && (
        <Alert tone="danger" className="mb-5">
          {error}
        </Alert>
      )}

      <Card>
        <div className="border-ink-200 flex flex-wrap items-center gap-3 border-b px-5 py-4">
          <SearchInput
            value={search}
            onChange={(value) => {
              setSearch(value)
              setPage(1)
            }}
            placeholder="Search by name, employee number or email"
            className="min-w-[16rem] flex-1"
          />
          <label className="text-ink-600 flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => {
                setShowInactive(event.target.checked)
                setPage(1)
              }}
              className="accent-brand-600 size-4"
            />
            Show inactive
          </label>
        </div>

        <DataTable
          columns={columns}
          rows={data?.items ?? []}
          loading={loading && !data}
          empty={
            <EmptyState
              icon="users"
              title={search ? 'No teachers match that search' : 'No teachers yet'}
              description={
                search
                  ? 'Try a different name or employee number.'
                  : 'Add teaching staff so results can be assigned to them.'
              }
              action={
                !search && (
                  <Button icon="plus" onClick={() => setFormState({ mode: 'create', teacher: null })}>
                    Add teacher
                  </Button>
                )
              }
            />
          }
        />

        <Pagination page={page} pageSize={PAGE_SIZE} total={data?.total ?? 0} onPageChange={setPage} />
      </Card>

      {formState && (
        <TeacherFormModal
          open
          mode={formState.mode}
          teacher={formState.teacher}
          subjects={subjects ?? []}
          onClose={() => setFormState(null)}
          onSaved={(message) => {
            setFormState(null)
            show(message)
            refresh()
          }}
        />
      )}

      {subjectsFor && (
        <TeacherSubjectsModal
          open
          teacher={subjectsFor}
          subjects={subjects ?? []}
          onClose={() => setSubjectsFor(null)}
          onSaved={(message) => {
            setSubjectsFor(null)
            show(message)
            refresh()
          }}
        />
      )}

      <ConfirmDialog
        open={Boolean(resending)}
        onClose={() => setResending(null)}
        onConfirm={() => resendCredentials(resending)}
        title="Resend login credentials?"
        message={`A new temporary password will be generated and emailed to ${resending?.email}.`}
        detail={
          `This replaces the password ${resending?.full_name} has now. Their current ` +
          `password stops working immediately and they will be signed out of any ` +
          `session. Nobody sees the new password but them.`
        }
        confirmLabel="Generate and send"
        icon="paper-plane"
      />

      <ConfirmDialog
        open={Boolean(confirming)}
        onClose={() => setConfirming(null)}
        onConfirm={() => toggleActive(confirming)}
        title={confirming?.is_active ? 'Deactivate this teacher?' : 'Reactivate this teacher?'}
        message={
          confirming?.is_active
            ? `${confirming?.full_name} will no longer be able to sign in or upload results. Results they have already submitted are kept.`
            : `${confirming?.full_name} will be able to sign in again.`
        }
        confirmLabel={confirming?.is_active ? 'Deactivate' : 'Reactivate'}
        variant={confirming?.is_active ? 'danger' : 'primary'}
        icon={confirming?.is_active ? 'ban' : 'circle-check'}
      />

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default TeachersPage
