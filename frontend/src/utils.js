const AVATAR_COLORS = ['#0e7c86', '#4f46e5', '#0f9d6b', '#b0791f', '#d1495b', '#7c3aed', '#0891b2']

export function initials(name = '') {
  const parts = name.replace(/^Dr\.?\s+/i, '').trim().split(/\s+/)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase()
}

export function avatarColor(id = 0) {
  return AVATAR_COLORS[id % AVATAR_COLORS.length]
}

export function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

const pad = (n) => String(n).padStart(2, '0')

/** ISO timestamp → the `yyyy-mm-dd` / `HH:mm` pair the date & time inputs want.
 *  Split in LOCAL time: the rep logs "3pm" meaning 3pm where they are. */
export function splitDateTime(iso) {
  const d = iso ? new Date(iso) : new Date()
  if (Number.isNaN(d.getTime())) return splitDateTime(null)
  return {
    date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
  }
}

/** The inverse — recombine the two inputs into an ISO timestamp for the API. */
export function joinDateTime(date, time) {
  if (!date) return null
  const d = new Date(`${date}T${time || '00:00'}`)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}
