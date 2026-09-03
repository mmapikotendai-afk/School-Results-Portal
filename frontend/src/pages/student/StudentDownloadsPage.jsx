import { useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import { Alert, Button, Card, CardBody, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import studentResultsService, { studentDownloads } from '@/services/studentService'
import { getErrorMessage } from '@/services/apiClient'
import { formatDate } from '@/utils/format'

/**
 * The student's own result files.
 *
 * Only published examinations are listed, because only those exist as far as a
 * student is concerned. Each file is generated from the record at the moment
 * it is asked for, so a correction the school made is already in it.
 */
export function StudentDownloadsPage() {
  useDocumentTitle('Downloads')

  const [busy, setBusy] = useState(null)
  const { toast, show, clear } = useToast()

  const history = useAsyncData(() => studentResultsService.history(), [])

  const published = useMemo(
    () => (history.data?.entries ?? []).filter((e) => e.is_published),
    [history.data],
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

  if (history.loading && !history.data) return <PageLoader label="Loading your downloads" />

  return (
    <div>
      <PageHeader
        title="Downloads"
        description="Your report card and results, ready to save or print."
      />

      {history.error && (
        <Alert tone="danger" title="Could not load your downloads" className="mb-5">
          {history.error}
        </Alert>
      )}

      {published.length === 0 ? (
        <Card>
          <CardBody className="p-0">
            <EmptyState
              icon="download"
              title="Nothing to download yet"
              description="Your report card becomes available as soon as the school publishes an examination."
              action={
                <Button as={Link} to="/student/dashboard" variant="secondary" icon="arrow-left">
                  Back to dashboard
                </Button>
              }
            />
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-4">
          {published.map((entry) => (
            <Card key={entry.examination_id}>
              <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-center">
                <span className="bg-brand-50 text-brand-700 flex size-11 shrink-0 items-center justify-center rounded-lg">
                  <FontAwesomeIcon icon="file-pdf" className="text-lg" aria-hidden="true" />
                </span>

                <div className="min-w-0 flex-1">
                  <h3 className="text-base font-semibold">{entry.examination_name}</h3>
                  <p className="text-ink-500 mt-0.5 text-sm">
                    {[entry.term_name, entry.academic_year_name].filter(Boolean).join(' · ')}
                    {entry.published_at ? ` · Released ${formatDate(entry.published_at)}` : ''}
                  </p>
                  <p className="text-ink-400 mt-0.5 text-xs">
                    {entry.subjects_taken} subject{entry.subjects_taken === 1 ? '' : 's'}
                    {entry.average !== null && entry.average !== undefined
                      ? ` · average ${entry.average}`
                      : ''}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button
                    icon="file-pdf"
                    loading={busy === `pdf-${entry.examination_id}`}
                    onClick={() => download('pdf', entry)}
                  >
                    Report card
                  </Button>
                  <Button
                    variant="secondary"
                    icon="file-csv"
                    loading={busy === `csv-${entry.examination_id}`}
                    onClick={() => download('csv', entry)}
                  >
                    CSV
                  </Button>
                </div>
              </CardBody>
            </Card>
          ))}

          <p className="text-ink-400 px-1 text-xs">
            <FontAwesomeIcon icon="circle-info" className="mr-1.5" aria-hidden="true" />
            These files are yours alone. They are generated from your own record and never
            include another student&rsquo;s results.
          </p>
        </div>
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default StudentDownloadsPage
