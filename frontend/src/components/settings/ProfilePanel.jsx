import { Badge, Card, CardBody, CardHeader } from '@/components/ui'
import useAuth from '@/hooks/useAuth'
import { formatDate } from '@/utils/format'
import { roleLabel } from '@/utils/roles'

function Row({ label, children }) {
  return (
    <div className="border-ink-100 flex flex-col gap-1 border-b py-3 last:border-b-0 sm:flex-row sm:items-center sm:gap-4">
      <dt className="text-ink-500 w-full text-sm sm:w-56 sm:shrink-0">{label}</dt>
      <dd className="text-ink-900 min-w-0 text-sm font-medium">{children}</dd>
    </div>
  )
}

/**
 * Read-only profile.
 *
 * Names, student numbers and employee numbers are school records rather than
 * personal preferences, so they are changed by an administrator, not here.
 */
export function ProfilePanel() {
  const { user } = useAuth()
  if (!user) return null

  return (
    <Card>
      <CardHeader
        icon="user-graduate"
        title="Profile"
        description="Your details as recorded by the school."
      />
      <CardBody>
        <dl>
          <Row label="Full name">{user.full_name}</Row>
          <Row label="Email address">{user.email}</Row>
          {user.username && <Row label="Username">{user.username}</Row>}
          <Row label="Role">{roleLabel(user.role)}</Row>

          {user.student_number && <Row label="Student number">{user.student_number}</Row>}
          {user.class_name && <Row label="Class">{user.class_name}</Row>}
          {user.employee_number && <Row label="Employee number">{user.employee_number}</Row>}

          <Row label="Account status">
            <Badge tone={user.is_active ? 'success' : 'danger'}>
              {user.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </Row>
          <Row label="Member since">{formatDate(user.created_at)}</Row>
        </dl>

        <p className="text-ink-500 mt-5 text-sm">
          To correct any of these details, contact the school office.
        </p>
      </CardBody>
    </Card>
  )
}

export default ProfilePanel
