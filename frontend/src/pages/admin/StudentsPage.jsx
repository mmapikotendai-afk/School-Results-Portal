import { useCallback, useMemo, useState } from 'react'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import StudentFormModal from '@/components/admin/StudentFormModal'
import StudentSubjectsModal from '@/components/admin/StudentSubjectsModal'
import StudentViewModal from '@/components/admin/StudentViewModal'
import Toast from '@/components/common/Toast'
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
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDebounced from '@/hooks/useDebounced'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { classService, studentService, subjectService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

const PAGE_SIZE = 15

export function StudentsPage() {
  useDocumentTitle('Students')

  const [search, setSearch] = useState('')
  const [classId, setClassId] = useState('')
  const [showInactive, setShowInactive] = useState(true)
  const [page, setPage] = useState(1)

  // One request when typing pauses, rather than one per keystroke.
  const debouncedSearch = useDebounced(search, 350)

  const [formState, setFormState] = useState(null) // { mode, student }
  const [subjectsFor, setSubjectsFor] = useState(null)
  const [viewing, setViewing] = useState(null)
  const [confirming, setConfirming] = useState(null)
  const { toast, show, clear } = useToast()

  const query = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      class_id: classId || undefined,
      include_inactive: showInactive,
      page,
      page_size: PAGE_SIZE,
    }),
    [debouncedSearch, classId, showInactive, page],
  )

  const { data, loading, error, refresh } = useAsyncData(
    () => studentService.list(query),
    [query],
  )
  const { data: classes } = useAsyncData(() => classService.list(), [])
  const { data: subjects } = useAsyncData(() => subjectService.list({ include_inactive: false }), [])

  // Any filter change invalidates the current page number.
  const resetTo = useCallback((setter) => (value) => {
    setter(value)
    setPage(1)
  }, [])

  async function toggleActive(student) {
    try {
      await studentService.setStatus(student.id, !student.is_active)
      show(
        student.is_active
          ? `${student.full_name} has been deactivated.`
          : `${student.full_name} has been reactivated.`,
      )
      refresh()
    } catch (err) {
      show(getErrorMessage(err), 'danger')
      throw err
    }
  }

  const columns = [
    {
      key: 'student_number',
      header: 'Student number',
      render: (row) => (
        <span className="text-ink-900 font-mono text-xs font-semibold">{row.student_number}</span>
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
      key: 'class',
      header: 'Class',
      render: (row) =>
        row.school_class ? (
          <div>
            <p className="text-ink-800">{row.school_class.name}</p>
            <p className="text-ink-400 text-xs">
              {row.school_class.level === 'O_LEVEL' ? 'O-Level' : 'A-Level'}
            </p>
          </div>
        ) : (
          <span className="text-ink-400">Unassigned</span>
        ),
    },
    {
      key: 'subject_count',
      header: 'Subjects',
      render: (row) => (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation()
            setSubjectsFor(row)
          }}
          className="text-brand-700 hover:bg-brand-50 rounded-lg px-2 py-1 text-sm font-medium transition-colors"
        >
          {row.subject_count} enrolled
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
          <RowAction icon="eye" label="View" onClick={() => setViewing(row)} />
          <RowAction
            icon="pen-to-square"
            label="Edit"
            tone="brand"
            onClick={() => setFormState({ mode: 'edit', student: row })}
          />
          <RowAction
            icon="table-list"
            label="Manage subjects"
            onClick={() => setSubjectsFor(row)}
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
        title="Students"
        description="Add learners, keep their records current and manage what they study."
        actions={
          <Button icon="plus" onClick={() => setFormState({ mode: 'create', student: null })}>
            Add student
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
            onChange={resetTo(setSearch)}
            placeholder="Search by name, student number or email"
            className="min-w-[16rem] flex-1"
          />
          <Select
            value={classId}
            onChange={(event) => resetTo(setClassId)(event.target.value)}
            placeholder="All classes"
            className="w-auto min-w-[12rem]"
            options={(classes ?? []).map((c) => ({ value: c.id, label: c.name }))}
          />
          <label className="text-ink-600 flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => resetTo(setShowInactive)(event.target.checked)}
              className="accent-brand-600 size-4"
            />
            Show inactive
          </label>
        </div>

        <DataTable
          columns={columns}
          rows={data?.items ?? []}
          loading={loading && !data}
          onRowClick={(row) => setViewing(row)}
          empty={
            <EmptyState
              icon="user-graduate"
              title={search || classId ? 'No students match those filters' : 'No students yet'}
              description={
                search || classId
                  ? 'Try a different name, student number or class.'
                  : 'Add your first learner to get started.'
              }
              action={
                !search &&
                !classId && (
                  <Button icon="plus" onClick={() => setFormState({ mode: 'create', student: null })}>
                    Add student
                  </Button>
                )
              }
            />
          }
        />

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={data?.total ?? 0}
          onPageChange={setPage}
        />
      </Card>

      {formState && (
        <StudentFormModal
          open
          mode={formState.mode}
          student={formState.student}
          classes={classes ?? []}
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
        <StudentSubjectsModal
          open
          student={subjectsFor}
          subjects={subjects ?? []}
          onClose={() => setSubjectsFor(null)}
          onSaved={(message) => {
            setSubjectsFor(null)
            show(message)
            refresh()
          }}
        />
      )}

      {viewing && (
        <StudentViewModal
          open
          studentId={viewing.id}
          onClose={() => setViewing(null)}
          onEdit={(student) => {
            setViewing(null)
            setFormState({ mode: 'edit', student })
          }}
          onManageSubjects={(student) => {
            setViewing(null)
            setSubjectsFor(student)
          }}
        />
      )}

      <ConfirmDialog
        open={Boolean(confirming)}
        onClose={() => setConfirming(null)}
        onConfirm={() => toggleActive(confirming)}
        title={confirming?.is_active ? 'Deactivate this student?' : 'Reactivate this student?'}
        message={
          confirming?.is_active
            ? `${confirming?.full_name} will no longer be able to sign in. Their record, enrollment history and results are all kept.`
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

export default StudentsPage
