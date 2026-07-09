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
