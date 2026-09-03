import { useMemo, useState } from 'react'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  DataTable,
  PageLoader,
  SearchInput,
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDebounced from '@/hooks/useDebounced'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { academicService, studentService } from '@/services/adminService'
import { adminDownloads } from '@/services/adminDownloads'
import { getErrorMessage } from '@/services/apiClient'
import { statusLabel } from '@/utils/constants'

/**
 * Reports and exports.
 *
 * Everything here is generated from the database at the moment you ask for it,
 * never from a file somebody uploaded earlier - so a mark corrected through the
 * portal appears in the very next download.
 */
export function ReportsPage() {
  useDocumentTitle('Reports')

  const [examId, setExamId] = useState('')
  const [search, setSearch] = useState('')
  const [busy, setBusy] = useState(null)
  const { toast, show, clear } = useToast()

  const debouncedSearch = useDebounced(search, 300)

  const exams = useAsyncData(() => academicService.listExaminations(), [])
  const examList = useMemo(() => exams.data ?? [], [exams.data])

  // Default to a published examination, derived rather than assigned from an
  // effect, so the first render already shows the right selection.
  const effectiveExamId =
    examId ||
    String((examList.find((e) => e.status === 'PUBLISHED') ?? examList[0])?.id ?? '')

  const students = useAsyncData(
    () => studentService.list({ search: debouncedSearch || undefined, page_size: 25 }),
    [debouncedSearch],
  )

  const exam = examList.find((e) => String(e.id) === String(effectiveExamId))
  const rows = students.data?.items ?? []

  /** Wrap a download so every button gets the same busy, success and error handling. */
  async function run(key, task, successMessage) {
    setBusy(key)
    try {
      const filename = await task()
      show(successMessage ?? `Downloaded ${filename}`)
    } catch (err) {
      show(getErrorMessage(err), 'danger')
    } finally {
      setBusy(null)
    }
  }

  const columns = [
    {
      key: 'student',
      header: 'Student',
      render: (row) => (
        <div className="min-w-0">
          <p className="text-ink-900 font-medium">{row.full_name}</p>
          <p className="text-ink-400 font-mono text-xs">{row.student_number}</p>
        </div>
      ),
    },
    {
      key: 'class_name',
      header: 'Class',
      render: (row) => row.class_name ?? <span className="text-ink-400">Unassigned</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) =>
        row.is_active ? (
          <Badge tone="success">Active</Badge>
        ) : (
          <Badge tone="neutral">Inactive</Badge>
        ),
    },
    {
      key: 'downloads',
      header: 'Download',
      align: 'right',
      render: (row) => (
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon="file-pdf"
            disabled={!effectiveExamId}
            loading={busy === `pdf-${row.id}`}
            onClick={() =>
              run(
                `pdf-${row.id}`,
                () =>
                  adminDownloads.reportCard(
                    row.id,
                    Number(effectiveExamId),
                    `${row.student_number}-report-card`,
                  ),
                `Report card for ${row.full_name} downloaded.`,
              )
            }
          >
            Report card
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon="file-csv"
            disabled={!effectiveExamId}
            loading={busy === `csv-${row.id}`}
            onClick={() =>
              run(`csv-${row.id}`, () =>
                adminDownloads.studentResultsCsv(
                  row.id,
                  Number(effectiveExamId),
                  `${row.student_number}-results`,
                ),
              )
            }
          >
            CSV
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon="clock-rotate-left"
            loading={busy === `hist-${row.id}`}
            onClick={() =>
              run(`hist-${row.id}`, () =>
                adminDownloads.studentHistoryCsv(row.id, `${row.student_number}-history`),
              )
            }
          >
            History
          </Button>
        </div>
      ),
    },
  ]

  if (exams.loading && !exams.data) return <PageLoader label="Loading examinations" />

  return (
    <div>
      <PageHeader
        title="Reports"
        description="Official report cards and result exports, generated from the live record."
      />

      {(exams.error || students.error) && (
        <Alert tone="danger" title="Could not load reports" className="mb-5">
          {exams.error || students.error}
        </Alert>
      )}

      {examList.length === 0 ? (
        <Card>
          <CardBody className="p-0">
            <EmptyState
              icon="file-pdf"
              title="No examinations yet"
              description="Report cards are generated per examination. Create one first."
            />
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-5">
          <Card>
            <CardHeader
              icon="file-lines"
              title="Choose an examination"
              description="Report cards and per-examination exports are drawn from this one."
            />
            <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <Select
                label="Examination"
                value={effectiveExamId}
                onChange={(e) => setExamId(e.target.value)}
                options={examList.map((e) => ({
                  value: e.id,
                  label: `${e.name}${e.term_name ? ` · ${e.term_name}` : ''}`,
                }))}
                className="sm:max-w-md"
              />
              <div className="flex flex-wrap items-center gap-2 pb-0.5">
                {exam && <Badge status={exam.status}>{statusLabel(exam.status)}</Badge>}
                <Button
                  variant="secondary"
                  icon="file-csv"
                  disabled={!effectiveExamId}
                  loading={busy === 'exam-csv'}
                  onClick={() =>
                    run(
                      'exam-csv',
                      () =>
                        adminDownloads.examinationCsv(
                          Number(effectiveExamId),
                          `${exam?.name ?? 'examination'}-results`,
                        ),
                      'Full examination export downloaded.',
                    )
                  }
                >
                  Export whole examination
                </Button>
              </div>
            </CardBody>
          </Card>

          {exam && exam.status !== 'PUBLISHED' && (
            <Alert tone="warning" title="This examination is not published">
              You can still generate report cards for it. They are watermarked
              PROVISIONAL, and students cannot see these results yet.
            </Alert>
          )}

          <Card>
            <CardHeader
              icon="user-graduate"
              title="Individual report cards"
              description="Search for a student, then download their report card or results."
              action={
                <SearchInput
                  value={search}
                  onChange={setSearch}
                  placeholder="Name or student number"
                  className="w-full sm:w-64"
                />
              }
            />
            <DataTable
              columns={columns}
              rows={rows}
              loading={students.loading && !students.data}
              empty={
                <EmptyState
                  icon={search ? 'magnifying-glass' : 'user-graduate'}
                  title={search ? 'No students match that search' : 'No students yet'}
                  description={
                    search
                      ? 'Check the spelling, or search by student number instead.'
                      : 'Add students before generating report cards.'
                  }
                  action={
                    search && (
                      <Button variant="secondary" icon="xmark" onClick={() => setSearch('')}>
                        Clear search
                      </Button>
                    )
                  }
                />
              }
            />
            {rows.length > 0 && students.data?.total > rows.length && (
              <div className="border-ink-200 text-ink-500 border-t px-5 py-3 text-sm">
                Showing {rows.length} of {students.data.total}. Narrow the search to find a
                particular student.
              </div>
            )}
          </Card>
        </div>
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default ReportsPage
