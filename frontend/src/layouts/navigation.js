import { ROLES } from '@/utils/roles'

/**
 * Sidebar navigation, per role.
 *
 * Each role sees only what that role does. The administrator's list is long
 * enough to need grouping - twelve flat items is a wall - so it is banded into
 * sections. Teachers and students get a single unbanded list, because five or
 * six items read faster without headings.
 *
 * Groups are presentation only: every item is a real destination, and the
 * order matches the order the school thinks in - people, then the academic
 * calendar, then results, then the system.
 */
export const NAVIGATION = {
  [ROLES.ADMIN]: [
    { section: null, items: [{ to: '/admin/dashboard', label: 'Dashboard', icon: 'gauge-high' }] },
    {
      section: 'People',
      items: [
        { to: '/admin/students', label: 'Students', icon: 'user-graduate' },
        { to: '/admin/teachers', label: 'Teachers', icon: 'users' },
      ],
    },
    {
      section: 'Academic structure',
      items: [
        { to: '/admin/subjects', label: 'Subjects', icon: 'book' },
        { to: '/admin/classes', label: 'Classes', icon: 'school' },
        { to: '/admin/academic-years', label: 'Academic Years', icon: 'calendar-days' },
        { to: '/admin/terms', label: 'Terms', icon: 'calendar-day' },
        { to: '/admin/examinations', label: 'Examinations', icon: 'file-lines' },
      ],
    },
    {
      section: 'Results',
      items: [
        { to: '/admin/submissions', label: 'Result Submissions', icon: 'list-check' },
        { to: '/admin/results', label: 'Results', icon: 'table-list' },
        { to: '/admin/reports', label: 'Reports', icon: 'file-pdf' },
      ],
    },
    {
      section: 'System',
      items: [{ to: '/admin/settings', label: 'Settings', icon: 'gear' }],
    },
  ],

  [ROLES.TEACHER]: [
    {
      section: null,
      items: [
        { to: '/teacher/dashboard', label: 'Dashboard', icon: 'gauge-high' },
        { to: '/teacher/results', label: 'My Results', icon: 'table-list' },
        { to: '/teacher/upload', label: 'Upload Results', icon: 'cloud-arrow-up' },
        { to: '/teacher/submissions', label: 'Submission Status', icon: 'list-check' },
        { to: '/teacher/downloads', label: 'Downloads', icon: 'download' },
        { to: '/teacher/settings', label: 'Settings', icon: 'gear' },
      ],
    },
  ],

  [ROLES.STUDENT]: [
    {
      section: null,
      items: [
        { to: '/student/dashboard', label: 'Dashboard', icon: 'gauge-high' },
        { to: '/student/results', label: 'My Results', icon: 'table-list' },
        { to: '/student/previous', label: 'Previous Results', icon: 'clock-rotate-left' },
        { to: '/student/downloads', label: 'Downloads', icon: 'download' },
        { to: '/student/settings', label: 'Settings', icon: 'gear' },
      ],
    },
  ],
}

export function navigationFor(role) {
  return NAVIGATION[role] ?? []
}

/** Every destination for a role, flattened - used to title the current page. */
export function flatNavigationFor(role) {
  return navigationFor(role).flatMap((group) => group.items)
}
