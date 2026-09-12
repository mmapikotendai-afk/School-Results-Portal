import { Link, Outlet } from 'react-router-dom'

import Logo from '@/components/common/Logo'
import { SCHOOL } from '@/utils/constants'

/**
 * Single-column shell for the sign-in screen: the form alone, centred in the
 * viewport at every breakpoint.
 *
 * The crest stands on its own above the form rather than beside a wordmark:
 * it already carries the school motto, and setting more type next to it only
 * competes with the heading below.
 *
 * The form now sits inside a ruled plate rather than floating on the page.
 * Signing in is the moment the portal states who issued it, so the frame,
 * the crest and the motto do that work together.
 */
export function AuthLayout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <div className="masthead-rule" aria-hidden="true" />

      <main className="flex flex-1 flex-col items-center justify-center px-5 py-12 sm:px-8">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-8 flex justify-center">
            <Logo size="xl" showText={false} />
          </Link>

          <div className="border-ink-900 border bg-white p-8 sm:p-10">
            <Outlet />
          </div>

          {SCHOOL.motto && (
            <p className="text-ink-500 mt-6 text-center font-serif text-sm italic">
              {SCHOOL.motto}
            </p>
          )}
        </div>
      </main>
    </div>
  )
}

export default AuthLayout
