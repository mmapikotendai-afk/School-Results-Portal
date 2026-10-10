import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import Logo from '@/components/common/Logo'
import { Button } from '@/components/ui'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { SCHOOL } from '@/utils/constants'

export function LandingPage() {
  useDocumentTitle()
  return <div className="flex min-h-dvh flex-col">
    <header className="border-b border-ink-200 bg-white"><div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-5 sm:px-10"><Logo /><Button as={Link} to="/login" size="sm" variant="secondary">Sign in <FontAwesomeIcon icon="arrow-right" className="ml-2" /></Button></div></header>
    <main className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-12 px-6 py-14 sm:px-10 lg:grid-cols-[1.25fr_1fr] lg:gap-20 lg:py-20">
      <section><h1 className="max-w-[12ch] font-serif text-[48px] leading-[1.05] font-normal tracking-[-0.035em] sm:text-[68px]">A clear view of every academic journey.</h1><p className="mt-7 max-w-lg text-base leading-relaxed text-ink-500">The results and report card portal for {SCHOOL.name}. Submit marks, manage academic records and keep track of your progress.</p><Button as={Link} to="/login" className="mt-8" icon="arrow-right" iconPosition="right">Open the portal</Button><p className="mt-4 text-xs text-ink-500">Use the account issued by your school office.</p></section>
      <section className="border-t border-ink-200 lg:border-t-0 lg:border-l lg:pl-10" aria-label="Inside the portal"><div className="flex items-center gap-5 py-8"><img src="/logo.png" alt="" className="h-24 w-auto" /><div><p className="font-serif text-xl font-medium">{SCHOOL.shortName}</p><p className="mt-2 text-xs leading-relaxed text-ink-500">{SCHOOL.motto}</p></div></div><dl className="divide-y divide-ink-200 border-y border-ink-200">{[['Teachers','A focused desk for your subjects, mark sheets and submissions.'],['Students','Your published results and report cards, in one academic record.'],['School office','A shared register for enrolment, examinations and publication.']].map(([title,detail]) => <div key={title} className="py-5"><dt className="text-sm font-semibold">{title}</dt><dd className="mt-2 text-sm leading-relaxed text-ink-500">{detail}</dd></div>)}</dl></section>
    </main>
    <footer className="border-t border-ink-200 px-6 py-5 text-center text-xs text-ink-500">School results &amp; academic records · {SCHOOL.shortName}</footer>
  </div>
}
export default LandingPage
