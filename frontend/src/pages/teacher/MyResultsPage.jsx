import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

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
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { teacherDownloads, teacherPortalService } from '@/services/teacherService'
import { getErrorMessage } from '@/services/apiClient'
import { statusLabel } from '@/utils/constants'
import { cx } from '@/utils/format'

/**
 * The marks this teacher has recorded, subject by subject.
 *
 * Read-only on purpose: this is the page for checking what is on record.
 * Changing a mark happens under Upload Results, where the reason for the
 * change is captured for the audit trail.
 */
export function MyResultsPage() {
  useDocumentTitle('My Results')

  const [subjectKey, setSubjectKey] = useState('')
  const [busy, setBusy] = useState(null)
  const { toast, show, clear } = useToast()

  const dashboard = useAsyncData(() => teacherPortalService.dashboard(), [])
  const cards = useMemo(() => dashboard.data?.subjects ?? [], [dashboard.data])

  // Open on a subject that already has marks, derived during render rather than
  // assigned from an effect, so the first paint is already correct.
  const effectiveKey = useMemo(() => {
    if (subjectKey) return subjectKey
    const first = cards.find((c) => c.submitted_count > 0) ?? cards[0]
    return first ? `${first.examination_id}:${first.subject_id}` : ''
  }, [cards, subjectKey])

  const selected = useMemo(
    () => cards.find((c) => `${c.examination_id}:${c.subject_id}` === effectiveKey) ?? null,
    [cards, effectiveKey],
  )

  const sheet = useAsyncData(
    () =>
      selected
        ? teacherPortalService.markSheet(selected.examination_id, selected.subject_id)
        : Promise.resolve(null),
    [selected?.examination_id, selected?.subject_id],
  )

  const rows = sheet.data?.rows ?? []
  const marked = rows.filter((r) => r.marks !== null && r.marks !== undefined)

  const average = marked.length
    ? (marked.reduce((sum, r) => sum + Number(r.marks), 0) / marked.length).toFixed(1)
    : null

  async function download(kind) {
    setBusy(kind)
    try {
      const name = await (kind === 'csv'
        ? teacherDownloads.csv(selected.examination_id, selected.subject_id, selected.subject_code)
        : teacherDownloads.pdf(selected.examination_id, selected.subject_id, selected.subject_code))
      show(`Downloaded ${name}`)
    } catch (err) {
      show(getErrorMessage(err, 'That download did not work.'), 'danger')
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
          <p className="text-ink-900 font-medium">{row.student_name}</p>
          <p className="text-ink-400 font-mono text-xs">{row.student_number}</p>
        </div>
      ),
    },
    {
      key: 'marks',
      header: 'Mark',
      align: 'right',
      render: (row) =>
        row.marks === null || row.marks === undefined ? (
          <span className="text-ink-300">—</span>
        ) : (
          <span className="text-ink-900 font-semibold tabular-nums">{row.marks}</span>
        ),
    },
    {
      key: 'grade',
      header: 'Grade',
      align: 'right',
      render: (row) =>
        row.grade ? (
          <Badge tone="neutral">{row.grade}</Badge>
        ) : (
          <span className="text-ink-300">—</span>
        ),
    },
    {
      key: 'remarks',
      header: 'Remarks',
      render: (row) =>
        row.remarks ? (
          <span className="text-ink-600">{row.remarks}</span>
        ) : (
          <span className="text-ink-300">—</span>
        ),
    },
  ]

  if (dashboard.loading && !dashboard.data) return <PageLoader label="Loading your results" />

  return (
    <div>
      <PageHeader
        title="My Results"
        description="The marks on record for each of your subjects."
        actions={
          selected && (
            <>
              <Button
                variant="secondary"
                icon="file-csv"
                loading={busy === 'csv'}
                onClick={() => download('csv')}
              >
                CSV
              </Button>
              <Button
                variant="secondary"
                icon="file-pdf"
                loading={busy === 'pdf'}
                onClick={() => download('pdf')}
              >
                PDF
              </Button>
            </>
          )
        }
      />

      {(dashboard.error || sheet.error) && (
        <Alert tone="danger" title="Could not load your results" className="mb-5">
          {dashboard.error || sheet.error}
        </Alert>
      )}

      {cards.length === 0 ? (
        <Card>
          <CardBody className="p-0">
            <EmptyState
              icon="table-list"
              title="No subjects assigned to you"
              description="The school office assigns subjects to teachers. Contact them if this looks wrong."
            />
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-5">
          <Card>
            <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <Select
                label="Subject"
                value={effectiveKey}
                onChange={(e) => setSubjectKey(e.target.value)}
                options={cards.map((c) => ({
                  value: `${c.examination_id}:${c.subject_id}`,
                  label: `${c.subject_name} · ${c.examination_name}`,
                }))}
                className="sm:max-w-md"
              />
              {selected && (
                <div className="flex flex-wrap items-center gap-2 pb-0.5">
                  <Badge status={selected.status}>{statusLabel(selected.status)}</Badge>
                  <span className="text-ink-500 text-sm">
                    {selected.submitted_count} of {selected.expected_count} marked
                  </span>
                </div>
              )}
            </CardBody>
          </Card>

          {selected && marked.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-3">
              {[
                { label: 'Students', value: rows.length, hint: 'On the roll' },
                { label: 'Marked', value: marked.length, hint: `${rows.length - marked.length} still blank` },
                { label: 'Class average', value: average ?? '—', hint: 'Of the marks recorded' },
              ].map((tile) => (
                <Card key={tile.label}>
                  <CardBody>
                    <p className="text-ink-500 text-sm">{tile.label}</p>
                    <p className="text-ink-900 mt-1 text-2xl font-semibold tabular-nums">
                      {tile.value}
                    </p>
                    <p className="text-ink-400 mt-0.5 text-xs">{tile.hint}</p>
                  </CardBody>
                </Card>
              ))}
            </div>
          )}

          <Card>
            <CardHeader
              icon="table-list"
              title={selected ? selected.subject_name : 'Results'}
              description={
                selected
                  ? `${selected.examination_name}${selected.term_name ? ` · ${selected.term_name}` : ''}`
                  : undefined
              }
              action={
                selected && (
                  <Button
                    as={Link}
                    to={`/teacher/examinations/${selected.examination_id}/subjects/${selected.subject_id}`}
                    variant="secondary"
                    size="sm"
                    icon="pen-to-square"
                  >
                    Edit marks
                  </Button>
                )
              }
            />
            <DataTable
              columns={columns}
              rows={rows}
              rowKey={(row) => row.student_id}
              loading={sheet.loading && !sheet.data}
              empty={
                <EmptyState
                  icon="inbox"
                  title="No students on this roll"
                  description="Nobody is enrolled in this subject for this examination yet."
                />
              }
            />
            {rows.length > 0 && marked.length === 0 && (
              <div
                className={cx(
                  'border-ink-200 border-t px-5 py-3 text-sm',
                  'text-ink-500 bg-ink-50/60',
                )}
              >
                No marks recorded yet for this subject.
              </div>
            )}
          </Card>
        </div>
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default MyResultsPage
