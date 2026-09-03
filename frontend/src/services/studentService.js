/**
 * Student-facing API calls.
 *
 * There is no student id in any of these. The backend scopes every response to
 * the signed-in account and only ever returns results from examinations the
 * school has published, so there is no id here that could be changed to reach
 * somebody else's marks.
 */

import apiClient from '@/services/apiClient'

const unwrap = (promise) => promise.then(({ data }) => data)

export const studentResultsService = {
  /** GET /student/results - published examinations, plus any in progress by name only. */
  all: () => unwrap(apiClient.get('/student/results')),

  /** GET /student/history - every examination, with whether it is published. */
  history: () => unwrap(apiClient.get('/student/history')),

  /** GET /student/results/:id - one published examination. */
  examination: (examinationId) =>
    unwrap(apiClient.get(`/student/results/${examinationId}`)),
}

/**
 * Downloads.
 *
 * Fetched through Axios rather than linked directly: these endpoints need the
 * bearer token, which a plain <a href> would not send.
 */
async function download(path, fallbackName) {
  const response = await apiClient.get(path, { responseType: 'blob' })

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

export const studentDownloads = {
  csv: (examinationId, label = 'results') =>
    download(`/student/results/${examinationId}/export.csv`, `${label}.csv`),

  pdf: (examinationId, label = 'statement') =>
    download(`/student/results/${examinationId}/export.pdf`, `${label}.pdf`),
}

export default studentResultsService
