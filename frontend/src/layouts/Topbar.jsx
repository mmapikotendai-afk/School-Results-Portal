import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui'
import { flatNavigationFor } from '@/layouts/navigation'
import useAuth from '@/hooks/useAuth'
import { initials } from '@/utils/format'
import { roleLabel, settingsPathForRole } from '@/utils/roles'

/** Portal header: mobile menu trigger, identity chip, settings and sign-out. */
export function Topbar({ onOpenMenu }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [signingOut, setSigningOut] = useState(false)

  const identifier = user?.student_number || user?.employee_number

  // Where am I? The sidebar answers this on a laptop, but it is hidden on a
  // phone, so the header carries the current page name instead.
  const current = flatNavigationFor(user?.role).find((item) =>
    location.pathname.startsWith(item.to),
  )

  async function handleSignOut() {
    setSigningOut(true)
    // Revokes the token on the server, then clears local state.
    await signOut()
    navigate('/login', { replace: true })
  }

  return (
    <header className="border-ink-200 sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-white/90 px-4 backdrop-blur sm:px-6">
      <button
        type="button"
        onClick={onOpenMenu}
        className="text-ink-600 hover:bg-ink-100 -ml-1 rounded-lg p-2 transition-colors lg:hidden"
        aria-label="Open navigation menu"
      >
        <FontAwesomeIcon icon="bars" />
      </button>

      {current && (
        <p className="text-ink-900 min-w-0 truncate text-sm font-semibold lg:hidden">
          {current.label}
        </p>
      )}

      <div className="flex-1" />

      <div className="flex items-center gap-2 sm:gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-ink-900 text-sm leading-tight font-semibold">{user?.full_name}</p>
          <p className="text-ink-500 text-xs">
            {roleLabel(user?.role)}
            {identifier ? ` · ${identifier}` : ''}
          </p>
        </div>

        <Link
          to={settingsPathForRole(user?.role)}
          className="text-ink-500 hover:bg-ink-100 hover:text-ink-900 rounded-lg p-2 transition-colors"
          aria-label="Settings"
          title="Settings"
        >
          <FontAwesomeIcon icon="gear" />
        </Link>

        <span
          className="bg-brand-100 text-brand-800 flex size-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold"
          aria-hidden="true"
        >
          {initials(user?.full_name)}
        </span>

        <Button
          variant="ghost"
          size="sm"
          icon="arrow-right-from-bracket"
          onClick={handleSignOut}
          loading={signingOut}
          aria-label="Sign out"
        >
          <span className="hidden sm:inline">{signingOut ? 'Signing out' : 'Sign out'}</span>
        </Button>
      </div>
    </header>
  )
}

export default Topbar
