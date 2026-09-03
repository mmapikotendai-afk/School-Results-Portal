import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { Link, Outlet } from 'react-router-dom'

import Logo from '@/components/common/Logo'
import { SCHOOL } from '@/utils/constants'

const HIGHLIGHTS = [
  { icon: 'file-csv', text: 'Upload examination results straight from a CSV file' },
  { icon: 'shield-halved', text: 'Every mark matched to a verified student number' },
  { icon: 'file-pdf', text: 'School-branded report cards, ready to print or download' },
]

/**
 * Two-column shell for the sign-in screen: a branded panel on large screens,
 * and the form alone on small ones.
 */
export function AuthLayout() {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      {/* Branded panel - decorative, hidden on small screens. */}
      <aside className="bg-brand-950 relative hidden flex-col justify-between overflow-hidden p-10 lg:flex xl:p-14">
        <div
          aria-hidden="true"
          className="bg-brand-800/40 absolute -top-24 -right-24 size-96 rounded-full blur-3xl"
        />
        <div
          aria-hidden="true"
          className="bg-accent-500/10 absolute -bottom-32 -left-20 size-96 rounded-full blur-3xl"
        />

        <Link to="/" className="relative z-10 w-fit rounded-lg">
          <Logo inverted size="lg" />
        </Link>

        <div className="relative z-10 max-w-md">
          <h2 className="font-serif text-3xl leading-tight font-semibold text-white xl:text-4xl">
            Examination results, gathered and published with confidence.
          </h2>
          <p className="text-brand-200 mt-4 text-sm leading-relaxed">
            {SCHOOL.name} uses this portal to collect marks from every teacher, combine
            them into one record per student, and release verified report cards.
          </p>

          <ul className="mt-8 space-y-4">
            {HIGHLIGHTS.map((item) => (
              <li key={item.text} className="flex items-start gap-3">
                <span className="bg-brand-900/80 text-accent-300 ring-brand-800 mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg ring-1">
                  <FontAwesomeIcon icon={item.icon} className="text-xs" aria-hidden="true" />
                </span>
                <span className="text-brand-100 text-sm">{item.text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-brand-300 relative z-10 text-xs">
          {SCHOOL.motto || `© ${new Date().getFullYear()} ${SCHOOL.name}`}
        </p>
      </aside>

      {/* Form column */}
      <main className="flex items-center justify-center px-5 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-8 inline-block rounded-lg lg:hidden">
            <Logo size="md" />
          </Link>
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default AuthLayout
