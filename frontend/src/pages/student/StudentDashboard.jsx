import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link } from 'react-router-dom'
import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import { Alert, Badge, Button, Card, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { getErrorMessage } from '@/services/apiClient'
import { studentDownloads, studentResultsService } from '@/services/studentService'
import { formatDate } from '@/utils/format'

export function StudentDashboard() {
  useDocumentTitle('My academic record')
  const history = useAsyncData(() => studentResultsService.history(), [])
  const results = useAsyncData(() => studentResultsService.all(), [])
  const { data, loading, error, refresh } = history
  const { toast, show, clear } = useToast()
  const [busy, setBusy] = useState(null)
  async function download(kind, entry) {
    setBusy(kind + '-' + entry.examination_id)
    try { const name = await studentDownloads[kind](entry.examination_id, entry.term_name ?? 'results'); show('Downloaded ' + name) }
    catch (err) { show(getErrorMessage(err, 'That download did not work.'), 'danger') }
    finally { setBusy(null) }
  }
  if (loading && !data) return <PageLoader label="Loading your academic record" />
  const latest = results.data?.published?.[0]
  return <div>
    <PageHeader title="My academic record" description="Your subjects, published results and report cards."
      actions={<Button variant="ghost" size="sm" icon="rotate" loading={loading || results.loading} onClick={() => {refresh(); results.refresh()}}>Refresh</Button>} />
    {error && <Alert tone="danger" className="mb-5">{error} <button className="underline" onClick={refresh}>Try again</button></Alert>}
    {data && <div className="mb-7 flex flex-wrap items-center justify-between gap-5 border-y border-ink-200 py-5">
      <div className="min-w-0"><h2 className="font-serif text-2xl font-medium">{data.full_name}</h2><p className="mt-2 text-xs tracking-wide text-ink-500">Student number <span className="ml-2 font-medium text-ink-800">{data.student_number}</span></p></div>
      <div className="flex items-center gap-4"><span className="h-8 w-px bg-ink-200" aria-hidden="true" /><div><p className="text-sm font-medium">{data.class_name ?? 'Class not assigned'}</p><p className="mt-1 text-xs text-ink-500">{data.level === 'O_LEVEL' ? 'Ordinary Level' : data.level === 'A_LEVEL' ? 'Advanced Level' : 'Student record'}</p></div></div>
    </div>}
    <div className="grid items-start gap-7 xl:grid-cols-[minmax(0,1fr)_270px]">
      <div className="min-w-0">
        {results.error && <Alert tone="warning" className="mb-5">Your subject results could not be loaded. <button className="underline" onClick={results.refresh}>Try again</button></Alert>}
        {results.loading && !results.data ? <PageLoader label="Loading published marks" /> : latest ? <Card>
          <div className="border-b border-ink-200 p-5 sm:p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h2 className="section-heading">Latest published results</h2><Badge tone="success">Published</Badge></div>
            <h3 className="font-serif text-[28px] leading-tight font-medium">{latest.examination_name}</h3><p className="mt-2 text-sm text-ink-500">{[latest.term_name, latest.academic_year_name].filter(Boolean).join(' · ')}</p>
            <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm"><span><strong>{latest.subjects_taken}</strong> <span className="text-ink-500">subjects</span></span>{latest.average != null && <span><strong className="tabular-nums">{latest.average}%</strong> <span className="text-ink-500">average</span></span>}</div>
          </div>
          <div className="px-5 sm:px-6"><div className="grid grid-cols-[minmax(0,1fr)_64px_48px] gap-3 border-b border-ink-200 py-3 text-xs text-ink-500"><span>Subject</span><span className="text-right">Mark /100</span><span className="text-right">Grade</span></div>
          <ul className="divide-y divide-ink-200">{latest.results.map(row => <li key={row.subject_id} className="grid grid-cols-[minmax(0,1fr)_64px_48px] items-center gap-3 py-4 text-sm"><div className="min-w-0"><p className="font-medium wrap-break-word">{row.subject_name}</p>{row.remarks && <p className="mt-1 text-xs leading-relaxed text-ink-500">{row.remarks}</p>}</div><span className="text-right font-semibold tabular-nums">{Number(row.marks).toFixed(0)}</span><span className="text-right font-serif text-xl">{row.grade ?? '—'}</span></li>)}</ul></div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-200 p-5 sm:px-6"><Button size="sm" icon="file-pdf" loading={busy === 'pdf-' + latest.examination_id} onClick={() => download('pdf',latest)}>Download report card</Button><Link to={'/student/results#exam-' + latest.examination_id} className="text-link">View full results <FontAwesomeIcon icon="arrow-right" className="ml-1 text-xs" /></Link></div>
        </Card> : !results.error && <Card><EmptyState icon="file-lines" title="Your next chapter is on its way" description="Published marks and report cards will appear here after the school completes its review." /></Card>}
        {results.data?.enrolled_subjects?.length > 0 && <section className="mt-7"><h2 className="section-heading">Subjects I study</h2><ul className="mt-3 flex flex-wrap gap-2">{results.data.enrolled_subjects.map(name => <li key={name} className="rounded-md border border-ink-200 bg-white px-3 py-2 text-xs text-ink-600">{name}</li>)}</ul></section>}
      </div>
      <aside>
        <h2 className="section-heading border-t-2 border-brand-900 pt-4">Examination history</h2>
        {data?.entries?.length ? <ol className="mt-3 divide-y divide-ink-200">{data.entries.map(entry => <li key={entry.examination_id} className="py-4">
          <p className="text-xs text-ink-500">{[entry.term_name, entry.academic_year_name].filter(Boolean).join(' · ')}</p><h3 className="mt-1.5 text-sm font-medium">{entry.examination_name}</h3>
          {entry.is_published ? <><div className="mt-2 flex flex-wrap items-center gap-2"><Badge tone="success">Published</Badge>{entry.published_at && <span className="text-[11px] text-ink-500">{formatDate(entry.published_at)}</span>}</div><div className="mt-3 flex flex-wrap items-center gap-3"><Link to={'/student/results#exam-' + entry.examination_id} className="text-link">View results</Link><Button variant="ghost" size="sm" loading={busy === 'pdf-' + entry.examination_id} onClick={() => download('pdf',entry)} aria-label={'Download PDF for ' + entry.examination_name}>PDF</Button><Button variant="ghost" size="sm" loading={busy === 'csv-' + entry.examination_id} onClick={() => download('csv',entry)} aria-label={'Download CSV for ' + entry.examination_name}>CSV</Button></div></> : <><div className="mt-2"><Badge tone="neutral"><FontAwesomeIcon icon="lock" />Not published</Badge></div><p className="mt-2 text-xs leading-relaxed text-ink-500">{entry.message || 'The school is preparing these results.'}</p></>}
        </li>)}</ol> : <p className="mt-4 text-sm leading-relaxed text-ink-500">Examinations will appear here when the school sets them up for your class.</p>}
        <div className="mt-5 border-t border-ink-200 pt-5"><h2 className="section-heading">A question about a mark?</h2><p className="mt-2 text-xs leading-relaxed text-ink-500">Speak to your subject teacher or the school office. Only your school can correct an academic record.</p></div>
      </aside>
    </div>
    <Toast toast={toast} onDismiss={clear} />
  </div>
}
export default StudentDashboard
