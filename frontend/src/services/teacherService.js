/**
 * Teacher portal API calls.
 *
 * Every subject-scoped call names an examination and a subject, and the server
 * checks the assignment before answering. A subject that is not assigned to the
 * caller returns 404 - the same answer as one that does not exist - so nothing
 * here can be used to discover what other teachers hold.
 */

import apiClient from '@/services/apiClient'

const unwrap = (promise) => promise.then(({ data }) => data)

const base = (examinationId, subjectId) =>
  `/teacher/examinations/${examinationId}/subjects/${subjectId}`

export const teacherPortalService = {
  /** GET /teacher/dashboard - current examination, my subjects, deadline, status. */
  dashboard: () => unwrap(apiClient.get('/teacher/dashboard')),

  /** GET the full roll for one subject, marked or not. */
  markSheet: (examinationId, subjectId) =>
    unwrap(apiClient.get(`${base(examinationId, subjectId)}/marksheet`)),

  /** PUT marks edited on screen. Blank entries are skipped, not zeroed. */
  saveMarkSheet: (examinationId, subjectId, entries, reason) =>
    unwrap(apiClient.put(`${base(examinationId, subjectId)}/marksheet`, { entries, reason })),

  /** PUT one corrected mark; the change is written to the audit trail. */
  updateResult: (resultId, payload) =>
    unwrap(apiClient.put(`/teacher/results/${resultId}`, payload)),

  /**
   * POST a CSV of marks.
   *
   * `validateOnly` checks the file and reports what would happen without saving.
   * `allowReplace` confirms that marks already on record may be overwritten -
   * without it the server refuses the import and reports the clashes instead.
   * `reason` is recorded on the audit entry for each replaced mark.
   */
  upload: (
    examinationId,
    subjectId,
    file,
    { validateOnly = false, allowReplace = false, reason = null } = {},
  ) => {
    const body = new FormData()
    body.append('file', file)
    if (reason) body.append('reason', reason)
    return unwrap(
      apiClient.post(`${base(examinationId, subjectId)}/upload`, body, {
        params: { validate_only: validateOnly, allow_replace: allowReplace },
        // Let the browser set the multipart boundary; a hand-written header omits it.
        headers: { 'Content-Type': undefined },
      }),
    )
  },

  /** The mark scale the API enforces, so the form shows the same limits. */
  markScale: () => unwrap(apiClient.get('/teacher/mark-scale')),

  /**
   * GET the (examination, subject) pairs this teacher may generate a template
   * for. Built server-side from their own assignments, so the picker can never
   * offer a combination the download would refuse.
   */
  templateOptions: () => unwrap(apiClient.get('/teacher/template-options')),

  /** GET the classes represented in a subject roll, for narrowing a template. */
  classes: (examinationId, subjectId) =>
    unwrap(apiClient.get(`${base(examinationId, subjectId)}/classes`)),
}

/**
 * Downloads.
 *
 * Fetched through Axios rather than linked directly: the endpoints need the
 * bearer token, which a plain <a href> would not send.
 */
async function download(path, fallbackName) {
  const response = await apiClient.get(path, { responseType: 'blob' })

  // Prefer the filename the server chose, so exports are named consistently.
  const disposition = response.headers['content-disposition'] ?? ''
  const match = /filename="?([^"';]+)"?/i.exec(disposition)
  const filename = match?.[1] ?? fallbackName

  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  // Revoking immediately can cancel the download in some browsers.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  return filename
}

export const teacherDownloads = {
  /** `classId` narrows the roll to one class; omit it for the whole subject. */
  template: (examinationId, subjectId, code, classId = null) =>
    download(
      `${base(examinationId, subjectId)}/template.csv${classId ? `?class_id=${classId}` : ''}`,
      `${code}-template.csv`,
    ),

  csv: (examinationId, subjectId, code) =>
    download(`${base(examinationId, subjectId)}/export.csv`, `${code}-results.csv`),

  pdf: (examinationId, subjectId, code) =>
    download(`${base(examinationId, subjectId)}/export.pdf`, `${code}-marksheet.pdf`),
}

export default teacherPortalService
