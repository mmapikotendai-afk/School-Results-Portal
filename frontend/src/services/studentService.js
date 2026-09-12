/**
 * Student-facing API calls.
 *
 * There is no student id in any of these. The backend scopes every response to
 * the signed-in account and only ever returns results from examinations the
 * school has published, so there is no id here that could be changed to reach
 * somebody else's marks.
 */

import apiClient from '@/services/apiClient'
import { downloadFile } from '@/services/download'

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
const download = downloadFile

export const studentDownloads = {
  csv: (examinationId, label = 'results') =>
    download(`/student/results/${examinationId}/export.csv`, `${label}.csv`),

  pdf: (examinationId, label = 'statement') =>
    download(`/student/results/${examinationId}/export.pdf`, `${label}.pdf`),
}

export default studentResultsService
