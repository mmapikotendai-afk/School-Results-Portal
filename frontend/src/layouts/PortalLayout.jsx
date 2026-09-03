import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import Sidebar from '@/layouts/Sidebar'
import Topbar from '@/layouts/Topbar'
import useAuth from '@/hooks/useAuth'

/** Authenticated shell: fixed sidebar on desktop, slide-over drawer on mobile. */
export function PortalLayout() {
  const { user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  // Close the drawer whenever the route changes. Adjusting state during
  // render (rather than in an effect) avoids a second render pass.
  const [lastPath, setLastPath] = useState(location.pathname)
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname)
    setMenuOpen(false)
  }

  // Stop the page behind the drawer from scrolling.
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [menuOpen])

  return (
    <div className="flex min-h-dvh">
      <div className="hidden shrink-0 lg:block">
        <div className="fixed inset-y-0 left-0 w-72">
          <Sidebar role={user?.role} />
        </div>
        <div className="w-72" aria-hidden="true" />
      </div>

      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            className="bg-ink-900/50 absolute inset-0"
            onClick={() => setMenuOpen(false)}
            aria-label="Close navigation menu"
          />
          <div className="shadow-overlay absolute inset-y-0 left-0">
            <Sidebar role={user?.role} onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenMenu={() => setMenuOpen(true)} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default PortalLayout
