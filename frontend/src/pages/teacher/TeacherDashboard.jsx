import { useState } from 'react'

import EmptyState from '@/components/common/EmptyState'
import PageHeader from '@/components/common/PageHeader'
import StatTile from '@/components/common/StatTile'
import Toast from '@/components/common/Toast'
import SubjectCard from '@/components/teacher/SubjectCard'
import { Alert, Button, Card, CardBody, PageLoader } from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { teacherPortalService } from '@/services/teacherService'

/**
 * Teacher overview.
 *
 * One card per assigned subject. Subjects that are not assigned to this teacher
 * never appear, and the server would refuse them anyway.
 */
export function TeacherDashboard() {
  useDocumentTitle('Dashboard')

  const { data, loading, error, refresh } = useAsyncData(
    () => teacherPortalService.dashboard(),
    [],
  )
  const { toast, show, clear } = useToast()
  const [refreshing, setRefreshing] = useState(false)

  async function handleRefresh() {
    setRefreshing(true)
    await refresh()
    setRefreshing(false)
  }

  if (loading && !data) return <PageLoader label="Loading your subjects" />

  const hasExam = Boolean(data?.current_examination)

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${data?.teacher_name?.split(' ')[0] ?? 'Teacher'}`}
        description={
          hasExam
            ? `${data.current_examination} · ${data.term_name}${data.academic_year_name ? `, ${data.academic_year_name}` : ''}`
            : 'No examination is currently open.'
        }
        actions={
          <Button
            variant="secondary"
            size="sm"
            icon="rotate"
            onClick={handleRefresh}
            loading={refreshing}
          >
            Refresh
          </Button>
        }
      />

      {error && (
        <Alert tone="danger" className="mb-5">
          {error}
        </Alert>
      )}

      {data?.overdue_subjects > 0 && (
        <Alert tone="danger" title="Marks are past due" className="mb-5">
          {data.overdue_subjects === 1
            ? 'One of your subjects is past its submission deadline.'
            : `${data.overdue_subjects} of your subjects are past their submission deadline.`}{' '}
          Upload the outstanding marks as soon as you can.
        </Alert>
      )}

      {data?.total_subjects > 0 && (
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <StatTile
            icon="table-list"
            label="My subjects"
            value={data.total_subjects}
            hint="Assigned this year"
          />
          <StatTile
            icon="circle-check"
            label="Submitted"
            value={data.submitted_subjects}
            hint="Marks delivered"
          />
          <StatTile
            icon="clock"
            label="Outstanding"
            value={data.outstanding_subjects}
            hint={data.overdue_subjects > 0 ? `${data.overdue_subjects} overdue` : 'Still to submit'}
          />
        </div>
      )}

      {data?.subjects?.length > 0 ? (
        <div className="grid gap-5 lg:grid-cols-2">
          {data.subjects.map((card) => (
            <SubjectCard
              key={`${card.examination_id}-${card.subject_id}`}
              card={card}
              onDownloadError={(message) => show(message, 'danger')}
            />
          ))}
        </div>
      ) : (
        !error && (
          <Card>
            <CardBody className="p-0">
              <EmptyState
                icon="table-list"
                title={hasExam ? 'No subjects assigned to you' : 'No examination is open'}
                description={
                  hasExam
                    ? 'The school office assigns subjects to teachers. Contact them if this looks wrong.'
                    : 'Once the school opens an examination for submission, your subjects will appear here.'
                }
              />
            </CardBody>
          </Card>
        )
      )}

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default TeacherDashboard
