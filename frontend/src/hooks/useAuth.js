import { useContext } from 'react'

import { AuthContext } from '@/context/authContext'

/** Access the authenticated session. Must be used inside <AuthProvider>. */
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an <AuthProvider>.')
  }
  return context
}

export default useAuth
