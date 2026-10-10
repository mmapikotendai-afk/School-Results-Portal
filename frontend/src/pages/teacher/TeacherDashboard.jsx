import { useState } from 'react'
import { Link } from 'react-router-dom'
import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import SubjectCard from '@/components/teacher/SubjectCard'
import UploadDialog from '@/components/teacher/UploadDialog'
import { Alert, Button, Card, Input, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { teacherPortalService } from '@/services/teacherService'

export function TeacherDashboard() {
  useDocumentTitle('Teaching desk')
  const { data, loading, error, refresh } = useAsyncData(() => teacherPortalService.dashboard(), [])
  const { toast, show, clear } = useToast()
  const [uploadFor, setUploadFor] = useState(null)
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')
  if (loading && !data) return <PageLoader label="Loading your subjects" />
  const hasExam = Boolean(data?.current_examination)
  const subjects = data?.subjects ?? []
  const done = card => ['SUBMITTED', 'LATE'].includes(card.status)
  const visible = subjects.filter(card => (filter === 'all' || (filter === 'submitted' ? done(card) : !done(card))) && (card.subject_name + ' ' + card.subject_code).toLowerCase().includes(query.toLowerCase())).sort((a,b) => Number(done(a)) - Number(done(b)) || Number(b.status === 'OVERDUE') - Number(a.status === 'OVERDUE'))
  return <div>
    <PageHeader title="Teaching desk" description={hasExam ? [data.current_examination, data.term_name, data.academic_year_name].filter(Boolean).join(' · ') : 'Your assigned subjects, marks and submission deadlines.'}
      actions={<><Button as={Link} to="/teacher/results" variant="secondary" size="sm" icon="clock-rotate-left">Previous submissions</Button><Button variant="ghost" size="sm" icon="rotate" onClick={refresh} loading={loading}>Refresh</Button></>} />
    {error && <Alert tone="danger" className="mb-5">{error} <button onClick={refresh} className="font-semibold underline">Try again</button></Alert>}
    {data?.overdue_subjects > 0 && <Alert tone="danger" title="Outstanding marks are past due" className="mb-5">{data.overdue_subjects} subject{data.overdue_subjects === 1 ? '' : 's'} past the submission deadline. Open the mark sheet to check missing entries and available editing permissions.</Alert>}
    {data && <div className="mb-7 flex flex-wrap items-center gap-x-7 gap-y-3 border-y border-ink-200 py-4 text-sm text-ink-500"><span><strong className="mr-1.5 text-ink-900">{data.total_subjects}</strong> assigned subjects</span><span><strong className="mr-1.5 text-ink-900">{data.submitted_subjects}</strong> submitted</span><span><strong className="mr-1.5 text-ink-900">{data.outstanding_subjects}</strong> outstanding</span></div>}
    {subjects.length ? <section aria-labelledby="subjects-title">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><h2 id="subjects-title" className="section-heading">Subject register</h2><p className="text-xs text-ink-500">Outstanding subjects appear first</p></div>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-200 p-3 sm:px-5">
          <div className="flex flex-wrap gap-1" aria-label="Filter subjects">{[['all','All subjects',subjects.length],['outstanding','Needs marks',subjects.filter(s => !done(s)).length],['submitted','Submitted',subjects.filter(done).length]].map(([value,label,count]) => <button key={value} type="button" className="filter-tab" aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}<span className="tabular-nums opacity-80">{count}</span></button>)}</div>
          <Input aria-label="Find a subject" icon="magnifying-glass" placeholder="Find a subject…" value={query} onChange={e => setQuery(e.target.value)} className="sm:max-w-[230px]" />
        </div>
        <div className="divide-y divide-ink-200">{visible.map(card => <SubjectCard key={card.examination_id + '-' + card.subject_id} card={card} onDownloadError={message => show(message, 'danger')} onUpload={setUploadFor} />)}</div>
        {!visible.length && <EmptyState icon="magnifying-glass" title="No matching subjects" description="Try a different subject name or view all assignments." action={<Button variant="secondary" size="sm" onClick={() => {setQuery(''); setFilter('all')}}>Clear filters</Button>} />}
      </Card>
    </section> : !error && <Card><EmptyState icon="book" title={hasExam ? 'Your subject register is empty' : 'No examination is open'} description={hasExam ? 'The school office assigns your subjects. Contact them if an assignment is missing.' : 'When the school opens an examination, your assigned subjects and mark sheets will appear here.'} action={<Button as={Link} to="/teacher/results" variant="secondary" size="sm">View previous results</Button>} /></Card>}
    <p className="mt-5 text-xs leading-relaxed text-ink-500">Working from a spreadsheet? Download the subject’s CSV template, add the marks, then upload it for validation.</p>
    {uploadFor && <UploadDialog open sheet={uploadFor} onClose={() => setUploadFor(null)} onUploaded={result => {setUploadFor(null); refresh(); show(result.detail)}} />}
    <Toast toast={toast} onDismiss={clear} />
  </div>
}
export default TeacherDashboard
