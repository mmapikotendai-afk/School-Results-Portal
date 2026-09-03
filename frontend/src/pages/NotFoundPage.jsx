import { Link } from 'react-router-dom'

import Logo from '@/components/common/Logo'
import { Button } from '@/components/ui'
import useAuth from '@/hooks/useAuth'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import { homePathForRole } from '@/utils/roles'

export function NotFoundPage() {
  useDocumentTitle('Page not found')

  const { isAuthenticated, user } = useAuth()
  const target = isAuthenticated ? homePathForRole(user.role) : '/'

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-5 text-center">
      <Logo size="lg" className="mb-8" />
      <p className="text-brand-600 text-sm font-semibold tracking-wider uppercase">Error 404</p>
      <h1 className="mt-2 font-serif text-3xl font-semibold sm:text-4xl">Page not found</h1>
      <p className="text-ink-500 mt-3 max-w-md text-sm">
        The page you are looking for does not exist, or you no longer have access to it.
      </p>
      <Button as={Link} to={target} className="mt-8" icon="arrow-right" iconPosition="right">
        {isAuthenticated ? 'Back to your dashboard' : 'Back to the home page'}
      </Button>
    </div>
  )
}

export default NotFoundPage
