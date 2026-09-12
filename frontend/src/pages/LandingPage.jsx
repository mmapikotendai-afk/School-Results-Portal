import { Link } from 'react-router-dom'

import ApiStatusBadge from '@/components/common/ApiStatusBadge'
import Logo from '@/components/common/Logo'
import { Button } from '@/components/ui'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { SCHOOL } from '@/utils/constants'

/**
 * Public landing page. The only route in or out is the sign-in button.
 *
 * The two blurred gradient orbs that used to float behind this hero are
 * gone. They were the stock "tech" decoration, they belonged to no school in
 * particular, and on a page whose job is to look like an institution issuing
 * official records they actively worked against it. What carries the page
 * now is the crest, the motto and the type.
 */
export function LandingPage() {
  useDocumentTitle()

  return (
    <div className="flex min-h-dvh flex-col">
      <div className="masthead-rule" aria-hidden="true" />

      <header className="border-ink-200 sticky top-0 z-30 border-b bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-18 w-full max-w-6xl items-center justify-between px-5 sm:px-8">
          <Logo />
          <Button as={Link} to="/login" size="sm" icon="arrow-right" iconPosition="right">
            Sign in
          </Button>
        </div>
      </header>

      <main className="flex flex-1 flex-col">
        <section className="bg-brand-950 relative flex flex-1 items-center">
          <div className="relative mx-auto grid w-full max-w-6xl gap-14 px-5 py-20 sm:px-8 sm:py-28 lg:grid-cols-[1.45fr_1fr] lg:items-center">
            <div>
              {/* Section numeral and eyebrow, set on a vermilion rule. */}
              <div className="mb-8 flex items-center gap-4">
                <span className="bg-accent-500 h-[3px] w-16" aria-hidden="true" />
                <p className="text-[11px] font-bold tracking-[0.2em] text-white/80 uppercase">
                  {SCHOOL.name}
                </p>
              </div>

              <h1 className="max-w-3xl text-[40px] leading-[0.98] font-bold tracking-tight text-white sm:text-6xl lg:text-[68px]">
                Results Management
                <br />
                <span className="font-serif font-semibold italic">&amp;</span> Report Cards
              </h1>

              <p className="text-brand-100 mt-8 max-w-xl text-base leading-relaxed sm:text-lg">
                One place for teachers to submit examination marks, for administrators to
                verify and publish them, and for students to receive an accurate report
                card.
              </p>

              <div className="mt-12 flex flex-wrap items-center gap-5">
                <Button as={Link} to="/login" size="lg" icon="arrow-right" iconPosition="right">
                  Sign in to the portal
                </Button>
                <p className="text-brand-300 text-sm">
                  Accounts are issued by the school office.
                </p>
              </div>

              {/* Three ordered facts about the product, in the numbered
                  register used throughout the system. */}
              <dl className="border-brand-900 mt-16 grid max-w-xl gap-px border-t pt-8 sm:grid-cols-3">
                {[
                  ['01', 'Teachers', 'Submit marks per subject'],
                  ['02', 'Administrators', 'Verify, then publish'],
                  ['03', 'Students', 'Receive a report card'],
                ].map(([n, term, detail]) => (
                  <div key={n}>
                    <dt className="text-accent-500 text-2xl font-bold tabular-nums">{n}</dt>
                    <dd className="mt-2 text-sm font-semibold text-white">{term}</dd>
                    <dd className="text-brand-300 mt-0.5 text-xs">{detail}</dd>
                  </div>
                ))}
              </dl>
            </div>

            {/* The crest, stated once at full size, with its motto. */}
            <div className="hidden justify-center lg:flex">
              <div className="bg-white px-10 py-12 text-center">
                <img
                  src="/logo.png"
                  alt={`${SCHOOL.name} crest`}
                  className="mx-auto h-56 w-auto"
                />
                {SCHOOL.motto && (
                  <p className="text-brand-800 mt-6 font-serif text-lg italic">
                    {SCHOOL.motto}
                  </p>
                )}
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-ink-200 border-t bg-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-5 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <div>
            <p className="text-ink-900 text-sm font-semibold">{SCHOOL.name}</p>
            {SCHOOL.motto && (
              <p className="text-ink-500 mt-0.5 font-serif text-xs italic">{SCHOOL.motto}</p>
            )}
          </div>
          <ApiStatusBadge />
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
