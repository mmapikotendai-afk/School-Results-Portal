import { useMemo, useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link, useNavigate } from 'react-router-dom'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import CredentialSlips from '@/components/admin/CredentialSlips'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  Input,
  PageLoader,
  Select,
  SubjectPicker,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import {
  academicService,
  classService,
  studentImportService,
  subjectService,
} from '@/services/adminService'
import { adminDownloads } from '@/services/adminDownloads'
import { getErrorMessage } from '@/services/apiClient'
import { cx } from '@/utils/format'

/**
 * Enrol a whole class from one CSV file.
 *
 * Three steps, and the middle one is the point: choose, preview, confirm.
 * Nothing is created until the administrator has seen every row the file
 * contains and the server has accepted all of them.
 *
 * The class is chosen here rather than read from the file. A class column
 * would let one mistyped cell put a Form 1 learner into Upper 6, with nothing
 * on screen to suggest anyone should look - so the file carries only who the
 * students are, and the class chosen here applies to all of them.
 */
export function StudentImportPage() {
  useDocumentTitle('Bulk Import Students')

  const navigate = useNavigate()
  const { toast, show, clear } = useToast()

  const { data: years, loading: loadingYears } = useAsyncData(
    () => academicService.listYears(),
    [],
  )
  const { data: classes, loading: loadingClasses } = useAsyncData(
    () => classService.list({ include_inactive: false }),
    [],
  )
  const { data: subjects } = useAsyncData(
    // Retired subjects are refused by the server, so they are not offered.
    () => subjectService.list({ include_inactive: false }),
    [],
  )

  const [yearId, setYearId] = useState('')
  const [classId, setClassId] = useState('')
  const [subjectIds, setSubjectIds] = useState([])
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)

  const [report, setReport] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)
  const [showAllRows, setShowAllRows] = useState(false)
  const [adminPassword, setAdminPassword] = useState('')

  const input = useRef(null)

  const activeYear = useMemo(() => (years ?? []).find((y) => y.is_active), [years])
  const effectiveYearId = yearId || (activeYear ? String(activeYear.id) : '')
  const chosenClass = (classes ?? []).find((c) => String(c.id) === String(classId))

  function chooseFile(selected) {
    setError(null)
    setReport(null)
    setResult(null)
    if (!selected) return
    if (!selected.name.toLowerCase().endsWith('.csv')) {
      setError('Upload a CSV file. Export your spreadsheet as CSV first.')
      return
    }
    setFile(selected)
  }

  async function downloadTemplate() {
    setBusy('template')
    try {
      const name = await adminDownloads.studentImportTemplate()
      show(`Downloaded ${name}`)
    } catch (err) {
      show(getErrorMessage(err, 'That download did not work.'), 'danger')
    } finally {
      setBusy(null)
    }
  }

  async function validate() {
    setBusy('validate')
    setError(null)
    try {
      setReport(
        await studentImportService.preview({
          file,
          classId,
          academicYearId: effectiveYearId || null,
          subjectIds,
        }),
      )
      setShowAllRows(false)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  async function confirmImport() {
    setBusy('import')
    setError(null)
    try {
      const outcome = await studentImportService.commit({
        file,
        classId,
        academicYearId: effectiveYearId || null,
        subjectIds,
        adminPassword,
      })
      setAdminPassword('')
      setResult(outcome)
      setReport(null)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  function startOver() {
    setFile(null)
    setReport(null)
    setResult(null)
    setError(null)
  }

  if ((loadingYears && !years) || (loadingClasses && !classes)) {
    return <PageLoader label="Loading classes" />
  }

  const noYear = !effectiveYearId
  const rows = report?.rows ?? []
  const invalidRows = rows.filter((r) => !r.valid)
  const visibleRows =
    showAllRows || rows.length <= 12 || invalidRows.length === 0 ? rows : invalidRows

  // ------------------------------------------------------------- summary

  if (result) {
    return (
      <div>
        <PageHeader
          title="Students Imported"
          description={`${result.class_name} · ${result.students_created} added`}
        />

        <Card className="mb-5">
          <CardBody>
            <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Figure label="Students" value={result.students_created} tone="success" />
              <Figure label="Subject enrollments" value={result.enrollments_created} />
              <Figure label="Credentials issued" value={result.credentials_issued} tone="success" />
            </div>

            <Alert tone="success">
              {result.detail}
            </Alert>

            {result.failed?.length > 0 && (
              <Alert tone="danger" className="mt-4" title="Not created">
                <ul className="mt-1 space-y-1">
                  {result.failed.map((f) => (
                    <li key={f.row}>
                      {f.student_number}: {f.message}
                    </li>
                  ))}
                </ul>
              </Alert>
            )}

            {result.credentials?.length > 0 && (
              <div className="mt-5">
                <CredentialSlips slips={result.credentials} autoDownload />
              </div>
            )}
          </CardBody>
        </Card>

        <div className="flex flex-wrap gap-2">
          <Button onClick={() => navigate('/admin/students')} icon="user-graduate">
            View students
          </Button>
          <Button variant="secondary" onClick={startOver} icon="plus">
            Import another class
          </Button>
        </div>

        <Toast toast={toast} onDismiss={clear} />
      </div>
    )
  }

  // ------------------------------------------------------------- preview

  if (report) {
    return (
      <div>
        <PageHeader
          title="Import Preview"
          description={`${report.class_name} · ${report.academic_year_id ? '' : ''}${report.total_rows} student${report.total_rows === 1 ? '' : 's'} detected`}
          actions={
            <Button variant="ghost" onClick={() => setReport(null)} icon="arrow-left">
              Back
            </Button>
          }
        />

        {error && (
          <Alert tone="danger" className="mb-5" onDismiss={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Card className="mb-5">
          <CardBody>
            <div className="mb-4 grid grid-cols-3 gap-3">
              <Figure label="Detected" value={report.total_rows} />
              <Figure label="Valid" value={report.accepted} tone="success" />
              <Figure
                label="Errors"
                value={report.rejected}
                tone={report.rejected ? 'danger' : 'muted'}
              />
            </div>

            <Alert tone={report.can_import ? 'success' : 'danger'} title={
              report.can_import ? 'Ready to import' : 'Import blocked'
            }>
              {report.detail}
            </Alert>

            {report.subjects?.length > 0 && (
              <p className="text-ink-500 mt-3 text-sm">
                Each student will be enrolled in: {report.subjects.join(', ')}.
              </p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            icon="table-list"
            title={visibleRows === rows ? 'All rows' : `${invalidRows.length} rows to fix`}
            description={
              rows.length > 12 && invalidRows.length > 0 ? (
                <button
                  type="button"
                  onClick={() => setShowAllRows((v) => !v)}
                  className="text-brand-700 text-sm font-medium underline"
                >
                  {showAllRows ? 'Show problems only' : `Show all ${rows.length} rows`}
                </button>
              ) : undefined
            }
          />
          <div className="max-h-[28rem] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-ink-50 sticky top-0">
                <tr>
                  <Th>Row</Th>
                  <Th>Student number</Th>
                  <Th>Name</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody className="divide-ink-100 divide-y">
                {visibleRows.map((r) => (
                  <tr key={r.row} className={cx(!r.valid && 'bg-danger-50/40')}>
                    <td className="text-ink-400 px-3 py-2 text-xs tabular-nums">{r.row}</td>
                    <td className="text-ink-800 px-3 py-2 font-mono text-xs">
                      {r.student_number}
                    </td>
                    <td className="text-ink-700 px-3 py-2">
                      {[r.first_name, r.last_name].filter(Boolean).join(' ') || '—'}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={cx(
                          'flex items-start gap-1.5',
                          r.valid ? 'text-success-700' : 'text-danger-700',
                        )}
                      >
                        <FontAwesomeIcon
                          icon={r.valid ? 'circle-check' : 'circle-exclamation'}
                          className="mt-0.5 shrink-0 text-xs"
                          aria-hidden="true"
                        />
                        <span>{r.message}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <Button variant="secondary" onClick={() => setReport(null)}>
            Cancel
          </Button>
          <div className="flex items-center gap-3">
            <p className="text-ink-400 text-xs">
              {report.can_import
                ? 'Nothing has been created yet.'
                : 'Fix the file and upload it again.'}
            </p>
            <div className="min-w-[16rem]">
              <Input
                label="Administrator password"
                type="password"
                autoComplete="current-password"
                value={adminPassword}
                onChange={(event) => setAdminPassword(event.target.value)}
                hint="Required before issuing a batch of passwords."
              />
            </div>
            <Button
              onClick={confirmImport}
              loading={busy === 'import'}
              disabled={!report.can_import || !adminPassword}
              icon="check"
            >
              {busy === 'import'
                ? `Importing ${report.accepted}…`
                : `Confirm & import ${report.accepted} student${report.accepted === 1 ? '' : 's'}`}
            </Button>
          </div>
        </div>

        <Toast toast={toast} onDismiss={clear} />
      </div>
    )
  }

  // --------------------------------------------------------------- setup

  return (
    <div>
      <PageHeader
        title="Bulk Import Students"
        description="Enrol a whole class from one CSV file."
        actions={
          <Button as={Link} to="/admin/students" variant="ghost" icon="arrow-left">
            Students
          </Button>
        }
      />

      {error && (
        <Alert tone="danger" className="mb-5" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {noYear && (
        <Alert tone="warning" title="No current academic year" className="mb-5">
          Subject enrollments belong to a year, so one has to be current before students
          can be imported.{' '}
          <Link to="/admin/academic-years" className="font-semibold underline">
            Choose one
          </Link>
          .
        </Alert>
      )}

      <Card className="mb-5">
        <CardHeader
          icon="school"
          title="Where these students belong"
          description="Applied to every student in the file, so one file is one class."
        />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Academic year"
            value={effectiveYearId}
            onChange={(e) => setYearId(e.target.value)}
            options={(years ?? []).map((y) => ({
              value: y.id,
              label: y.is_active ? `${y.name} (current)` : y.name,
            }))}
          />
          <Select
            label="Class"
            value={classId}
            onChange={(e) => setClassId(e.target.value)}
            placeholder="Choose a class"
            options={(classes ?? []).map((c) => ({
              value: c.id,
              label: `${c.name} (${c.level === 'A_LEVEL' ? 'A-Level' : 'O-Level'})`,
            }))}
            hint="The CSV must not contain a class column."
          />
        </CardBody>
      </Card>

      <Card className="mb-5">
        <CardHeader
          icon="book"
          title="Starting subjects"
          description="Every imported student is enrolled in these. Individual students can be changed afterwards."
        />
        <CardBody>
          <SubjectPicker
            subjects={subjects ?? []}
            selectedIds={subjectIds}
            onChange={setSubjectIds}
          />
        </CardBody>
      </Card>

      <Card className="mb-5">
        <CardHeader
          icon="file-csv"
          title="Student CSV"
          description="first_name, last_name, date_of_birth, gender"
        />
        <CardBody>
          <div className="bg-brand-50 mb-4 flex items-start gap-3 rounded-lg px-4 py-3">
            <FontAwesomeIcon
              icon="circle-info"
              className="text-brand-700 mt-0.5"
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1 text-sm">
              <p className="text-brand-900">
                Start from the template. Student numbers are generated when you confirm.
              </p>
              <button
                type="button"
                onClick={downloadTemplate}
                disabled={busy === 'template'}
                className="text-brand-800 mt-1.5 font-semibold underline"
              >
                Download CSV template
              </button>
            </div>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              chooseFile(e.dataTransfer.files?.[0])
            }}
            className={cx(
              'rounded-lg border-2 border-dashed px-5 py-8 text-center transition-colors',
              dragging ? 'border-brand-500 bg-brand-50' : 'border-ink-300',
            )}
          >
            <FontAwesomeIcon
              icon={file ? 'file-csv' : 'cloud-arrow-up'}
              className={cx('text-2xl', file ? 'text-success-600' : 'text-ink-400')}
              aria-hidden="true"
            />
            {file ? (
              <div className="mt-2">
                <p className="text-ink-900 text-sm font-medium">{file.name}</p>
                <p className="text-ink-500 text-xs">{(file.size / 1024).toFixed(1)} KB</p>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="text-ink-500 hover:text-ink-800 mt-2 text-xs underline"
                >
                  Choose a different file
                </button>
              </div>
            ) : (
              <div className="mt-2">
                <p className="text-ink-700 text-sm">Drag a CSV file here, or</p>
                <button
                  type="button"
                  onClick={() => input.current?.click()}
                  className="text-brand-700 mt-1 text-sm font-semibold underline"
                >
                  browse for a file
                </button>
              </div>
            )}
            <input
              ref={input}
              type="file"
              aria-label="Choose a CSV file"
              accept=".csv,text/csv"
              className="sr-only"
              onChange={(e) => {
                chooseFile(e.target.files?.[0])
                e.target.value = ''
              }}
            />
          </div>
        </CardBody>
      </Card>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-ink-500 flex flex-wrap items-center gap-2 text-sm">
          {chosenClass ? (
            <>
              <Badge tone="brand">{chosenClass.name}</Badge>
              <span>
                {subjectIds.length} subject{subjectIds.length === 1 ? '' : 's'} selected
              </span>
            </>
          ) : (
            <span>Choose a class to continue.</span>
          )}
        </div>
        <Button
          onClick={validate}
          loading={busy === 'validate'}
          disabled={!file || !classId || noYear}
          icon="arrow-right"
          iconPosition="right"
        >
          Continue
        </Button>
      </div>

      {(classes ?? []).length === 0 && (
        <Card className="mt-5">
          <CardBody className="p-0">
            <EmptyState
              icon="school"
              title="No classes yet"
              description="Create a class before importing students into it."
            />
          </CardBody>
        </Card>
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

/** One counted figure in the preview and summary bands. */
function Figure({ label, value, tone = 'default' }) {
  const TONES = {
    default: 'bg-ink-50 text-ink-900',
    success: 'bg-success-50 text-success-700',
    danger: 'bg-danger-50 text-danger-700',
    muted: 'bg-ink-50 text-ink-400',
  }
  return (
    <div className={cx('rounded-lg px-4 py-3', TONES[tone])}>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      <p className="text-xs font-medium opacity-90">{label}</p>
    </div>
  )
}

function Th({ children }) {
  return (
    <th
      scope="col"
      className="text-ink-500 px-3 py-2 text-left text-xs font-semibold uppercase"
    >
      {children}
    </th>
  )
}

export default StudentImportPage
