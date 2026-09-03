import { useEffect, useMemo, useState } from 'react'
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
  CardHeader,
  PageLoader,
  Select,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { teacherDownloads, teacherPortalService } from '@/services/teacherService'
import { getErrorMessage } from '@/services/apiClient'
import { statusLabel } from '@/utils/constants'

/**
 * Every file a teacher can take away, in one place.
 *
 * The picker is built from the assignments the server returns, so it can never
 * offer a subject the download would refuse. Marks come from the database at
 * the moment of download, not from whatever CSV was uploaded originally.
 */
export function DownloadsPage() {
  useDocumentTitle('Downloads')

  const { data: options, loading, error } = useAsyncData(
    () => teacherPortalService.templateOptions(),
    [],
  )

  const [examId, setExamId] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [classId, setClassId] = useState('')
  const [classes, setClasses] = useState([])
  const [busy, setBusy] = useState(null)
  const { toast, show, clear } = useToast()

  // Distinct examinations, in the order the server returned them (newest first).
  const examinations = useMemo(() => {
    const seen = new Map()
    for (const option of options ?? []) {
      if (!seen.has(option.examination_id)) seen.set(option.examination_id, option)
    }
    return [...seen.values()]
  }, [options])

  const effectiveExamId =
    examId || (examinations.length ? String(examinations[0].examination_id) : '')

  const subjects = useMemo(
    () => (options ?? []).filter((o) => String(o.examination_id) === String(effectiveExamId)),
    [options, effectiveExamId],
  )

  const selected = useMemo(
    () => subjects.find((o) => String(o.subject_id) === String(subjectId)) ?? null,
    [subjects, subjectId],
  )

  // Changing the examination invalidates everything chosen beneath it.
  function chooseExamination(value) {
    setExamId(value)
    setSubjectId('')
    setClassId('')
    setClasses([])
  }

  function chooseSubject(value) {
    setSubjectId(value)
    setClassId('')
    setClasses([])
  }

  useEffect(() => {
    if (!selected) return undefined
    let cancelled = false
    teacherPortalService
      .classes(selected.examination_id, selected.subject_id)
      .then((rows) => !cancelled && setClasses(rows))
      // The class filter is optional, so a failure here just hides it.
      .catch(() => !cancelled && setClasses([]))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.examination_id, selected?.subject_id])

  async function run(kind, task) {
    setBusy(kind)
    try {
      const name = await task()
      show(`Downloaded ${name}`)
    } catch (err) {
      show(getErrorMessage(err, 'That download did not work.'), 'danger')
    } finally {
      setBusy(null)
    }
  }

  const rollSize = classId
    ? (classes.find((c) => String(c.class_id) === String(classId))?.student_count ?? 0)
    : (selected?.enrolled_count ?? 0)

  if (loading && !options) return <PageLoader label="Loading your subjects" />

  const FILES = selected
    ? [
        {
          id: 'template',
          icon: 'file-csv',
          title: 'Blank mark template',
          description: `Pre-filled with the ${rollSize} student${rollSize === 1 ? '' : 's'} on the roll. Fill in the marks column and upload it back.`,
          label: 'Download template',
          variant: 'primary',
          run: () =>
            teacherDownloads.template(
              selected.examination_id,
              selected.subject_id,
              selected.subject_code,
              classId || null,
            ),
        },
        {
          id: 'csv',
          icon: 'table-list',
          title: 'Recorded results (CSV)',
          description:
            'The marks currently on record, straight from the database. Corrections made in the portal appear here.',
          label: 'Download CSV',
          variant: 'secondary',
          run: () =>
            teacherDownloads.csv(
              selected.examination_id,
              selected.subject_id,
              selected.subject_code,
            ),
        },
        {
          id: 'pdf',
          icon: 'file-pdf',
          title: 'Mark sheet (PDF)',
          description: 'A printable mark sheet on the school masthead, for signing and filing.',
          label: 'Download PDF',
          variant: 'secondary',
          run: () =>
            teacherDownloads.pdf(
              selected.examination_id,
              selected.subject_id,
              selected.subject_code,
            ),
        },
      ]
    : []

  return (
    <div>
      <PageHeader
        title="Downloads"
        description="Templates, results and printable mark sheets for the subjects you teach."
      />

      {error && (
        <Alert tone="danger" title="Could not load your subjects" className="mb-5">
          {error}
        </Alert>
      )}

      {options?.length === 0 && !error ? (
        <Card>
          <CardBody className="p-0">
            <EmptyState
              icon="download"
              title="Nothing to download yet"
              description="Downloads appear once you have subjects assigned in an examination."
            />
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-5">
          <Card>
            <CardHeader
              icon="table-list"
              title="Choose a subject"
              description="Only the subjects assigned to you are listed."
            />
            <CardBody className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Select
                label="Examination"
                value={effectiveExamId}
                onChange={(e) => chooseExamination(e.target.value)}
                options={examinations.map((o) => ({
                  value: o.examination_id,
                  label: `${o.examination_name}${o.term_name ? ` · ${o.term_name}` : ''}`,
                }))}
              />
              <Select
                label="Subject"
                value={subjectId}
                onChange={(e) => chooseSubject(e.target.value)}
                placeholder="Choose a subject"
                options={subjects.map((o) => ({
                  value: o.subject_id,
                  label: `${o.subject_name} (${o.subject_code})`,
                }))}
              />
              <Select
                label="Class"
                value={classId}
                onChange={(e) => setClassId(e.target.value)}
                placeholder="All classes"
                options={classes.map((c) => ({
                  value: c.class_id,
                  label: `${c.class_name} (${c.student_count})`,
                }))}
                disabled={!selected || classes.length === 0}
                hint={
                  selected && classes.length === 0
                    ? 'This subject is taught as one group.'
                    : 'Narrows the template only.'
                }
              />
            </CardBody>

            {selected && (
              <div className="border-ink-200 bg-ink-50/60 flex flex-wrap items-center gap-x-4 gap-y-2 border-t px-5 py-3 text-sm">
                <span className="text-ink-900 font-medium">{selected.subject_name}</span>
                <Badge status={selected.examination_status}>
                  {statusLabel(selected.examination_status)}
                </Badge>
                <span className="text-ink-500">
                  <FontAwesomeIcon icon="user-graduate" className="mr-1.5" aria-hidden="true" />
                  {rollSize} student{rollSize === 1 ? '' : 's'}
                  {classId ? ' in this class' : ' on the roll'}
                </span>
              </div>
            )}
          </Card>

          {selected ? (
            <div className="grid gap-4 lg:grid-cols-3">
              {FILES.map((file) => (
                <Card key={file.id} className="flex flex-col">
                  <CardBody className="flex flex-1 flex-col">
                    <span className="bg-brand-50 text-brand-700 mb-3 flex size-10 items-center justify-center rounded-lg">
                      <FontAwesomeIcon icon={file.icon} aria-hidden="true" />
                    </span>
                    <h3 className="text-base font-semibold">{file.title}</h3>
                    <p className="text-ink-500 mt-1 flex-1 text-sm">{file.description}</p>
                    <Button
                      variant={file.variant}
                      icon="download"
                      className="mt-4"
                      fullWidth
                      loading={busy === file.id}
                      onClick={() => run(file.id, file.run)}
                    >
                      {file.label}
                    </Button>
                  </CardBody>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardBody className="p-0">
                <EmptyState
                  icon="download"
                  title="Choose a subject"
                  description="Pick one of your subjects above and its downloads will appear here."
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

export default DownloadsPage
