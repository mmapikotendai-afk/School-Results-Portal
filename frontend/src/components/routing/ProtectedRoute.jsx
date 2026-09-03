import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { PageLoader } from '@/components/ui'
import useAuth from '@/hooks/useAuth'
import { homePathForRole } from '@/utils/roles'

/**
 * Gate for authenticated routes.
 *
 * Pass `allowedRoles` to restrict a branch to particular roles; a signed-in
 * user with the wrong role is sent to their own home rather than to /login,
 * which would look like a failed sign-in.
 */
export function ProtectedRoute({ allowedRoles }) {
  const { isAuthenticated, initialising, user } = useAuth()
  const location = useLocation()

  if (initialising) {
    return <PageLoader label="Restoring your session" />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles?.length && !allowedRoles.includes(user.role)) {
    return <Navigate to={homePathForRole(user.role)} replace />
  }

  return <Outlet />
}

export default ProtectedRoute
