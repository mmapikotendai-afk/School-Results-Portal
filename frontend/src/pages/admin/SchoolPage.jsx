import { useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import PageHeader from '@/components/common/PageHeader'
import Toast from '@/components/common/Toast'
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  ConfirmDialog,
  Input,
  PageLoader,
} from '@/components/ui'
import useAsyncData from '@/hooks/useAsyncData'
import useDocumentTitle from '@/hooks/useDocumentTitle'
import useToast from '@/hooks/useToast'
import { schoolService } from '@/services/adminService'
import { getErrorMessage } from '@/services/apiClient'

const MAX_LOGO_BYTES = 2 * 1024 * 1024
const ACCEPTED = ['image/png', 'image/jpeg', 'image/svg+xml', 'image/webp']

/**
 * School information.
 *
 * The name and crest set here are what get printed on generated report cards,
 * so the page shows a preview of how the masthead will read.
 */
/**
 * `embedded` drops the page heading so this can sit inside the Settings tabs,
 * which supply their own. The form is identical either way.
 */
export function SchoolPage({ embedded = false }) {
  useDocumentTitle('School information')

  const { data, error, refresh } = useAsyncData(() => schoolService.get(), [])
  const [form, setForm] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [saveError, setSaveError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [confirmRemove, setConfirmRemove] = useState(false)
  const fileInput = useRef(null)
  const { toast, show, clear } = useToast()

  // Seed the form the first time the record arrives, and again whenever a save
  // brings back a newer one. Adjusting state during render rather than in an
  // effect avoids a second render pass showing empty fields.
  const [seededAt, setSeededAt] = useState(null)
  if (data && data.updated_at !== seededAt) {
    setSeededAt(data.updated_at)
    setForm({
      school_name: data.school_name ?? '',
      address: data.address ?? '',
      phone: data.phone ?? '',
      email: data.email ?? '',
      motto: data.motto ?? '',
    })
  }

  if (!form) return <PageLoader label="Loading school information" />

  function handleChange(event) {
    const { name, value } = event.target
    setForm((p) => ({ ...p, [name]: value }))
    setFieldErrors((p) => ({ ...p, [name]: undefined }))
  }

  async function handleSave(event) {
    event.preventDefault()
    const errors = {}
    if (!form.school_name.trim()) errors.school_name = 'A school name is required.'
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      errors.email = 'Enter a valid email address.'
    }
    setFieldErrors(errors)
    if (Object.keys(errors).length) return

    setSaving(true)
    setSaveError(null)
    try {
      await schoolService.update({
        school_name: form.school_name.trim(),
        address: form.address.trim() || null,
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
        motto: form.motto.trim() || null,
      })
      show('School information saved.')
      refresh()
    } catch (err) {
      setSaveError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleLogo(event) {
    const file = event.target.files?.[0]
    // Reset immediately so choosing the same file twice still fires a change.
    event.target.value = ''
    if (!file) return

    if (!ACCEPTED.includes(file.type)) {
      show('The logo must be a PNG, JPEG, SVG or WebP image.', 'danger')
      return
    }
    if (file.size > MAX_LOGO_BYTES) {
      show('The logo must be 2 MB or smaller.', 'danger')
      return
    }

    setUploading(true)
    try {
      await schoolService.uploadLogo(file)
      show('School logo updated.')
      refresh()
    } catch (err) {
      show(getErrorMessage(err), 'danger')
    } finally {
      setUploading(false)
    }
  }

  async function removeLogo() {
    await schoolService.deleteLogo()
    show('School logo removed.')
    refresh()
  }

  return (
    <div>
      {!embedded && (
        <PageHeader
          title="School information"
          description="The name, crest and contact details printed on generated report cards."
        />
      )}

      {error && (
        <Alert tone="danger" className="mb-5">
          {error}
        </Alert>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_20rem]">
        <Card>
          <CardHeader icon="school" title="Details" description="Shown on every report card." />
          <CardBody>
            {saveError && (
              <Alert tone="danger" className="mb-5" onDismiss={() => setSaveError(null)}>
                {saveError}
              </Alert>
            )}

            <form onSubmit={handleSave} noValidate className="space-y-5">
              <Input
                label="School name"
                name="school_name"
                value={form?.school_name ?? ''}
                onChange={handleChange}
                error={fieldErrors.school_name}
                disabled={saving}
                required
              />
              <Input
                label="Motto"
                name="motto"
                value={form?.motto ?? ''}
                onChange={handleChange}
                placeholder="Knowledge. Integrity. Service."
                disabled={saving}
              />
              <Input
                label="Address"
                name="address"
                value={form?.address ?? ''}
                onChange={handleChange}
                disabled={saving}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Phone"
                  name="phone"
                  value={form?.phone ?? ''}
                  onChange={handleChange}
                  disabled={saving}
                />
                <Input
                  label="Email"
                  name="email"
                  type="email"
                  icon="envelope"
                  value={form?.email ?? ''}
                  onChange={handleChange}
                  error={fieldErrors.email}
                  disabled={saving}
                />
              </div>

              <div className="border-ink-200 border-t pt-5">
                <Button type="submit" loading={saving} icon="check">
                  Save changes
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader icon="image" title="School logo" description="PNG, JPEG, SVG or WebP, up to 2 MB." />
            <CardBody>
              <div className="border-ink-200 bg-ink-50 mb-4 flex aspect-square items-center justify-center overflow-hidden rounded-lg border">
                {data?.logo_url ? (
                  <img
                    src={data.logo_url}
                    alt={`${data.school_name} logo`}
                    className="max-h-full max-w-full object-contain p-4"
                  />
                ) : (
                  <div className="text-ink-400 text-center">
                    <FontAwesomeIcon icon="image" className="text-3xl" aria-hidden="true" />
                    <p className="mt-2 text-sm">No logo uploaded</p>
                  </div>
                )}
              </div>

              <input
                ref={fileInput}
                type="file"
                accept={ACCEPTED.join(',')}
                onChange={handleLogo}
                className="sr-only"
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  icon="cloud-arrow-up"
                  loading={uploading}
                  onClick={() => fileInput.current?.click()}
                >
                  {data?.logo_url ? 'Replace' : 'Upload'}
                </Button>
                {data?.logo_url && (
                  <Button
                    size="sm"
                    variant="secondary"
                    icon="xmark"
                    onClick={() => setConfirmRemove(true)}
                  >
                    Remove
                  </Button>
                )}
              </div>
            </CardBody>
          </Card>

          {/* How the crest and name will sit together on a report card. */}
          <Card>
            <CardHeader icon="file-pdf" title="Report card preview" />
            <CardBody>
              <div className="border-ink-300 rounded-lg border border-dashed p-4 text-center">
                {data?.logo_url ? (
                  <img
                    src={data.logo_url}
                    alt=""
                    className="mx-auto mb-2 h-12 object-contain"
                  />
                ) : (
                  <img src="/crest.svg" alt="" className="mx-auto mb-2 h-12 opacity-30" />
                )}
                <p className="text-ink-900 font-serif text-sm font-semibold">
                  {form?.school_name || 'Your School Name'}
                </p>
                {form?.motto && <p className="text-ink-500 mt-0.5 text-xs italic">{form.motto}</p>}
                {form?.address && <p className="text-ink-400 mt-1 text-xs">{form.address}</p>}
                <div className="border-ink-200 mt-3 border-t pt-2">
                  <p className="text-ink-400 text-[10px] tracking-wider uppercase">
                    Statement of Results
                  </p>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={confirmRemove}
        onClose={() => setConfirmRemove(false)}
        onConfirm={removeLogo}
        title="Remove the school logo?"
        message="Report cards will fall back to the default crest until a new logo is uploaded."
        confirmLabel="Remove logo"
        variant="danger"
        icon="xmark"
      />

      <Toast toast={toast} onDismiss={clear} />
    </div>
  )
}

export default SchoolPage
