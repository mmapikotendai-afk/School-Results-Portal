import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import { Alert, Badge, Button, Card, CardBody, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { getErrorMessage } from '@/services/apiClient'
import { studentDownloads, studentResultsService } from '@/services/studentService'
import { formatDate } from '@/utils/format'

/**
 * One examination on the results history.
 *
 * A published entry offers the results and the downloads. An unpublished one
 * is named and explained, and shows nothing else - the API sends no marks for
 * it, so there is nothing here that could leak one.
 */
function HistoryRow({ entry, onDownload, busy }) {
  const label = [entry.term_name, entry.academic_year_name].filter(Boolean).join(' — ')

  return (
    <div className="border-ink-200 flex flex-wrap items-center justify-between gap-4 border-b px-5 py-4 last:border-b-0">
      <div className="min-w-0 flex-1">
        <p className="text-ink-900 font-semibold">{label || entry.examination_name}</p>
        <p className="text-ink-500 mt-0.5 text-sm">{entry.examination_name}</p>

        {entry.is_published ? (
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <Badge tone="success">
              <FontAwesomeIcon icon="circle-check" className="text-[10px]" aria-hidden="true" />
              Published
            </Badge>
            {entry.published_at && (
              <span className="text-ink-400 text-xs">{formatDate(entry.published_at)}</span>
            )}
            <span className="text-ink-500 text-xs">
              {entry.subjects_taken} subject{entry.subjects_taken === 1 ? '' : 's'}
              {entry.average !== null && ` · average ${entry.average}`}
            </span>
          </div>
        ) : (
          <div className="mt-2">
            <Badge tone="neutral">
              <FontAwesomeIcon icon="lock" className="text-[10px]" aria-hidden="true" />
              Not published
            </Badge>
            <p className="text-ink-500 mt-1.5 text-sm">{entry.message}</p>
          </div>
        )}
      </div>

      {entry.is_published && (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            icon="file-pdf"
            loading={busy === `pdf-${entry.examination_id}`}
            onClick={() => onDownload('pdf', entry)}
          >
            PDF
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon="file-csv"
            loading={busy === `csv-${entry.examination_id}`}
            onClick={() => onDownload('csv', entry)}
          >
            CSV
          </Button>
          <Button
            as={Link}
            to={`/student/results#exam-${entry.examination_id}`}
            size="sm"
            icon="arrow-right"
            iconPosition="right"
          >
            View Results
          </Button>
        </div>
      )}
    </div>
  )
}

/** Student overview: who they are, and their results history. */
export function StudentDashboard() {
  useDocumentTitle('Dashboard')

  const { data, loading, error } = useAsyncData(() => studentResultsService.history(), [])
  const { toast, show, clear } = useToast()
  const [busy, setBusy] = useState(null)

  async function handleDownload(kind, entry) {
    const key = `${kind}-${entry.examination_id}`
    setBusy(key)
    try {
      const name = await studentDownloads[kind](
        entry.examination_id,
        `${entry.term_name ?? 'results'}`,
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
        title={data?.full_name ? `Hello, ${data.full_name.split(' ')[0]}` : 'Dashboard'}
        description="Your latest results, and what is still to come."
      />

      {error && (
        <Alert tone="danger" className="mb-5">
          {error}
        </Alert>
      )}

      {/* Identity card */}
      {data && (
        <Card className="mb-6">
          <CardBody>
            <div className="flex flex-wrap items-center gap-x-10 gap-y-4">
              <div>
                <p className="text-ink-400 text-xs font-semibold tracking-wide uppercase">
                  Student
                </p>
                <p className="text-ink-900 font-serif text-lg font-semibold">
                  {data.full_name}
                </p>
              </div>
              <div>
                <p className="text-ink-400 text-xs font-semibold tracking-wide uppercase">
                  Student number
                </p>
                <p className="text-ink-900 font-mono text-sm font-semibold">
                  {data.student_number}
                </p>
              </div>
              <div>
                <p className="text-ink-400 text-xs font-semibold tracking-wide uppercase">
                  Class
                </p>
                <p className="text-ink-900 text-sm font-semibold">
                  {data.class_name ?? 'Not assigned'}
                  {data.level && (
                    <span className="text-ink-400 ml-2 text-xs font-normal">
                      {data.level === 'O_LEVEL' ? 'O-Level' : 'A-Level'}
                    </span>
                  )}
                </p>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      <Card>
        <div className="border-ink-200 flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
          <div>
            <h2 className="text-base font-semibold">Results history</h2>
            <p className="text-ink-500 mt-0.5 text-sm">
              Results stay available once the school has published them.
            </p>
          </div>
          {data && (
            <span className="text-ink-500 text-sm">
              {data.published_count} published
              {data.pending_count > 0 && ` · ${data.pending_count} pending`}
            </span>
          )}
        </div>

        {data?.entries?.length ? (
          <div>
            {data.entries.map((entry) => (
              <HistoryRow
                key={entry.examination_id}
                entry={entry}
                busy={busy}
                onDownload={handleDownload}
              />
            ))}
          </div>
        ) : (
          !error && (
            <EmptyState
              icon="file-lines"
              title="No examinations yet"
              description="Once the school sets up an examination for your class, it will appear here."
            />
          )
        )}
      </Card>

      <p className="text-ink-400 mt-6 flex items-start gap-2 text-xs">
        <FontAwesomeIcon icon="circle-info" className="mt-0.5" aria-hidden="true" />
        You only receive results for the subjects you are enrolled in. If a mark looks
        wrong, speak to your subject teacher or the school office.
      </p>

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default StudentDashboard
