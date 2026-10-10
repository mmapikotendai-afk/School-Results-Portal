import { useEffect, useRef, useState } from 'react'

import { Alert, Button } from '@/components/ui'
import { studentService, teacherService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'
import { downloadCredentialPdf } from '@/utils/credentialPdf'

export function CredentialSlips({ slips, onFinished, autoDownload = false }) {
  const [available, setAvailable] = useState(true)
  const [printing, setPrinting] = useState(false)
  const [error, setError] = useState(null)
  const consumptionStarted = useRef(false)
  const first = slips?.[0]

  useEffect(() => {
    if (!first?.expires_at) return undefined
    const delay = Math.max(0, new Date(first.expires_at).getTime() - Date.now())
    const timer = window.setTimeout(() => setAvailable(false), delay)
    return () => window.clearTimeout(timer)
  }, [first?.expires_at])

  async function downloadOnce() {
    if (consumptionStarted.current) return
    consumptionStarted.current = true
    setPrinting(true)
    setError(null)
    try {
      const service = first.teacher_id ? teacherService : studentService
      await service.consumeCredentialBatch(first.batch_id)
      downloadCredentialPdf(slips)
      setAvailable(false)
      onFinished?.()
    } catch (err) {
      setError(getErrorMessage(err, 'These credentials can no longer be downloaded.'))
    } finally {
      setPrinting(false)
    }
  }

  useEffect(() => {
    if (autoDownload && available && first?.batch_id) downloadOnce()
    // Credential data must be consumed only once for this rendered issuance.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoDownload, first?.batch_id])

  if (!available) {
    return (
      <Alert tone="success" title="Credentials closed">
        The one-time credential view has been cleared. Reset a student&rsquo;s password to
        issue a new slip if another copy is required.
      </Alert>
    )
  }

  return (
    <div>
      <Alert tone="warning" className="mb-4" title="Downloaded once — keep the file private">
        Plaintext passwords are visible only in this short-lived view. They are not stored
        and cannot be opened again after download or expiry.
      </Alert>
      {error && <Alert tone="danger" className="mb-4">{error}</Alert>}
      <div className="credential-print-area space-y-4">
        {slips.map((slip) => (
          <section key={slip.student_id ?? slip.teacher_id} className="credential-slip rounded-xl border border-ink-300 bg-white p-5">
            <p className="font-serif text-xl font-semibold text-ink-950">{slip.school_name}</p>
            <p className="mt-1 text-sm text-ink-500">{slip.teacher_id ? 'Teacher' : 'Student'} portal credentials</p>
            <dl className="mt-5 grid grid-cols-[auto_1fr] gap-x-5 gap-y-2 text-sm">
              <dt className="text-ink-500">{slip.teacher_id ? 'Teacher' : 'Student'}</dt><dd className="font-medium text-ink-950">{slip.teacher_name ?? slip.student_name}</dd>
              <dt className="text-ink-500">{slip.teacher_id ? 'Employee number' : 'Student number'}</dt><dd className="font-mono font-semibold text-ink-950">{slip.employee_number ?? slip.student_number}</dd>
              <dt className="text-ink-500">Temporary password</dt><dd className="font-mono font-semibold text-ink-950">{slip.temporary_password}</dd>
              <dt className="text-ink-500">Portal</dt><dd className="break-all text-ink-950">{slip.portal_url}</dd>
            </dl>
            <p className="mt-5 border-t border-ink-200 pt-4 text-xs leading-relaxed text-ink-600">{slip.instructions}</p>
          </section>
        ))}
      </div>
      <Button className="mt-4 print:hidden" icon="download" onClick={downloadOnce} loading={printing}>
        Download {slips.length === 1 ? 'credential PDF' : `${slips.length} credential PDFs`}
      </Button>
    </div>
  )
}

export default CredentialSlips
