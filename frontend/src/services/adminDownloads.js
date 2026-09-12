/**
 * Administrator downloads.
 *
 * Fetched through Axios rather than linked directly: these endpoints need the
 * bearer token, which a plain <a href> would not send.
 */

import { downloadFile } from '@/services/download'

const download = downloadFile

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
