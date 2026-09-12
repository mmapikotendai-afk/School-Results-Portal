/**
 * The one file-download helper, shared by the admin, teacher and student
 * services.
 *
 * Downloads are fetched through Axios rather than linked directly, because
 * these endpoints need the bearer token and a plain <a href> would not send
 * it. That means the response arrives as a Blob and this module is responsible
 * for everything a normal browser download would have handled for us: naming
 * the file, noticing that the "file" is actually an error, and not pulling the
 * object URL out from under the browser before it has finished writing.
 */

import apiClient from '@/services/apiClient'

/**
 * The filename the server chose, falling back to one we supply.
 *
 * Handles both spellings of the header. `filename*=UTF-8''...` is the encoded
 * form servers use when the name is not plain ASCII, and it takes precedence
 * over `filename=` when both are present.
 *
 * Returns null when the header is absent or unreadable - which, cross-origin,
 * it will be unless the API sends Access-Control-Expose-Headers.
 */
function filenameFrom(headers) {
  // Axios v1 exposes an AxiosHeaders instance; older shapes are plain objects.
  const raw =
    (typeof headers?.get === 'function' ? headers.get('content-disposition') : null) ??
    headers?.['content-disposition'] ??
    ''
  if (!raw) return null

  const encoded = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(raw)
  if (encoded?.[1]) {
    try {
      return decodeURIComponent(encoded[1].trim().replace(/^"|"$/g, ''))
    } catch {
      // A malformed encoding is not worth failing the download over.
    }
  }

  const plain = /filename="?([^"';]+)"?/i.exec(raw)
  return plain?.[1]?.trim() ?? null
}

/** Pull the message out of an error the server sent as JSON in a Blob. */
async function messageFromBlob(blob) {
  try {
    const detail = JSON.parse(await blob.text())?.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object' && detail.message) return detail.message
  } catch {
    // Not JSON after all; the generic message below is the best we can do.
  }
  return null
}

/**
 * Fetch `path` and save it as a file. Returns the filename actually used.
 *
 * Throws rather than writing anything when the response is not a real file, so
 * the caller's error toast fires instead of the user receiving a download that
 * cannot be opened.
 */
export async function downloadFile(path, fallbackName) {
  const response = await apiClient.get(path, { responseType: 'blob' })
  const blob = response.data

  // An empty body means something went wrong upstream. Saving it produces a
  // 0-byte file that the PDF reader reports only as "cannot open this file",
  // which tells the user nothing about what actually happened.
  if (!blob || blob.size === 0) {
    throw new Error('The server returned an empty file, so nothing was saved. Please try again.')
  }

  // A JSON body under a .pdf name is an error that reached us with a success
  // shape. Read it and report it rather than writing it to disk.
  if (blob.type?.includes('application/json')) {
    throw new Error(
      (await messageFromBlob(blob)) ?? 'That file could not be generated. Please try again.',
    )
  }

  const filename = filenameFrom(response.headers) ?? fallbackName

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()

  // Revoking kills the download in progress, and the browser may not have
  // finished writing the file - if the user has "ask where to save each file"
  // switched on, it has not even started, and a short timer truncates the
  // result to zero bytes. The blob is released with the page anyway, so the
  // only cost of waiting is a few kilobytes held a little longer.
  window.setTimeout(() => URL.revokeObjectURL(url), 120_000)

  return filename
}

export default downloadFile
