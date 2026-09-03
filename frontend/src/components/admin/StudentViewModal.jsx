import { useEffect, useState } from 'react'

import { Alert, Badge, Button, Modal, Spinner } from '@/components/ui'
import { studentService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'
import { formatDate } from '@/utils/format'

function Row({ label, children }) {
  return (
    <div className="border-ink-100 flex flex-col gap-1 border-b py-2.5 last:border-b-0 sm:flex-row sm:gap-4">
      <dt className="text-ink-500 w-full text-sm sm:w-40 sm:shrink-0">{label}</dt>
      <dd className="text-ink-900 min-w-0 text-sm font-medium">{children}</dd>
    </div>
  )
}

/** Read-only student record, including subjects currently studied and dropped. */
export function StudentViewModal({ open, studentId, onClose, onEdit, onManageSubjects }) {
  const [student, setStudent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    studentService
      .get(studentId)
      .then((data) => !cancelled && setStudent(data))
      .catch((err) => !cancelled && setError(getErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [studentId])

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={student?.full_name ?? 'Student'}
      description={student?.student_number}
      footer={
        student && (
          <>
            <Button variant="secondary" icon="table-list" onClick={() => onManageSubjects(student)}>
              Manage subjects
            </Button>
            <Button icon="pen-to-square" onClick={() => onEdit(student)}>
              Edit
            </Button>
          </>
        )
      }
    >
      {loading && (
        <div className="flex items-center justify-center gap-3 py-10">
          <Spinner />
          <span className="text-ink-500 text-sm">Loading…</span>
        </div>
      )}

      {error && <Alert tone="danger">{error}</Alert>}

      {student && (
        <div className="space-y-5">
          <dl>
            <Row label="Student number">
              <span className="font-mono">{student.student_number}</span>
            </Row>
            <Row label="Class">
              {student.school_class ? (
                <>
                  {student.school_class.name}
                  <span className="text-ink-400 ml-2 text-xs">
                    {student.level === 'O_LEVEL' ? 'O-Level' : 'A-Level'}
                  </span>
                </>
              ) : (
                <span className="text-ink-400">Unassigned</span>
              )}
            </Row>
            <Row label="Date of birth">{formatDate(student.date_of_birth)}</Row>
            <Row label="Gender">{student.gender ?? '—'}</Row>
            <Row label="Email">{student.email}</Row>
            <Row label="Status">
              <Badge tone={student.is_active ? 'success' : 'neutral'}>
                {student.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </Row>
          </dl>

          <div>
            <p className="text-ink-700 mb-2 text-sm font-medium">
              Subjects studied ({student.subjects.length})
            </p>
            {student.subjects.length ? (
              <div className="flex flex-wrap gap-1.5">
                {student.subjects.map((s) => (
                  <Badge key={s.id} tone="brand">
                    {s.name}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-ink-400 text-sm">Not enrolled in any subjects yet.</p>
            )}
          </div>

          {student.dropped_subjects.length > 0 && (
            <div>
              <p className="text-ink-700 mb-2 text-sm font-medium">
                Dropped this year ({student.dropped_subjects.length})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {student.dropped_subjects.map((s) => (
                  <Badge key={s.id} tone="neutral">
                    {s.name}
                  </Badge>
                ))}
              </div>
              <p className="text-ink-400 mt-2 text-xs">
                Enrollment history and any recorded results are kept.
              </p>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

export default StudentViewModal
