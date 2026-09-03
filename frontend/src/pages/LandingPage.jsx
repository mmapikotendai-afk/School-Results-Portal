import { Link } from 'react-router-dom'

import ApiStatusBadge from '@/components/common/ApiStatusBadge'
import Logo from '@/components/common/Logo'
import { Button } from '@/components/ui'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { SCHOOL } from '@/utils/constants'

/** Public landing page. The only route in or out is the sign-in button. */
export function LandingPage() {
  useDocumentTitle()

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-ink-200 sticky top-0 z-30 border-b bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-5 sm:px-8">
          <Logo />
          <Button as={Link} to="/login" size="sm" icon="arrow-right" iconPosition="right">
            Sign in
          </Button>
        </div>
      </header>

      <main className="flex flex-1 flex-col">
        {/* Hero. It is now the only section, so it stretches to fill whatever
            height is left and centres its content, rather than sitting at the
            top with a band of empty page beneath it on a tall screen. */}
        <section className="bg-brand-950 relative flex flex-1 items-center overflow-hidden">
          <div
            aria-hidden="true"
            className="bg-brand-700/30 absolute -top-32 -right-20 size-[28rem] rounded-full blur-3xl"
          />
          <div
            aria-hidden="true"
            className="bg-accent-500/10 absolute -bottom-40 -left-24 size-[28rem] rounded-full blur-3xl"
          />

          <div className="relative mx-auto w-full max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
            <p className="text-accent-300 mb-4 text-xs font-semibold tracking-[0.2em] uppercase">
              {SCHOOL.name}
            </p>
            <h1 className="max-w-3xl font-serif text-4xl leading-tight font-semibold text-white sm:text-5xl lg:text-6xl">
              Results Management &amp; Report Card Portal
            </h1>
            <p className="text-brand-100 mt-6 max-w-2xl text-base leading-relaxed sm:text-lg">
              One place for teachers to submit examination marks, for administrators to
              verify and publish them, and for students to receive an accurate report card.
            </p>

            <div className="mt-10 flex flex-wrap items-center gap-3">
              <Button as={Link} to="/login" size="lg" variant="accent" icon="arrow-right" iconPosition="right">
                Sign in to the portal
              </Button>
              <p className="text-brand-300 text-sm">
                Accounts are issued by the school office.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-ink-50">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-5 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <div>
            <p className="text-ink-700 text-sm font-semibold">{SCHOOL.name}</p>
            {SCHOOL.motto && <p className="text-ink-500 text-xs">{SCHOOL.motto}</p>}
          </div>
          <ApiStatusBadge />
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
