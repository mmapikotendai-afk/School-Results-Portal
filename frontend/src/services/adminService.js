/**
 * Administrator API calls.
 *
 * Grouped by the thing being managed. Every one of these endpoints is gated by
 * require_admin on the server, so a non-admin reaching them gets a 403
 * regardless of what the UI allowed.
 */

import apiClient from '@/services/apiClient'

const unwrap = (promise) => promise.then(({ data }) => data)

export const dashboardService = {
  stats: () => unwrap(apiClient.get('/admin/dashboard')),
}

export const studentService = {
  list: (params) => unwrap(apiClient.get('/admin/students', { params })),
  get: (id, params) => unwrap(apiClient.get(`/admin/students/${id}`, { params })),
  create: (payload) => unwrap(apiClient.post('/admin/students', payload)),
  update: (id, payload) => unwrap(apiClient.put(`/admin/students/${id}`, payload)),
  setStatus: (id, isActive) =>
    unwrap(apiClient.patch(`/admin/students/${id}/status`, { is_active: isActive })),
  getSubjects: (id, params) =>
    unwrap(apiClient.get(`/admin/students/${id}/subjects`, { params })),
  setSubjects: (id, subjectIds, academicYearId) =>
    unwrap(
      apiClient.put(`/admin/students/${id}/subjects`, {
        subject_ids: subjectIds,
        academic_year_id: academicYearId ?? null,
      }),
    ),
}

export const teacherService = {
  list: (params) => unwrap(apiClient.get('/admin/teachers', { params })),
  get: (id, params) => unwrap(apiClient.get(`/admin/teachers/${id}`, { params })),
  create: (payload) => unwrap(apiClient.post('/admin/teachers', payload)),
  update: (id, payload) => unwrap(apiClient.put(`/admin/teachers/${id}`, payload)),
  setStatus: (id, isActive) =>
    unwrap(apiClient.patch(`/admin/teachers/${id}/status`, { is_active: isActive })),
  setSubjects: (id, subjectIds, academicYearId) =>
    unwrap(
      apiClient.put(`/admin/teachers/${id}/subjects`, {
        subject_ids: subjectIds,
        academic_year_id: academicYearId ?? null,
      }),
    ),
}

export const subjectService = {
  list: (params) => unwrap(apiClient.get('/admin/subjects', { params })),
  create: (payload) => unwrap(apiClient.post('/admin/subjects', payload)),
  update: (id, payload) => unwrap(apiClient.put(`/admin/subjects/${id}`, payload)),
  usage: (id) => unwrap(apiClient.get(`/admin/subjects/${id}/usage`)),
  setStatus: (id, isActive) =>
    unwrap(apiClient.patch(`/admin/subjects/${id}/status`, { is_active: isActive })),
}

export const classService = {
  list: (params) => unwrap(apiClient.get('/admin/classes', { params })),
  create: (payload) => unwrap(apiClient.post('/admin/classes', payload)),
  update: (id, payload) => unwrap(apiClient.put(`/admin/classes/${id}`, payload)),
  setStatus: (id, isActive) =>
    unwrap(apiClient.patch(`/admin/classes/${id}/status`, { is_active: isActive })),
}

export const academicService = {
  listYears: () => unwrap(apiClient.get('/admin/academic-years')),
  createYear: (payload) => unwrap(apiClient.post('/admin/academic-years', payload)),
  updateYear: (id, payload) => unwrap(apiClient.put(`/admin/academic-years/${id}`, payload)),
  activateYear: (id) => unwrap(apiClient.post(`/admin/academic-years/${id}/activate`)),

  listTerms: (params) => unwrap(apiClient.get('/admin/terms', { params })),
  createTerm: (payload) => unwrap(apiClient.post('/admin/terms', payload)),
  updateTerm: (id, payload) => unwrap(apiClient.put(`/admin/terms/${id}`, payload)),
  activateTerm: (id) => unwrap(apiClient.post(`/admin/terms/${id}/activate`)),

  listExaminations: (params) => unwrap(apiClient.get('/admin/examinations', { params })),
  createExamination: (payload) => unwrap(apiClient.post('/admin/examinations', payload)),
  updateExamination: (id, payload) =>
    unwrap(apiClient.put(`/admin/examinations/${id}`, payload)),
  setExaminationStatus: (id, status) =>
    unwrap(apiClient.patch(`/admin/examinations/${id}/status`, { status })),
  publicationSummary: (id) => unwrap(apiClient.get(`/admin/examinations/${id}/publication`)),
  submissions: (id) => unwrap(apiClient.get(`/admin/examinations/${id}/submissions`)),
  syncSubmissions: (id) => unwrap(apiClient.post(`/admin/examinations/${id}/sync-submissions`)),
}

export const resultsService = {
  /** A student's full history, narrowable by year, term or examination. */
  studentResults: (studentId, params) =>
    unwrap(apiClient.get(`/admin/students/${studentId}/results`, { params })),

  /** Results for a whole examination, optionally one class, ranked. */
  examinationResults: (examinationId, params) =>
    unwrap(apiClient.get(`/admin/examinations/${examinationId}/results`, { params })),

  /** Correct one mark. A reason is required and lands on the audit trail. */
  editResult: (resultId, payload) =>
    unwrap(apiClient.put(`/admin/results/${resultId}`, payload)),

  /** The full provenance of one mark: who uploaded it, and every change since. */
  resultAudit: (resultId) => unwrap(apiClient.get(`/admin/results/${resultId}/audit`)),

  /** Recent corrections across the school, optionally narrowed. */
  auditTrail: (params) => unwrap(apiClient.get('/admin/audit', { params })),

  /** The configured grading scale. */
  gradingScale: () => unwrap(apiClient.get('/admin/grading-scale')),
}

export const schoolService = {
  get: () => unwrap(apiClient.get('/admin/school')),
  update: (payload) => unwrap(apiClient.put('/admin/school', payload)),
  uploadLogo: (file) => {
    const body = new FormData()
    body.append('file', file)
    // Let the browser set the multipart boundary; a hand-written header omits it.
    return unwrap(
      apiClient.post('/admin/school/logo', body, {
        headers: { 'Content-Type': undefined },
      }),
    )
  },
  deleteLogo: () => unwrap(apiClient.delete('/admin/school/logo')),
}
