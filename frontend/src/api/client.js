// Single typed-ish fetch helper. Base URL comes from VITE_API_URL; when empty
// the Vite dev proxy (see vite.config.js) forwards /api and /health.
const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let detail
    try {
      detail = (await res.json()).detail
    } catch {
      detail = res.statusText
    }
    throw new Error(detail || `Request failed (${res.status})`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  health: () => request('/health'),
  listHcps: () => request('/api/v1/hcps'),
  listInteractions: (hcpId) =>
    request(`/api/v1/interactions${hcpId ? `?hcp_id=${hcpId}` : ''}`),
  createInteraction: (payload) =>
    request('/api/v1/interactions', { method: 'POST', body: JSON.stringify(payload) }),
  updateInteraction: (id, patch) =>
    request(`/api/v1/interactions/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  chat: (payload) =>
    request('/api/v1/chat', { method: 'POST', body: JSON.stringify(payload) }),
}
