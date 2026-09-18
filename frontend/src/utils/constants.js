/**
 * Application-wide constants sourced from Vite environment variables.
 * Nothing sensitive lives here - only public branding and endpoints.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const SCHOOL = {
  name: import.meta.env.VITE_SCHOOL_NAME || 'Presbyterian High School',
  shortName: import.meta.env.VITE_SCHOOL_SHORT_NAME || 'School',
  motto: import.meta.env.VITE_SCHOOL_MOTTO || '',
}

export const APP_NAME = 'Results Portal'

/**
 * The session is an httpOnly cookie set by the server: it cannot be read from
 * here, and it is discarded when the browser closes. Only the CSRF token is
 * readable, and it exists to be echoed back in a header on writes.
 */
export const CSRF_HEADER = 'X-CSRF-Token'

/** When the session ends, so the app can sign out on time rather than on the
 *  next failed request. Holds an expiry timestamp, never a credential. */
export const SESSION_EXPIRY_STORAGE_KEY = 'srp.session_expires_at'

/* ---------------------------------------------------------------------------
 * Status vocabularies, mirroring app/models/enums.py on the backend.
 * ------------------------------------------------------------------------ */

export const EXAMINATION_STATUS = {
  DRAFT: 'DRAFT',
  SUBMISSION_OPEN: 'SUBMISSION_OPEN',
  SUBMISSION_COMPLETE: 'SUBMISSION_COMPLETE',
  UNDER_REVIEW: 'UNDER_REVIEW',
  PUBLISHED: 'PUBLISHED',
}

export const SUBMISSION_STATUS = {
  PENDING: 'PENDING',
  PARTIAL: 'PARTIAL',
  OVERDUE: 'OVERDUE',
  SUBMITTED: 'SUBMITTED',
  LATE: 'LATE',
}

export const ENROLLMENT_STATUS = {
  ACTIVE: 'ACTIVE',
  INACTIVE: 'INACTIVE',
}

export const EDUCATION_LEVEL = {
  O_LEVEL: 'O_LEVEL',
  A_LEVEL: 'A_LEVEL',
}

/** Human-readable labels for the status values above. */
export const STATUS_LABELS = {
  DRAFT: 'Draft',
  SUBMISSION_OPEN: 'Open for submission',
  SUBMISSION_COMPLETE: 'Submissions complete',
  UNDER_REVIEW: 'Under review',
  PUBLISHED: 'Published',
  PENDING: 'Not started',
  PARTIAL: 'In progress',
  OVERDUE: 'Overdue',
  SUBMITTED: 'Submitted',
  LATE: 'Submitted late',
  ACTIVE: 'Active',
  INACTIVE: 'Dropped',
  O_LEVEL: 'O-Level',
  A_LEVEL: 'A-Level',
}

export function statusLabel(status) {
  return STATUS_LABELS[status] || status
}
