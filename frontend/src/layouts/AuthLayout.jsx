import { Link, Outlet } from 'react-router-dom'
import Logo from '@/components/common/Logo'
import { SCHOOL } from '@/utils/constants'

export function AuthLayout() {
  return <div className="auth-shell min-h-dvh lg:grid lg:grid-cols-[1fr_1.1fr]">
    <aside className="auth-identity flex flex-col justify-between border-b border-ink-200 p-6 sm:p-10 lg:border-r lg:border-b-0 lg:p-14">
      <Link to="/" aria-label="School home" className="w-fit"><Logo size="lg" /></Link>
      <div className="hidden py-16 lg:block">
        <h2 className="max-w-[12ch] font-serif text-[clamp(40px,4vw,64px)] leading-[1.08] font-normal tracking-[-0.035em]">Every result.<br />Part of your story.</h2>
        <p className="mt-7 max-w-sm text-base leading-relaxed text-ink-600">A shared place for teachers, students and the school office to keep academic records clear and connected.</p>
        <div className="mt-12 h-px w-16 bg-accent-700" />
      </div>
      <div className="hidden text-sm text-ink-500 lg:block"><p className="font-medium text-ink-700">{SCHOOL.name}</p>{SCHOOL.motto && <p className="mt-2 font-serif italic">{SCHOOL.motto}</p>}</div>
    </aside>
    <main className="flex items-center justify-center px-6 py-14 sm:px-10 lg:py-20">
      <div className="w-full max-w-[390px]"><Outlet /><p className="mt-10 border-t border-ink-200 pt-5 text-xs leading-relaxed text-ink-500">Your school account gives you access to the records and tools assigned to your role.</p></div>
    </main>
  </div>
}
export default AuthLayout
