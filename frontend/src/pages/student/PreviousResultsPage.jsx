import { useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  PageLoader,
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import studentResultsService, { studentDownloads } from '@/services/studentService'
import { getErrorMessage } from '@/services/apiClient'
import { formatDate } from '@/utils/format'

/**
 * Every examination this student has sat, oldest terms included.
 *
 * Results published earlier stay available for good - a new term never hides
 * an old report. Examinations that have not been published yet are listed by
 * name only, with no marks, so the student can see that something is coming
 * without seeing it early.
 */
export function PreviousResultsPage() {
  useDocumentTitle('Previous Results')

  const [yearFilter, setYearFilter] = useState('')
  const [openId, setOpenId] = useState(null)
  const [busy, setBusy] = useState(null)
  const { toast, show, clear } = useToast()

  const history = useAsyncData(() => studentResultsService.history(), [])
  const entries = useMemo(() => history.data?.entries ?? [], [history.data])

  const years = useMemo(
    () => [...new Set(entries.map((e) => e.academic_year_name).filter(Boolean))],
    [entries],
  )

  const visible = useMemo(
    () => (yearFilter ? entries.filter((e) => e.academic_year_name === yearFilter) : entries),
    [entries, yearFilter],
  )

  const detail = useAsyncData(
    () => (openId ? studentResultsService.examination(openId) : Promise.resolve(null)),
    [openId],
  )

  async function download(kind, entry) {
    setBusy(`${kind}-${entry.examination_id}`)
    try {
      const name = await (kind === 'csv'
        ? studentDownloads.csv(entry.examination_id, entry.examination_name)
        : studentDownloads.pdf(entry.examination_id, entry.examination_name))
      show(`Downloaded ${name}`)
    } catch (err) {
      show(getErrorMessage(err, 'That download did not work.'), 'danger')
    } finally {
      setBusy(null)
    }
  }

  if (history.loading && !history.data) return <PageLoader label="Loading your results" />

  const publishedCount = entries.filter((e) => e.is_published).length

  return (
    <div>
      <PageHeader
        title="Previous Results"
        description="Every examination you have sat. Published results stay here permanently."
      />

      {history.error && (
        <Alert tone="danger" title="Could not load your results" className="mb-5">
          {history.error}
        </Alert>
      )}

      {entries.length === 0 ? (
        <Card>
          <CardBody className="p-0">
            <EmptyState
              icon="clock-rotate-left"
              title="No results yet"
              description="Once your school publishes an examination, it will appear here and stay available."
            />
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-5">
          {years.length > 1 && (
            <Card>
              <CardBody className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <Select
                  label="Academic year"
                  value={yearFilter}
                  onChange={(e) => setYearFilter(e.target.value)}
                  placeholder="All years"
                  options={years.map((y) => ({ value: y, label: y }))}
                  className="sm:max-w-xs"
                />
                <p className="text-ink-500 pb-2.5 text-sm">
                  {publishedCount} published of {entries.length}
                </p>
              </CardBody>
            </Card>
          )}

          <ol className="space-y-4">
            {visible.map((entry) => {
              const isOpen = openId === entry.examination_id
              return (
                <li key={entry.examination_id}>
                  <Card>
                    <div className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-base font-semibold">{entry.examination_name}</h3>
                          {entry.is_published ? (
                            <Badge tone="success">Published</Badge>
                          ) : (
                            <Badge tone="neutral">Not yet released</Badge>
                          )}
                        </div>
                        <p className="text-ink-500 mt-1 text-sm">
                          {[entry.term_name, entry.academic_year_name]
                            .filter(Boolean)
                            .join(' · ')}
                          {entry.published_at
                            ? ` · Released ${formatDate(entry.published_at)}`
                            : ''}
                        </p>
                      </div>

                      {entry.is_published ? (
                        <div className="flex flex-wrap items-center gap-2">
                          {entry.average !== null && entry.average !== undefined && (
                            <div className="mr-2 text-right">
                              <p className="text-ink-900 text-lg font-semibold tabular-nums">
                                {entry.average}
                              </p>
                              <p className="text-ink-400 text-xs">Average</p>
                            </div>
                          )}
                          <Button
                            variant="secondary"
                            size="sm"
                            icon={isOpen ? 'chevron-down' : 'angle-right'}
                            onClick={() => setOpenId(isOpen ? null : entry.examination_id)}
                            aria-expanded={isOpen}
                          >
                            {isOpen ? 'Hide' : 'View'}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            icon="file-pdf"
                            loading={busy === `pdf-${entry.examination_id}`}
                            onClick={() => download('pdf', entry)}
                          >
                            PDF
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            icon="file-csv"
                            loading={busy === `csv-${entry.examination_id}`}
                            onClick={() => download('csv', entry)}
                          >
                            CSV
                          </Button>
                        </div>
                      ) : (
                        <p className="text-ink-500 flex items-center gap-2 text-sm">
                          <FontAwesomeIcon icon="clock" aria-hidden="true" />
                          Results are not available yet
                        </p>
                      )}
                    </div>

                    {isOpen && (
                      <div className="border-ink-200 border-t">
                        {detail.loading && !detail.data ? (
                          <div className="text-ink-500 flex items-center justify-center gap-3 py-10 text-sm">
                            <FontAwesomeIcon icon="spinner" className="animate-spin" />
                            Loading results…
                          </div>
                        ) : detail.error ? (
                          <div className="p-5">
                            <Alert tone="danger">{detail.error}</Alert>
                          </div>
                        ) : (
                          <div className="overflow-x-auto">
                            <table className="w-full min-w-[32rem] text-sm">
                              <thead>
                                <tr className="border-ink-200 text-ink-500 border-b text-left text-xs uppercase">
                                  <th scope="col" className="px-5 py-2.5 font-semibold">Subject</th>
                                  <th scope="col" className="px-5 py-2.5 text-right font-semibold">Mark</th>
                                  <th scope="col" className="px-5 py-2.5 text-right font-semibold">Grade</th>
                                  <th scope="col" className="px-5 py-2.5 font-semibold">Remarks</th>
                                </tr>
                              </thead>
                              <tbody className="divide-ink-100 divide-y">
                                {(detail.data?.results ?? []).map((row) => (
                                  <tr key={row.subject_id}>
                                    <td className="px-5 py-3">
                                      <p className="text-ink-900 font-medium">{row.subject_name}</p>
                                      <p className="text-ink-400 font-mono text-xs">
                                        {row.subject_code}
                                      </p>
                                    </td>
                                    <td className="text-ink-900 px-5 py-3 text-right font-semibold tabular-nums">
                                      {row.marks}
                                    </td>
                                    <td className="px-5 py-3 text-right">
                                      <Badge tone="neutral">{row.grade}</Badge>
                                    </td>
                                    <td className="text-ink-600 px-5 py-3">
                                      {row.remarks ?? '—'}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                </li>
              )
            })}
          </ol>

          {visible.length === 0 && (
            <Card>
              <CardBody className="p-0">
                <EmptyState
                  icon="clock-rotate-left"
                  title="Nothing in that year"
                  description="Try a different academic year."
                  action={
                    <Button variant="secondary" icon="xmark" onClick={() => setYearFilter('')}>
                      Show all years
                    </Button>
                  }
                />
              </CardBody>
            </Card>
          )}
        </div>
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default PreviousResultsPage
