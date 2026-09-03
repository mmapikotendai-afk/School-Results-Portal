import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import { Alert, Badge, Button, Card, CardBody, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useToast from '@/hooks/useToast'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { studentDownloads, studentResultsService } from '@/services/studentService'
import { getErrorMessage } from '@/services/apiClient'
import { formatDate } from '@/utils/format'

/** Colour a grade by how it reads at a glance, without asserting a pass mark. */
function gradeTone(grade) {
  if (!grade) return 'neutral'
  const symbol = grade.toUpperCase()
  if (symbol === 'A') return 'success'
  if (symbol === 'B' || symbol === 'C') return 'brand'
  if (symbol === 'U' || symbol === 'F') return 'danger'
  return 'warning'
}

/** One published examination and the marks in it. */
function ExaminationCard({ entry, onDownload, busy }) {
  return (
    <Card id={`exam-${entry.examination_id}`} className="scroll-mt-24">
      <div className="border-ink-200 flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4">
        <div className="min-w-0">
          <h3 className="text-base font-semibold">{entry.examination_name}</h3>
          <p className="text-ink-500 mt-0.5 text-sm">
            {entry.term_name}
            {entry.academic_year_name ? ` · ${entry.academic_year_name}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="text-right">
            <Badge tone="success">Published</Badge>
            {entry.published_at && (
              <p className="text-ink-400 mt-1 text-xs">{formatDate(entry.published_at)}</p>
            )}
          </div>
          <Button
            variant="secondary"
            size="sm"
            icon="file-pdf"
            loading={busy === `pdf-${entry.examination_id}`}
            onClick={() => onDownload('pdf', entry)}
          >
            PDF
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon="file-csv"
            loading={busy === `csv-${entry.examination_id}`}
            onClick={() => onDownload('csv', entry)}
          >
            CSV
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[26rem] border-collapse text-sm">
          <thead>
            <tr className="border-ink-200 border-b">
              <th scope="col" className="text-ink-500 px-5 py-2.5 text-left text-xs font-semibold tracking-wide uppercase">
                Subject
              </th>
              <th scope="col" className="text-ink-500 px-5 py-2.5 text-right text-xs font-semibold tracking-wide uppercase">
                Mark
              </th>
              <th scope="col" className="text-ink-500 px-5 py-2.5 text-right text-xs font-semibold tracking-wide uppercase">
                Grade
              </th>
              <th scope="col" className="text-ink-500 px-5 py-2.5 text-left text-xs font-semibold tracking-wide uppercase">
                Remark
              </th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {entry.results.map((row) => (
              <tr key={row.subject_id}>
                <td className="px-5 py-3">
                  <p className="text-ink-900 font-medium">{row.subject_name}</p>
                  <p className="text-ink-400 font-mono text-xs">{row.subject_code}</p>
                </td>
                <td className="text-ink-900 px-5 py-3 text-right font-semibold tabular-nums">
                  {Number(row.marks).toFixed(0)}
                </td>
                <td className="px-5 py-3 text-right">
                  <Badge tone={gradeTone(row.grade)}>{row.grade ?? '—'}</Badge>
                </td>
                <td className="text-ink-600 px-5 py-3">{row.remarks ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border-ink-200 bg-ink-50 flex flex-wrap items-center gap-6 border-t px-5 py-3">
        <div>
          <p className="text-ink-400 text-xs">Subjects</p>
          <p className="text-ink-900 font-semibold">{entry.subjects_taken}</p>
        </div>
        {entry.average !== null && (
          <div>
            <p className="text-ink-400 text-xs">Average</p>
            <p className="text-ink-900 font-semibold tabular-nums">{entry.average}</p>
          </div>
        )}
        {entry.best_subject && (
          <div>
            <p className="text-ink-400 text-xs">Best subject</p>
            <p className="text-ink-900 font-semibold">{entry.best_subject}</p>
          </div>
        )}
      </div>
    </Card>
  )
}

/**
 * My results.
 *
 * Only published examinations appear. One still being marked or reviewed is
 * named so the student knows the school has not forgotten them, but carries no
 * mark, grade or count - the API does not send one.
 */
export function StudentResultsPage() {
  useDocumentTitle('My Results')

  const { data, loading, error } = useAsyncData(() => studentResultsService.all(), [])
  const { toast, show, clear } = useToast()
  const [busy, setBusy] = useState(null)

  async function handleDownload(kind, entry) {
    setBusy(`${kind}-${entry.examination_id}`)
    try {
      const name = await studentDownloads[kind](
        entry.examination_id,
        entry.term_name ?? 'results',
      )
      show(`Downloaded ${name}`)
    } catch (err) {
      show(getErrorMessage(err, 'That download did not work.'), 'danger')
    } finally {
      setBusy(null)
    }
  }

  if (loading && !data) return <PageLoader label="Loading your results" />

  return (
    <div>
      <PageHeader
        title="My results"
        description={
          data
            ? `${data.full_name} · ${data.student_number}${data.class_name ? ` · ${data.class_name}` : ''}`
            : undefined
        }
      />

      {error && (
        <Alert tone="danger" className="mb-5">
          {error}
        </Alert>
      )}

      {/* Examinations under way: named, never scored. */}
      {data?.in_progress?.length > 0 && (
        <div className="mb-6 space-y-3">
          {data.in_progress.map((exam) => (
            <Alert key={exam.examination_id} tone="info" title={exam.headline ?? 'Results Not Yet Published'}>
              <p className="font-medium">
                {exam.term_name ? `${exam.term_name} — ` : ''}
                {exam.examination_name}
              </p>
              <p className="mt-1">{exam.message}</p>
              <p className="mt-1 text-xs opacity-80">
                {exam.term_name}
                {exam.academic_year_name ? ` · ${exam.academic_year_name}` : ''} · Results
                appear here once the school publishes them.
              </p>
            </Alert>
          ))}
        </div>
      )}

      {data?.published?.length > 0 ? (
        <div className="space-y-5">
          {data.published.map((entry) => (
            <ExaminationCard
              key={entry.examination_id}
              entry={entry}
              busy={busy}
              onDownload={handleDownload}
            />
          ))}
        </div>
      ) : (
        !error && (
          <Card>
            <CardBody className="p-0">
              <EmptyState
                icon="file-lines"
                title="No published results yet"
                description={
                  data?.in_progress?.length
                    ? 'Your marks will appear here as soon as the school publishes them.'
                    : 'Once your teachers submit marks and the school publishes them, your results will appear here.'
                }
              />
            </CardBody>
          </Card>
        )
      )}

      {data?.enrolled_subjects?.length > 0 && (
        <Card className="mt-5">
          <div className="border-ink-200 border-b px-5 py-4">
            <h3 className="text-base font-semibold">Subjects I study</h3>
            <p className="text-ink-500 mt-0.5 text-sm">
              You only receive results for the subjects you are enrolled in.
            </p>
          </div>
          <CardBody>
            <div className="flex flex-wrap gap-1.5">
              {data.enrolled_subjects.map((name) => (
                <Badge key={name} tone="brand">
                  {name}
                </Badge>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      <Toast toast={toast} onDismiss={clear} />

      <p className="text-ink-400 mt-6 flex items-start gap-2 text-xs">
        <FontAwesomeIcon icon="circle-info" className="mt-0.5" aria-hidden="true" />
        If a mark looks wrong, speak to your subject teacher or the school office. Results
        can only be corrected by the school.
      </p>
    </div>
  )
}

export default StudentResultsPage
