/** The three portal roles. There is deliberately no parent or public role. */
export const ROLES = {
  ADMIN: 'ADMIN',
  TEACHER: 'TEACHER',
  STUDENT: 'STUDENT',
}

export const ROLE_LABELS = {
  [ROLES.ADMIN]: 'Administrator',
  [ROLES.TEACHER]: 'Teacher',
  [ROLES.STUDENT]: 'Student',
}

/** Landing route for each role after a successful sign-in. */
export const ROLE_HOME = {
  [ROLES.ADMIN]: '/admin/dashboard',
  [ROLES.TEACHER]: '/teacher/dashboard',
  [ROLES.STUDENT]: '/student/dashboard',
}

/** Where the Settings link points for each role. */
export const ROLE_SETTINGS = {
  [ROLES.ADMIN]: '/admin/settings',
  [ROLES.TEACHER]: '/teacher/settings',
  [ROLES.STUDENT]: '/student/settings',
}

export function settingsPathForRole(role) {
  return ROLE_SETTINGS[role] || '/login'
}

export function homePathForRole(role) {
  return ROLE_HOME[role] || '/login'
}

export function roleLabel(role) {
  return ROLE_LABELS[role] || 'User'
}
