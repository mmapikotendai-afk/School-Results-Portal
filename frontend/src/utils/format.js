/** Small display helpers shared across pages. */

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { dateStyle: 'medium' })
}

/** Build initials for the avatar chip, e.g. "Amara Okafor" -> "AO". */
export function initials(fullName = '') {
  return fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
}

/** Join class names, dropping falsy values. */
export function cx(...classes) {
  return classes.filter(Boolean).join(' ')
}
