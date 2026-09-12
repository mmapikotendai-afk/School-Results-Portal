import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { NavLink } from 'react-router-dom'

import Logo from '@/components/common/Logo'
import { navigationFor } from '@/layouts/navigation'
import { cx } from '@/utils/format'
import { roleLabel } from '@/utils/roles'

/** Primary navigation. Rendered inline on desktop and in a drawer on mobile. */
export function Sidebar({ role, onNavigate }) {
  const groups = navigationFor(role)

  return (
    <div className="bg-brand-950 flex h-full w-72 flex-col">
      <div className="border-brand-900 flex h-16 shrink-0 items-center border-b px-5">
        <Logo inverted size="sm" />
      </div>

      <div className="border-brand-900 border-b px-5 py-3">
        <p className="text-brand-300 text-[11px] font-bold tracking-[0.16em] uppercase">
          {roleLabel(role)}
        </p>
      </div>

      <nav className="scrollbar-none flex-1 overflow-y-auto px-3 py-4" aria-label="Main">
        {groups.map((group, index) => (
          <div key={group.section ?? `group-${index}`} className={cx(index > 0 && 'mt-5')}>
            {group.section && (
              <p className="text-brand-300/90 px-3 pb-2 text-[11px] font-bold tracking-[0.16em] uppercase">
                {group.section}
              </p>
            )}

            <div className="space-y-1">
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cx(
                      'nav-item group relative',
                      isActive
                        ? 'bg-brand-800 font-semibold text-white'
                        : 'text-brand-200 hover:bg-brand-900 hover:text-white',
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {/* A marker on the active item, so the current page is
                          readable at a glance and not by colour alone. */}
                      <span
                        className={cx(
                          'bg-accent-500 absolute top-0 bottom-0 left-0 w-[3px] transition-opacity',
                          isActive ? 'opacity-100' : 'opacity-0',
                        )}
                        aria-hidden="true"
                      />
                      <FontAwesomeIcon
                        icon={item.icon}
                        className="w-4 shrink-0"
                        aria-hidden="true"
                      />
                      <span className="truncate">{item.label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-brand-900 text-brand-300 shrink-0 border-t px-5 py-4 text-[11px] tracking-wide">
        Results Portal &middot; v0.1.0
      </div>
    </div>
  )
}

export default Sidebar
