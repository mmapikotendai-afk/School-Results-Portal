import { useEffect } from 'react'

import { APP_NAME, SCHOOL } from '@/utils/constants'

/** Keep the browser tab title in step with the current page. */
export function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title
      ? `${title} · ${APP_NAME}`
      : `${SCHOOL.shortName} ${APP_NAME}`
  }, [title])
}

export default useDocumentTitle
