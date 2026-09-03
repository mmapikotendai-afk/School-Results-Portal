/**
 * Administrator downloads.
 *
 * Fetched through Axios rather than linked directly: these endpoints need the
 * bearer token, which a plain <a href> would not send.
 */

import apiClient from '@/services/apiClient'

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

export const adminDownloads = {
  /** One student, one examination. */
  studentResultsCsv: (studentId, examinationId, label = 'results') =>
    download(
      `/admin/students/${studentId}/results/${examinationId}/export.csv`,
      `${label}.csv`,
    ),

  /** One student, every examination they have sat. */
  studentHistoryCsv: (studentId, label = 'results-history') =>
    download(`/admin/students/${studentId}/results/export.csv`, `${label}.csv`),

  /** Every result in one examination, across all classes and subjects. */
  examinationCsv: (examinationId, label = 'examination-results') =>
    download(`/admin/examinations/${examinationId}/export.csv`, `${label}.csv`),

  /** The official report card for one student in one examination. */
  reportCard: (studentId, examinationId, label = 'report-card') =>
    download(
      `/admin/students/${studentId}/results/${examinationId}/report-card.pdf`,
      `${label}.pdf`,
    ),
}

export default adminDownloads
