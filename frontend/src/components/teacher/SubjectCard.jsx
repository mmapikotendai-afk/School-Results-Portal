import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge, Button } from '@/components/ui'
import { teacherDownloads } from '@/services/teacherService'
import { getErrorMessage } from '@/services/apiClient'
import { formatDateTime } from '@/utils/format'

export function SubjectCard({ card, onDownloadError, onUpload }) {
  const [busy, setBusy] = useState(null)
  const isDone = ['SUBMITTED', 'LATE'].includes(card.status)
  async function download(kind) {
    setBusy(kind)
    try { await teacherDownloads[kind](card.examination_id, card.subject_id, card.subject_code) }
    catch (err) { onDownloadError?.(getErrorMessage(err, 'That download did not work.')) }
    finally { setBusy(null) }
  }
  return <article className="subject-row px-5 py-5 sm:px-6">
    <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_170px_150px] md:items-start">
      <div className="min-w-0"><div className="flex flex-wrap items-center gap-2.5"><h3 className="text-base font-semibold">{card.subject_name}</h3><span className="text-xs text-ink-500">{card.subject_code}</span></div><p className="mt-1 text-xs leading-relaxed text-ink-500">{card.examination_name} · {card.term_name}</p></div>
      <div><p className="mb-1.5 text-xs text-ink-500">Marks entered</p><p className="text-sm tabular-nums"><strong className="font-semibold">{card.submitted_count}</strong> <span className="text-ink-500">of {card.expected_count} students</span></p>{card.expected_count > 0 && <div className="mt-2 h-1 overflow-hidden rounded-sm bg-ink-100" aria-hidden="true"><div className={isDone ? 'h-full bg-success-600' : 'h-full bg-brand-800'} style={{width: Math.min(100, card.submitted_count / card.expected_count * 100) + '%'}} /></div>}</div>
      <div className="md:text-right"><Badge status={card.status}>{card.status === 'PENDING' ? 'Not submitted' : undefined}</Badge>{card.submission_deadline && <p className={'mt-2 text-[11px] leading-relaxed ' + (card.is_past_deadline && !isDone ? 'text-danger-600' : 'text-ink-500')}>Due {formatDateTime(card.submission_deadline)}</p>}</div>
    </div>
    {isDone && card.submitted_at && <p className="mt-3 text-xs text-ink-500">Submitted {formatDateTime(card.submitted_at)}{card.submitted_by ? ' by ' + card.submitted_by : ''}{card.status === 'LATE' ? ' · received after the deadline' : ''}</p>}
    {!card.can_upload && card.locked_reason && <p className="mt-3 text-xs leading-relaxed text-ink-500">{card.locked_reason}</p>}
    <div className="mt-4 flex flex-wrap items-center gap-2">
      {card.can_upload && <Button size="sm" icon="cloud-arrow-up" onClick={() => onUpload?.(card)}>Upload CSV</Button>}
      <Button as={Link} to={'/teacher/examinations/' + card.examination_id + '/subjects/' + card.subject_id} variant="secondary" size="sm" icon={card.can_upload ? 'pen-to-square' : 'eye'}>{card.can_upload ? (isDone ? 'Manage marks' : 'Enter marks') : 'View results'}</Button>
      <Button variant="ghost" size="sm" icon="download" loading={busy === 'template'} onClick={() => download('template')}>CSV template</Button>
      {card.submitted_count > 0 && <div className="flex items-center gap-1 md:ml-auto"><Button variant="ghost" size="sm" icon="file-csv" loading={busy === 'csv'} onClick={() => download('csv')}>CSV</Button><Button variant="ghost" size="sm" icon="file-pdf" loading={busy === 'pdf'} onClick={() => download('pdf')}>PDF</Button></div>}
    </div>
  </article>
}
export default SubjectCard
