import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import PageHeader from '@/components/common/PageHeader'
import ChangePasswordForm from '@/components/settings/ChangePasswordForm'
import ProfilePanel from '@/components/settings/ProfilePanel'
import SecurityPanel from '@/components/settings/SecurityPanel'
import SchoolPage from '@/pages/admin/SchoolPage'
import useAuth from '@/hooks/useAuth'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { cx } from '@/utils/format'
import { ROLES } from '@/utils/roles'

const BASE_TABS = [
  { id: 'profile', label: 'Profile', icon: 'user-graduate' },
  { id: 'security', label: 'Security', icon: 'shield-halved' },
  { id: 'password', label: 'Change Password', icon: 'lock' },
]

/**
 * Settings, shared by all three roles.
 *
 * The panels read from the signed-in user, so an administrator, a teacher and a
 * student each get the same screen showing their own details - there is no
 * role-specific copy of this page to keep in step. Administrators get one extra
 * tab for the school's own details, which is a setting rather than a screen of
 * its own.
 */
export function SettingsPage() {
  useDocumentTitle('Settings')
  const { user } = useAuth()
  const [active, setActive] = useState('profile')

  const isAdmin = user?.role === ROLES.ADMIN
  const tabs = isAdmin
    ? [...BASE_TABS, { id: 'school', label: 'School Information', icon: 'school' }]
    : BASE_TABS

  return (
    <div>
      <PageHeader
        title="Settings"
        description={
          isAdmin
            ? 'Your profile, account security, and the school details printed on report cards.'
            : 'Your profile, account security and password.'
        }
      />

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        {/* Tabs: a vertical rail on desktop, a scrollable row on mobile. */}
        <nav
          className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 lg:mx-0 lg:flex-col lg:overflow-visible lg:px-0 lg:pb-0"
          aria-label="Settings sections"
        >
          {tabs.map((tab) => {
            const isActive = active === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActive(tab.id)}
                aria-current={isActive ? 'page' : undefined}
                className={cx(
                  'flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-50 text-brand-800'
                    : 'text-ink-600 hover:bg-ink-100 hover:text-ink-900',
                )}
              >
                <FontAwesomeIcon icon={tab.icon} className="w-4" aria-hidden="true" />
                {tab.label}
              </button>
            )
          })}
        </nav>

        <div className="min-w-0">
          {active === 'profile' && <ProfilePanel />}
          {active === 'security' && (
            <SecurityPanel onChangePassword={() => setActive('password')} />
          )}
          {active === 'password' && <ChangePasswordForm />}
          {active === 'school' && isAdmin && <SchoolPage embedded />}
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
