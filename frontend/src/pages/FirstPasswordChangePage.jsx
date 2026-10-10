import ChangePasswordForm from '@/components/settings/ChangePasswordForm'
import useDocumentTitle from '@/hooks/useDocumentTitle'

export function FirstPasswordChangePage() {
  useDocumentTitle('Choose a new password')
  return (
    <div>
      <div className="mb-6">
        <h1 className="font-serif text-4xl font-medium tracking-tight text-ink-950">
          Choose your password
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-ink-600">
          Your temporary password worked. Replace it now before opening the portal.
        </p>
      </div>
      <ChangePasswordForm firstLogin />
    </div>
  )
}

export default FirstPasswordChangePage
