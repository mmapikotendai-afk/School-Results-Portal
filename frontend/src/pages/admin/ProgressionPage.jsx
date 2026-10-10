import { useEffect, useMemo, useState } from 'react'

import PageHeader from '@/components/common/PageHeader'
import { Alert, Badge, Button, Card, DataTable, Select, SubjectPicker } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { academicService, classService, progressionService, subjectService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

const ACTIONS = [
  { value: 'PROMOTE', label: 'Promote to next Form' },
  { value: 'REPEAT', label: 'Repeat the same Form' },
  { value: 'CHANGE_CLASS', label: 'Change class in this year' },
  { value: 'O_LEVEL_TO_A_LEVEL', label: 'Form 4 to Lower 6' },
  { value: 'CONFIRM_RETURN', label: 'Confirm returned students' },
]

const pretty = value => value?.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase())

export function ProgressionPage() {
  useDocumentTitle('Student Progression')
  const catalog = useAsyncData(async () => {
    const [years, classes, subjects] = await Promise.all([
      academicService.listYears(), classService.list(), subjectService.list(),
    ])
    return { years, classes, subjects }
  }, [])
  const years = catalog.data?.years ?? []
  const classes = catalog.data?.classes ?? []
  const subjects = catalog.data?.subjects ?? []
  const activeYear = years.find(year => year.is_active)?.id ?? ''
  const [form, setForm] = useState({ source: '', target: '', sourceClass: '', targetClass: '', action: 'PROMOTE' })
  const [roster, setRoster] = useState([])
  const [selected, setSelected] = useState([])
  const [subjectIds, setSubjectIds] = useState([])
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)

  const sourceYear = form.source || String(activeYear)
  const targetYear = form.target || String(activeYear)

  useEffect(() => {
    if (!sourceYear) return
    let current = true
    progressionService.roster({
      academic_year_id: Number(sourceYear),
      class_id: form.sourceClass ? Number(form.sourceClass) : undefined,
      enrollment_status: form.action === 'CONFIRM_RETURN' ? 'PENDING_RETURN' : undefined,
    }).then(rows => {
      if (!current) return
      setRoster(rows); setSelected([]); setPreview(null); setError(null)
    }).catch(err => { if (current) setError(getErrorMessage(err)) })
    return () => { current = false }
  }, [sourceYear, form.sourceClass, form.action, message])

  const payload = useMemo(() => ({
    student_ids: selected,
    source_academic_year_id: Number(sourceYear),
    target_academic_year_id: Number(targetYear),
    target_class_id: Number(form.targetClass),
    action: form.action,
    subject_ids: subjectIds,
  }), [selected, form, subjectIds, sourceYear, targetYear])

  async function review() {
    setBusy(true); setError(null); setMessage(null)
    try { setPreview(await progressionService.preview(payload)) }
    catch (err) { setError(getErrorMessage(err)) }
    finally { setBusy(false) }
  }

  async function confirm() {
    setBusy(true); setError(null)
    try {
      const result = form.action === 'CONFIRM_RETURN'
        ? await progressionService.confirmReturn(selected, Number(sourceYear))
        : await progressionService.confirm(payload)
      setMessage(result.detail); setPreview(null); setSelected([])
    } catch (err) { setError(getErrorMessage(err)) }
    finally { setBusy(false) }
  }

  const yearOptions = years.map(year => ({ value: year.id, label: year.name }))
  const classOptions = classes.filter(row => row.is_active).map(row => ({ value: row.id, label: `${row.name} · ${pretty(row.form_level)}` }))
  const columns = [
    { key: 'pick', header: <input type="checkbox" aria-label="Select all students" checked={roster.length > 0 && selected.length === roster.length} onChange={event => setSelected(event.target.checked ? roster.map(row => row.student_id) : [])} />, render: row => <input type="checkbox" aria-label={`Select ${row.student_name}`} checked={selected.includes(row.student_id)} onChange={() => setSelected(values => values.includes(row.student_id) ? values.filter(id => id !== row.student_id) : [...values, row.student_id])} /> },
    { key: 'student_number', header: 'Student number', primary: true },
    { key: 'student_name', header: 'Student' },
    { key: 'class_name', header: 'Current placement', render: row => <div>{row.class_name}<div className="mt-1 text-xs text-ink-500">{pretty(row.form_level)}</div></div> },
    { key: 'status', header: 'Status', render: row => <Badge status={row.status}>{pretty(row.status)}</Badge> },
  ]

  return <div>
    <PageHeader title="Student progression" description="Prepare annual placements, review every move, then confirm student returns separately." />
    {error && <Alert tone="danger" title="Progression could not be completed" className="mb-5">{error}</Alert>}
    {message && <Alert tone="success" title="Register updated" className="mb-5">{message}</Alert>}
    <Card className="mb-6 p-5 sm:p-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Select label="Action" value={form.action} options={ACTIONS} onChange={event => setForm(value => ({ ...value, action: event.target.value }))} />
        <Select label="Source academic year" value={sourceYear} options={yearOptions} placeholder="Choose a year" onChange={event => setForm(value => ({ ...value, source: event.target.value }))} />
        <Select label="Source class" value={form.sourceClass} options={classOptions} placeholder="All classes" onChange={event => setForm(value => ({ ...value, sourceClass: event.target.value }))} />
        {form.action !== 'CONFIRM_RETURN' && <>
          <Select label="Target academic year" value={targetYear} options={yearOptions} placeholder="Choose a year" onChange={event => setForm(value => ({ ...value, target: event.target.value }))} />
          <Select label="Target class" value={form.targetClass} options={classOptions} placeholder="Choose a class" onChange={event => setForm(value => ({ ...value, targetClass: event.target.value }))} />
        </>}
      </div>
      {form.action === 'O_LEVEL_TO_A_LEVEL' && <div className="mt-5 border-t border-ink-200 pt-5"><h2 className="mb-3 text-sm font-semibold">New A-Level subjects</h2><SubjectPicker subjects={subjects.filter(row => row.is_active && ['A_LEVEL', 'BOTH'].includes(row.level))} selectedIds={subjectIds} onChange={setSubjectIds} /></div>}
    </Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3"><h2 className="section-heading">Students <span className="ml-2 text-xs font-normal text-ink-500">{selected.length} selected</span></h2><div className="flex gap-2">{form.action !== 'CONFIRM_RETURN' && <Button variant="secondary" onClick={review} disabled={!selected.length || !targetYear || !form.targetClass} loading={busy}>Preview</Button>}<Button onClick={confirm} disabled={!selected.length || (form.action !== 'CONFIRM_RETURN' && !preview?.can_confirm)} loading={busy}>{form.action === 'CONFIRM_RETURN' ? 'Confirm return' : 'Confirm placement'}</Button></div></div>
    {preview && <Alert tone={preview.can_confirm ? 'success' : 'warning'} title="Placement preview" className="mb-5">{preview.detail}<ul className="mt-2 space-y-1 text-sm">{preview.rows.filter(row => !row.valid).map(row => <li key={row.student_id}>{row.student_number}: {row.message}</li>)}</ul></Alert>}
    <Card><DataTable columns={columns} rows={roster} rowKey={row => row.student_id} loading={busy && !roster.length} empty={<p className="p-8 text-center text-sm text-ink-500">No students match this year, class and status.</p>} /></Card>
  </div>
}

export default ProgressionPage
