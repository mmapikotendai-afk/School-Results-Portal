import { useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import EditResultModal from '@/components/admin/EditResultModal'
import ResultAuditModal from '@/components/admin/ResultAuditModal'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  DataTable,
  Pagination,
  RowAction,
  SearchInput,
  Select,
  Spinner,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDebounced from '@/hooks/useDebounced'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { adminDownloads } from '@/services/adminDownloads'
import { academicService, resultsService, studentService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'
import { statusLabel } from '@/utils/constants'

const PAGE_SIZE = 10

/**
 * Results management.
 *
 * Follows the path an administrator actually takes: find the student, open
 * their history, narrow to a term or examination, then act on one mark.
 */
export function ResultsPage() {
  useDocumentTitle('Results')

  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const debounced = useDebounced(search, 350)

  const [selected, setSelected] = useState(null)
  const [yearId, setYearId] = useState('')
  const [termId, setTermId] = useState('')
  const [examId, setExamId] = useState('')

  const [editing, setEditing] = useState(null)
  const [auditing, setAuditing] = useState(null)
  const [busy, setBusy] = useState(null)
  const { toast, show, clear } = useToast()

  const listQuery = useMemo(
    () => ({ search: debounced || undefined, page, page_size: PAGE_SIZE }),
    [debounced, page],
  )
  const students = useAsyncData(() => studentService.list(listQuery), [listQuery])
  const { data: years } = useAsyncData(() => academicService.listYears(), [])
  const { data: terms } = useAsyncData(() => academicService.listTerms(), [])
  const { data: exams } = useAsyncData(() => academicService.listExaminations(), [])

  const filters = useMemo(
    () => ({
      academic_year_id: yearId || undefined,
      term_id: termId || undefined,
      examination_id: examId || undefined,
    }),
    [yearId, termId, examId],
  )

  const history = useAsyncData(
    () => (selected ? resultsService.studentResults(selected.id, filters) : Promise.resolve([])),
    [selected?.id, filters],
  )

  async function download(kind, entry) {
    const key = `${kind}-${entry.examination_id}`
    setBusy(key)
    try {
      const name =
        kind === 'csv'
          ? await adminDownloads.studentResultsCsv(selected.id, entry.examination_id)
          : await adminDownloads.reportCard(selected.id, entry.examination_id)
      show(`Downloaded ${name}`)
    } catch (err) {
      show(getErrorMessage(err, 'That download did not work.'), 'danger')
    } finally {
      setBusy(null)
    }
  }

  const columns = [
    {
      key: 'student_number',
      header: 'Student number',
      render: (row) => (
        <span className="text-ink-900 font-mono text-xs font-semibold">
          {row.student_number}
        </span>
      ),
    },
    {
      key: 'full_name',
      header: 'Name',
      render: (row) => <span className="text-ink-900 font-medium">{row.full_name}</span>,
    },
    {
      key: 'class',
      header: 'Class',
      render: (row) => row.school_class?.name ?? <span className="text-ink-400">—</span>,
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) => (
        <RowAction
          icon="arrow-right"
          label="View results"
          tone="brand"
          onClick={() => setSelected(row)}
        />
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Results"
        description="Find a student, review their record, and correct a mark where necessary."
        actions={
          selected && (
            <Button variant="secondary" size="sm" onClick={() => setSelected(null)}>
              Back to students
            </Button>
          )
        }
      />

      {!selected ? (
        <Card>
          <div className="border-ink-200 border-b px-5 py-4">
            <SearchInput
              value={search}
              onChange={(v) => {
                setSearch(v)
                setPage(1)
              }}
              placeholder="Search by name, student number or email"
              className="max-w-md"
            />
          </div>

          {students.error && (
            <Alert tone="danger" className="m-5">
              {students.error}
            </Alert>
          )}

          <DataTable
            columns={columns}
            rows={students.data?.items ?? []}
            loading={students.loading && !students.data}
            onRowClick={setSelected}
            empty={
              <EmptyState
                icon="user-graduate"
                title={search ? 'No students match that search' : 'No students yet'}
                description={
                  search
                    ? 'Try a different name or student number.'
                    : 'Add students before reviewing results.'
                }
              />
            }
          />
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={students.data?.total ?? 0}
            onPageChange={setPage}
          />
        </Card>
      ) : (
        <div className="space-y-5">
          {/* Who we are looking at */}
          <Card>
            <CardBody>
              <div className="flex flex-wrap items-center gap-x-10 gap-y-3">
                <div>
                  <p className="text-ink-400 text-xs font-semibold tracking-wide uppercase">
                    Student
                  </p>
                  <p className="text-ink-900 font-serif text-lg font-semibold">
                    {selected.full_name}
                  </p>
                </div>
                <div>
                  <p className="text-ink-400 text-xs font-semibold tracking-wide uppercase">
                    Student number
                  </p>
                  <p className="text-ink-900 font-mono text-sm font-semibold">
                    {selected.student_number}
                  </p>
                </div>
                <div>
                  <p className="text-ink-400 text-xs font-semibold tracking-wide uppercase">
                    Class
                  </p>
                  <p className="text-ink-900 text-sm font-semibold">
                    {selected.school_class?.name ?? 'Not assigned'}
                  </p>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Filters */}
          <Card>
            <div className="flex flex-wrap items-end gap-3 px-5 py-4">
              <Select
                label="Academic year"
                value={yearId}
                onChange={(e) => {
                  setYearId(e.target.value)
                  setTermId('')
                  setExamId('')
                }}
                placeholder="All years"
                className="w-auto min-w-[10rem]"
                options={(years ?? []).map((y) => ({ value: y.id, label: y.name }))}
              />
              <Select
                label="Term"
                value={termId}
                onChange={(e) => {
                  setTermId(e.target.value)
                  setExamId('')
                }}
                placeholder="All terms"
                className="w-auto min-w-[10rem]"
                options={(terms ?? [])
                  .filter((t) => !yearId || String(t.academic_year_id) === String(yearId))
                  .map((t) => ({ value: t.id, label: t.name }))}
              />
              <Select
                label="Examination"
                value={examId}
                onChange={(e) => setExamId(e.target.value)}
                placeholder="All examinations"
                className="w-auto min-w-[14rem]"
                options={(exams ?? [])
                  .filter((x) => !termId || String(x.term_id) === String(termId))
                  .map((x) => ({ value: x.id, label: x.name }))}
              />
              {(yearId || termId || examId) && (
                <button
                  type="button"
                  onClick={() => {
                    setYearId('')
                    setTermId('')
                    setExamId('')
                  }}
                  className="text-ink-500 hover:text-ink-800 pb-2.5 text-sm underline"
                >
                  Clear filters
                </button>
              )}
            </div>
          </Card>

          {history.error && <Alert tone="danger">{history.error}</Alert>}

          {history.loading && !history.data ? (
            <div className="flex items-center justify-center gap-3 py-12">
              <Spinner />
              <span className="text-ink-500 text-sm">Loading results…</span>
            </div>
          ) : history.data?.length ? (
            history.data.map((entry) => {
              const record = entry.students[0]
              return (
                <Card key={entry.examination_id}>
                  <div className="border-ink-200 flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4">
                    <div className="min-w-0">
                      <h3 className="text-base font-semibold">{entry.examination_name}</h3>
                      <p className="text-ink-500 mt-0.5 text-sm">
                        {entry.term_name}
                        {entry.academic_year_name ? ` · ${entry.academic_year_name}` : ''}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-3">
                        <Badge status={entry.status}>{statusLabel(entry.status)}</Badge>
                        <span className="text-ink-500 text-sm">
                          average {record.average} · position {record.position ?? '—'} of{' '}
                          {record.ranked_out_of ?? '—'} in {entry.class_name}
                        </span>
                        {!record.is_complete && (
                          <span className="text-warning-700 text-xs font-semibold">
                            {record.subjects_marked} of {record.subjects_enrolled} subjects
                            marked
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        icon="file-csv"
                        loading={busy === `csv-${entry.examination_id}`}
                        onClick={() => download('csv', entry)}
                      >
                        CSV
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        icon="file-pdf"
                        loading={busy === `pdf-${entry.examination_id}`}
                        onClick={() => download('pdf', entry)}
                      >
                        Report card
                      </Button>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[34rem] border-collapse text-sm">
                      <thead>
                        <tr className="border-ink-200 border-b">
                          <th scope="col" className="text-ink-500 px-5 py-2.5 text-left text-xs font-semibold uppercase">
                            Subject
                          </th>
                          <th scope="col" className="text-ink-500 px-5 py-2.5 text-right text-xs font-semibold uppercase">
                            Marks
                          </th>
                          <th scope="col" className="text-ink-500 px-5 py-2.5 text-right text-xs font-semibold uppercase">
                            Grade
                          </th>
                          <th scope="col" className="text-ink-500 px-5 py-2.5 text-left text-xs font-semibold uppercase">
                            Remarks
                          </th>
                          <th scope="col" className="px-5 py-2.5" aria-label="Actions" />
                        </tr>
                      </thead>
                      <tbody className="divide-ink-100 divide-y">
                        {record.subjects.map((sub) => (
                          <tr key={sub.result_id}>
                            <td className="px-5 py-3">
                              <p className="text-ink-900 font-medium">{sub.subject_name}</p>
                              <p className="text-ink-400 font-mono text-xs">
                                {sub.subject_code}
                              </p>
                            </td>
                            <td className="text-ink-900 px-5 py-3 text-right font-semibold tabular-nums">
                              {Number(sub.marks).toFixed(0)}
                            </td>
                            <td className="px-5 py-3 text-right">
                              <Badge tone="brand">{sub.grade ?? '—'}</Badge>
                            </td>
                            <td className="text-ink-600 px-5 py-3">{sub.remarks ?? '—'}</td>
                            <td className="px-5 py-3 text-right">
                              <div className="flex items-center justify-end gap-0.5">
                                <RowAction
                                  icon="clock"
                                  label="View history"
                                  onClick={() => setAuditing(sub.result_id)}
                                />
                                <RowAction
                                  icon="pen-to-square"
                                  label="Correct this mark"
                                  tone="brand"
                                  onClick={() =>
                                    setEditing({
                                      subject: sub,
                                      student: record,
                                      examination: entry.examination_name,
                                    })
                                  }
                                />
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {entry.status === 'PUBLISHED' && (
                    <p className="border-ink-200 text-ink-400 flex items-start gap-2 border-t px-5 py-2.5 text-xs">
                      <FontAwesomeIcon icon="circle-info" className="mt-0.5" aria-hidden="true" />
                      These results are published. A correction here changes what the
                      student sees.
                    </p>
                  )}
                </Card>
              )
            })
          ) : (
            <Card>
              <CardBody className="p-0">
                <EmptyState
                  icon="file-lines"
                  title="No results for these filters"
                  description={
                    yearId || termId || examId
                      ? 'Try widening the filters, or clear them to see the whole record.'
                      : 'This student has no results recorded yet.'
                  }
                />
              </CardBody>
            </Card>
          )}
        </div>
      )}

      {editing && (
        <EditResultModal
          open
          subject={editing.subject}
          student={editing.student}
          examination={editing.examination}
          onClose={() => setEditing(null)}
          onSaved={(message) => {
            setEditing(null)
            show(message)
            history.refresh()
          }}
        />
      )}

      {auditing && (
        <ResultAuditModal open resultId={auditing} onClose={() => setAuditing(null)} />
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default ResultsPage
