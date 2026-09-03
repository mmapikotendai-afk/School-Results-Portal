import { useEffect, useId, useRef } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { cx } from '@/utils/format'

const SIZES = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-3xl',
}

/**
 * Dialog used by every admin form.
 *
 * Uses the native <dialog> element, so focus trapping, Escape handling and the
 * top layer come from the platform rather than being reimplemented.
 */
export function Modal({ open, onClose, title, description, size = 'md', footer, children }) {
  const ref = useRef(null)
  // A generated id, so two dialogs on one page cannot share a heading id.
  const titleId = useId()

  useEffect(() => {
    const node = ref.current
    if (!node) return

    if (open && !node.open) {
      node.showModal()
    } else if (!open && node.open) {
      node.close()
    }
  }, [open])

  // Escape fires the dialog's own cancel event; route it through onClose so
  // the parent's state stays in step with what is on screen.
  useEffect(() => {
    const node = ref.current
    if (!node) return

    function handleCancel(event) {
      event.preventDefault()
      onClose?.()
    }
    node.addEventListener('cancel', handleCancel)
    return () => node.removeEventListener('cancel', handleCancel)
  }, [onClose])

  if (!open) return null

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className={cx(
        'bg-ink-900/50 m-0 h-full max-h-none w-full max-w-none justify-center overflow-y-auto p-0 backdrop:bg-transparent',
        'flex items-start sm:items-center',
      )}
      onClick={(event) => {
        // Clicking the backdrop (the dialog element itself) closes it.
        if (event.target === ref.current) onClose?.()
      }}
    >
      <div
        className={cx(
          'shadow-overlay my-auto w-full rounded-xl bg-white',
          'mx-auto p-0 sm:my-8',
          SIZES[size],
        )}
      >
        <div className="border-ink-200 flex items-start gap-4 border-b px-5 py-4">
          <div className="min-w-0 flex-1">
            <h2 id={titleId} className="text-lg font-semibold">
              {title}
            </h2>
            {description && <p className="text-ink-500 mt-1 text-sm">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-ink-400 hover:bg-ink-100 hover:text-ink-700 -mt-1 -mr-1 rounded-lg p-2 transition-colors"
            aria-label="Close"
          >
            <FontAwesomeIcon icon="xmark" />
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-5 py-5">{children}</div>

        {footer && (
          <div className="border-ink-200 bg-ink-50 flex flex-wrap items-center justify-end gap-2 rounded-b-xl border-t px-5 py-4">
            {footer}
          </div>
        )}
      </div>
    </dialog>
  )
}

export default Modal
