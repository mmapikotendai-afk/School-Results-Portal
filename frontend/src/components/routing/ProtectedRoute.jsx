import { Navigate, Outlet } from 'react-router-dom'

import { PageLoader } from '@/components/ui'
import useAuth from '@/hooks/useAuth'
import { homePathForRole } from '@/utils/roles'

/**
 * Gate for authenticated routes.
 *
 * Pass `allowedRoles` to restrict a branch to particular roles; a signed-in
 * user with the wrong role is sent to their own home rather than to /login,
 * which would look like a failed sign-in.
 *
 * A signed-out visitor goes to /login with no memory of where they were
 * heading. Links to pages inside the portal get pasted into messages and
 * forwarded, and signing in must always begin at the account's own home
 * rather than wherever a shared link happened to point.
 */
export function ProtectedRoute({ allowedRoles }) {
  const { isAuthenticated, initialising, user } = useAuth()

  if (initialising) {
    return <PageLoader label="Restoring your session" />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles?.length && !allowedRoles.includes(user.role)) {
    return <Navigate to={homePathForRole(user.role)} replace />
  }

  return <Outlet />
}

export default ProtectedRoute
