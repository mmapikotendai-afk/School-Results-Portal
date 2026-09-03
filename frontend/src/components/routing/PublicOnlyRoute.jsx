import { Navigate, Outlet } from 'react-router-dom'

import { PageLoader } from '@/components/ui'
import useAuth from '@/hooks/useAuth'
import { homePathForRole } from '@/utils/roles'

/** Keeps signed-in users away from the login screen. */
export function PublicOnlyRoute() {
  const { isAuthenticated, initialising, user } = useAuth()

  if (initialising) return <PageLoader label="Loading" />
  if (isAuthenticated) return <Navigate to={homePathForRole(user.role)} replace />

  return <Outlet />
}

export default PublicOnlyRoute
