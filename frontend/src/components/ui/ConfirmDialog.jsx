import { useState } from 'react'

import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import Alert from '@/components/ui/Alert'

/**
 * Confirmation before an action that is awkward to undo.
 *
 * Holds its own submitting state, so the caller passes an async onConfirm and
 * the dialog stays open with the button spinning until it settles.
 */
export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  detail,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'primary',
  icon,
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function handleConfirm() {
    setBusy(true)
    setError(null)
    try {
      await onConfirm()
      onClose?.()
    } catch (err) {
      setError(err?.message || 'That did not work. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={busy ? undefined : onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button variant={variant} onClick={handleConfirm} loading={busy} icon={icon}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {error && (
        <Alert tone="danger" className="mb-4">
          {error}
        </Alert>
      )}
      <p className="text-ink-700 text-sm">{message}</p>
      {detail && <div className="mt-4">{detail}</div>}
    </Modal>
  )
}

export default ConfirmDialog
