import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link, useLocation } from 'react-router-dom'
import Logo from '@/components/common/Logo'
import { navigationFor } from '@/layouts/navigation'
import { cx } from '@/utils/format'
import { roleLabel } from '@/utils/roles'

export function Sidebar({ role, collapsed = false, onNavigate, onToggle, onClose }) {
  const groups = navigationFor(role)
  const { pathname } = useLocation()
  const active = groups.flatMap(group => group.items).filter(item => pathname === item.to || pathname.startsWith(item.to + '/')).sort((a,b) => b.to.length - a.to.length)[0]?.to
  return (
    <div className="navigation-rail flex h-full flex-col border-r border-ink-200">
      <div className={cx('flex min-h-24 items-center gap-2 px-5 py-5', collapsed && 'justify-center px-3')}>
        <Link to={'/' + role?.toLowerCase() + '/dashboard'} onClick={onNavigate} aria-label="School workspace" className="min-w-0 flex-1"><Logo size="md" showText={!collapsed} className={collapsed ? 'justify-center' : ''} /></Link>
        {onClose && <button type="button" onClick={onClose} aria-label="Close navigation" className="rounded-md p-3 text-ink-600 hover:bg-ink-200"><FontAwesomeIcon icon="xmark" /></button>}
      </div>
      <div className={cx('mx-4 mb-3 border-y border-ink-200 py-3 text-xs text-ink-500', collapsed && 'text-center')}>
        {collapsed ? <FontAwesomeIcon icon="school" title={roleLabel(role)} /> : roleLabel(role) + ' workspace'}
      </div>
      <nav className="min-h-0 flex-1 overflow-y-auto px-3 pb-4" aria-label="Main navigation">
        {groups.map((group, index) => (
          <div key={group.section ?? index} className={index > 0 ? 'mt-5' : ''}>
            {group.section && !collapsed && <p className="mb-1.5 px-3 text-[11px] font-medium text-ink-500">{group.section}</p>}
            {group.section && collapsed && <div className="mx-3 mb-3 border-t border-ink-200" />}
            <div className="space-y-0.5">
              {group.items.map(item => (
                <Link key={item.to} to={item.to} onClick={onNavigate} title={collapsed ? item.label : undefined} aria-label={collapsed ? item.label : undefined} aria-current={active === item.to ? 'page' : undefined}
                  className={cx('nav-item', collapsed && 'justify-center px-0', active === item.to ? 'bg-white font-semibold text-brand-900 shadow-nav' : 'text-ink-600 hover:bg-ink-200/50 hover:text-ink-900')}>
                  <FontAwesomeIcon icon={item.icon} className={cx('w-4 shrink-0 text-[13px]', active === item.to ? 'text-brand-800' : 'text-ink-500')} aria-hidden="true" />
                  {!collapsed && <span className="min-w-0 flex-1">{item.label}</span>}
                  {!collapsed && active === item.to && <span className="size-1 rounded-full bg-accent-700" aria-hidden="true" />}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-ink-200 px-3 py-3">
        {onToggle ? <button type="button" onClick={onToggle} aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'} aria-expanded={!collapsed} className={cx('nav-item w-full text-ink-500 hover:bg-ink-200/50', collapsed && 'justify-center px-0')}>
          <FontAwesomeIcon icon={collapsed ? 'chevron-right' : 'chevron-left'} className="w-4 text-xs" />{!collapsed && <span>Collapse navigation</span>}
        </button> : <p className="px-3 text-xs text-ink-500">School results & records</p>}
      </div>
    </div>
  )
}
export default Sidebar
