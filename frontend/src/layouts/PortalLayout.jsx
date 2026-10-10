import { useEffect, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from '@/layouts/Sidebar'
import Topbar from '@/layouts/Topbar'
import useAuth from '@/hooks/useAuth'

export function PortalLayout() {
  const { user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('portal.nav.collapsed') === 'true')
  const drawer = useRef(null)
  const location = useLocation()
  const [lastPath, setLastPath] = useState(location.pathname)
  if (lastPath !== location.pathname) { setLastPath(location.pathname); setMenuOpen(false) }
  useEffect(() => {
    const node = drawer.current
    if (menuOpen && !node.open) node.showModal()
    else if (!menuOpen && node.open) node.close()
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [menuOpen])
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 1024px)')
    const closeOnDesktop = event => { if (event.matches) setMenuOpen(false) }
    desktop.addEventListener('change', closeOnDesktop)
    return () => desktop.removeEventListener('change', closeOnDesktop)
  }, [])
  function toggleRail() {
    setCollapsed(value => {
      localStorage.setItem('portal.nav.collapsed', String(!value))
      return !value
    })
  }
  return (
    <div className="portal-shell flex min-h-dvh" data-collapsed={collapsed}>
      <a href="#main-content" className="skip-link">Skip to content</a>
      <aside className="portal-rail hidden shrink-0 lg:block">
        <div className="portal-rail fixed inset-y-0 left-0 z-40">
          <Sidebar role={user?.role} collapsed={collapsed} onToggle={toggleRail} />
        </div>
      </aside>
      <dialog ref={drawer} aria-label="Navigation" className="nav-drawer" onCancel={() => setMenuOpen(false)} onClose={() => setMenuOpen(false)} onClick={event => { if (event.target === event.currentTarget) setMenuOpen(false) }}>
        <div className="h-full w-[min(288px,85vw)]">
          <Sidebar role={user?.role} onNavigate={() => setMenuOpen(false)} onClose={() => setMenuOpen(false)} />
        </div>
      </dialog>
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenMenu={() => setMenuOpen(true)} menuOpen={menuOpen} />
        <main id="main-content" tabIndex={-1} className="flex-1 px-4 py-7 outline-none sm:px-7 lg:px-9 lg:py-9">
          <div className="mx-auto w-full max-w-[1320px]"><Outlet /></div>
        </main>
      </div>
    </div>
  )
}
export default PortalLayout
