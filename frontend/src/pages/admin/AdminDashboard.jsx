import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import SubmissionProgress from '@/components/admin/SubmissionProgress'
import { Alert, Badge, Button, Card, DataTable, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { dashboardService, resultsService } from '@/services/adminService'
import { formatDate, formatDateTime } from '@/utils/format'

function PublicationDesk({ data }) {
  const publication = data.publication
  return <section className="border-t-2 border-brand-900 pt-4">
            <h2 className="section-heading">Publication desk</h2>
            <div className="mt-4"><Badge tone={publication?.state === 'published' ? 'success' : 'neutral'}>{publication?.label ?? 'Awaiting submissions'}</Badge></div>
            <p className="mt-3 text-sm leading-relaxed text-ink-500">{publication?.detail}</p>
            <dl className="my-5 divide-y divide-ink-200 border-y border-ink-200 text-sm"><div className="flex justify-between gap-3 py-3"><dt className="text-ink-500">Published results</dt><dd className="font-medium tabular-nums">{data.results_published}</dd></div><div className="flex justify-between gap-3 py-3"><dt className="text-ink-500">Awaiting publication</dt><dd className="font-medium tabular-nums">{data.results_unpublished}</dd></div></dl>
            {publication?.published_by && <p className="mb-4 text-xs leading-relaxed text-ink-500">Published by {publication.published_by}{publication.published_at ? ' · ' + formatDate(publication.published_at) : ''}</p>}
            <Button as={Link} to="/admin/examinations" size="sm" fullWidth icon="arrow-right" iconPosition="right">{publication?.state === 'published' ? 'Manage examinations' : 'Review & publish'}</Button>
          </section>
}

export function AdminDashboard() {
  useDocumentTitle('Academic workspace')
  const { data, loading, error, refresh } = useAsyncData(() => dashboardService.stats(), [])
  const audit = useAsyncData(() => resultsService.auditTrail({ limit: 4 }), [])
  if (loading && !data) return <PageLoader label="Loading academic workspace" />
  const exam = data?.current_examination
  const outstanding = [...(data?.overdue_submissions ?? []).map(row => ({...row, state: 'OVERDUE'})), ...(data?.pending_submissions ?? []).map(row => ({...row, state: 'PENDING'}))]
  const columns = [
    { key: 'subject_name', header: 'Subject', primary: true, render: row => <div><p className="font-medium text-ink-900">{row.subject_name}</p><p className="mt-1 text-xs text-ink-500">{row.subject_code}</p></div> },
    { key: 'teacher_name', header: 'Teacher' },
    { key: 'marks', header: 'Marks received', render: row => row.expected_count > 0 ? <span className="tabular-nums">{row.submitted_count} <span className="text-ink-500">/ {row.expected_count}</span></span> : 'No enrolled students' },
    { key: 'state', header: 'Due', render: row => <div><Badge status={row.state}>{row.state === 'OVERDUE' ? (row.days_overdue ?? 0) + ' days overdue' : 'Pending'}</Badge><p className="mt-1 text-xs text-ink-500">{formatDate(row.deadline)}</p></div> },
  ]
  return <div>
    <PageHeader title="Academic workspace" description={data?.active_year_name ? [data.active_term_name, data.active_year_name].filter(Boolean).join(' · ') + ' — results, records and the next steps for your school.' : 'Organise the academic year, then bring your school records together.'}
      actions={<Button variant="secondary" size="sm" icon="rotate" onClick={() => { refresh(); audit.refresh() }} loading={loading}>Refresh</Button>} />
    {error && <Alert tone="danger" title="Workspace could not be refreshed" className="mb-6">{error} <button onClick={refresh} className="font-semibold underline">Try again</button></Alert>}
    {data && <>
      <div className="record-census mb-7" aria-label="School register">
        {[['students', data.total_students, 'active students'], ['teachers', data.total_teachers, 'teachers'], ['classes', data.total_classes, 'classes'], ['subjects', data.total_subjects, 'subjects']].map(([path,count,label]) => count != null && <Link key={path} to={'/admin/' + path}><strong>{count.toLocaleString()}</strong>{label}<FontAwesomeIcon icon="chevron-right" className="ml-1 text-[9px]" /></Link>)}
      </div>
      <div className="grid items-start gap-7 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div className="min-w-0 space-y-7">
          <Card>
            {exam ? <>
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-ink-200 px-5 py-5 sm:px-6">
                <div><h2 className="font-serif text-2xl font-medium">{exam.name}</h2><p className="mt-1 text-xs text-ink-500">{[exam.term_name, exam.academic_year_name].filter(Boolean).join(' · ')}</p></div>
                <Badge status={exam.status} />
              </div>
              <div className="p-5 sm:p-6">
                <SubmissionProgress submitted={data.submissions_complete} pending={data.submissions_pending} overdue={data.submissions_overdue} total={data.submissions_total} progress={data.submission_progress} />
                <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-ink-200 pt-4">
                  <p className={'flex items-center gap-2 text-xs ' + (exam.is_past_deadline ? 'text-danger-600' : 'text-ink-500')}><FontAwesomeIcon icon="clock" />{exam.submission_deadline ? 'Due ' + formatDateTime(exam.submission_deadline) : 'No submission deadline set'}</p>
                  <Link to="/admin/submissions" className="text-link">Track submissions <FontAwesomeIcon icon="arrow-right" className="ml-1 text-xs" /></Link>
                </div>
              </div>
            </> : <div className="p-6 sm:p-8"><h2 className="font-serif text-2xl font-medium">Prepare your next examination</h2><p className="mt-3 max-w-lg text-sm leading-relaxed text-ink-500">Set the academic year and term, then open an examination to collect marks from teachers.</p><ol className="my-6 divide-y divide-ink-200">
              {[[data.active_year_name, 'Academic year', '/admin/academic-years'], [data.active_term_name, 'Term', '/admin/terms'], [null, 'Examination', '/admin/examinations']].map(([value,label,to], i) => <li key={label} className="flex items-center justify-between gap-3 py-3 text-sm"><span className="flex items-center gap-3"><span className="text-ink-500">{i+1}.</span>{label}</span><Link to={to} className="text-link">{value || 'Set up'} <FontAwesomeIcon icon={value ? 'circle-check' : 'arrow-right'} className="ml-2 text-xs" /></Link></li>)}
              </ol><Button as={Link} to="/admin/examinations" size="sm" icon="plus">Create examination</Button></div>}
          </Card>
          {exam && <div className="xl:hidden"><PublicationDesk data={data} /></div>}
          {exam && <section aria-labelledby="attention-title">
            <div className="mb-4 flex items-center justify-between gap-3"><h2 id="attention-title" className="section-heading">Outstanding submissions <span className="ml-2 text-xs font-normal text-ink-500">{outstanding.length}</span></h2><Link to="/admin/submissions" className="text-link">View all</Link></div>
            <Card><DataTable columns={columns} rows={outstanding.slice(0, 5)} rowKey={row => row.submission_id} empty={<EmptyState icon="circle-check" title={data.submissions_total > 0 ? 'All required subjects submitted' : 'No submissions to track yet'} description={data.submissions_total > 0 ? 'Review the marks before publishing student report cards.' : 'Assign subjects and open submissions in Examinations.'} action={<Button as={Link} to="/admin/examinations" variant="secondary" size="sm">Manage examination</Button>} />} />{outstanding.length > 5 && <div className="border-t border-ink-200 px-5 py-3 text-xs text-ink-500">Showing 5 of {outstanding.length} outstanding submissions. <Link to="/admin/submissions" className="text-link">View the full register</Link></div>}</Card>
          </section>}
          <section aria-labelledby="operations-title">
            <div className="mb-3 flex items-center justify-between gap-3"><h2 id="operations-title" className="section-heading">Recent mark corrections</h2><Link to="/admin/results" className="text-link">Review results</Link></div>
            {audit.error ? <Alert tone="warning">Recent corrections could not be loaded. <button className="underline" onClick={audit.refresh}>Retry</button></Alert> : audit.loading && !audit.data ? <p className="py-4 text-sm text-ink-500" role="status">Loading corrections…</p> : audit.data?.length ? <ul className="divide-y divide-ink-200 border-y border-ink-200">{audit.data.map(event => <li key={event.id} className="flex items-start gap-3 py-4"><FontAwesomeIcon icon="pen-to-square" className="mt-1 text-xs text-ink-500" /><div className="min-w-0 flex-1"><p className="text-sm"><span className="font-medium">{event.subject_name}</span> · {event.student_name}</p><p className="mt-1 text-xs leading-relaxed text-ink-500">{event.changed_by ?? 'School staff'} changed {event.old_marks ?? '—'} to {event.new_marks ?? '—'}{event.reason ? ' · ' + event.reason : ''}</p><p className="mt-1 text-xs text-ink-500">{formatDateTime(event.changed_at)}</p></div></li>)}</ul> : <p className="border-y border-ink-200 py-5 text-sm leading-relaxed text-ink-500">No mark corrections recorded. Changes to results will appear here with the author and reason.</p>}
          </section>
        </div>
        <aside className="space-y-7">
          {exam && <div className="hidden xl:block"><PublicationDesk data={data} /></div>}
          <section className="border-t border-ink-200 pt-4"><h2 className="section-heading">Student register</h2><p className="mt-3 text-sm leading-relaxed text-ink-500">Manage admissions, annual placements and confirmed returns.</p><div className="mt-4 space-y-3"><Link to="/admin/students" className="text-link block">Open student register <FontAwesomeIcon icon="arrow-right" className="ml-1 text-xs" /></Link><Link to="/admin/students/import" className="text-link block">New intake or transfer import</Link><Link to="/admin/progression" className="text-link block">Progression and returns</Link></div></section>
          <section className="border-t border-ink-200 pt-4"><h2 className="section-heading">Academic structure</h2><div className="mt-3 divide-y divide-ink-200">{[['Academic years','/admin/academic-years'],['Terms','/admin/terms'],['Classes & placements','/admin/classes'],['Subjects & teachers','/admin/subjects']].map(([label,to]) => <Link key={to} to={to} className="flex items-center justify-between gap-2 py-3 text-[13px] text-ink-600 hover:text-brand-800">{label}<FontAwesomeIcon icon="chevron-right" className="text-[9px]" /></Link>)}</div></section>
        </aside>
      </div>
    </>}
  </div>
}
export default AdminDashboard
